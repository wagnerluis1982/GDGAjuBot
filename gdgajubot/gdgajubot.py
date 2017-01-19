#!/usr/bin/env python3
"""Bot do GDG-Aracaju."""
import argparse
import logging
import re
import datetime
import time

import requests
import requests.exceptions
import telebot
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from bs4 import BeautifulSoup

from . import util


class Resources:
    BOOK_URL = "https://www.packtpub.com/packt/offers/free-learning"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/51.0.2704.79 Safari/537.36"
    }

    # Configuring cache
    cache = CacheManager(**parse_cache_config_options({'cache.type': 'memory'}))

    def __init__(self, config):
        self.config = config

    @cache.cache('get_events', expire=60)
    def get_events(self, list_size=5):
        return list(self.generate_events(list_size))

    def generate_events(self, n):
        """Obtém eventos do Meetup."""
        # api v3 base url
        url = "https://api.meetup.com/%(group_name)s/events" % self.config

        # response for the events
        r = requests.get(url, params={
            'key': self.config['meetup_key'],
            'status': 'upcoming',
            'only': 'name,time,link',  # filter response to these fields
            'page': n,                 # limit to n events
        })

        return r.json()

    @cache.cache('get_packt_free_book', expire=600)
    def get_packt_free_book(self):
        r = requests.get(self.BOOK_URL, headers=self.HEADERS)
        return self.extract_packt_free_book(r.content, r.encoding)

    @staticmethod
    def extract_packt_free_book(content, encoding='utf-8'):
        if hasattr(content, 'read'):    # file-type
            content = content.read()
        if isinstance(content, bytes):  # convert to str
            content = content.decode(encoding)

        # Extracting information with html parser
        page = BeautifulSoup(content, 'html.parser')
        dealoftheday = page.select_one('#deal-of-the-day div div div:nth-of-type(2)')

        if not dealoftheday:
            return None

        book = util.AttributeDict()
        book['name'] = dealoftheday.select_one('div:nth-of-type(2) h2').text.strip()
        book['summary'] = dealoftheday.select_one('div:nth-of-type(3)').text.strip()
        book['expires'] = int(dealoftheday.select_one('span.packt-js-countdown').attrs['data-countdown-to'])

        return book

    @cache.cache('get_short_url')
    def get_short_url(self, long_url):
        # Faz a requisição da URL curta somente se houver uma key configurada
        if self.config['url_shortener_key']:
            r = requests.post("https://www.googleapis.com/urlshortener/v1/url",
                              params={'key': self.config['url_shortener_key'],
                                      'fields': 'id'},
                              json={'longUrl': long_url})
            if r.status_code == 200:
                return r.json()['id']
            else:
                logging.exception(r.text)

        # Caso tenha havido algum problema usa a própria URL longa
        return long_url


# Funções de busca usadas nas easter eggs
find_ruby = re.compile(r"(?i)\bRUBY\b").search
find_java = re.compile(r"(?i)\bJAVA\b").search
find_python = re.compile(r"(?i)\bPYTHON\b").search

# Helper para definir os comandos do bot
commands = util.HandlerHelper()


class GDGAjuBot:
    def __init__(self, config, bot=None, resources=None):
        self.config = config
        self.bot = bot if bot else telebot.TeleBot(config['telegram_token'])
        self.resources = resources if resources else Resources(config)

        self.bot.set_update_listener(self.handle_messages)

    @commands('/start')
    def send_welcome(self, message):
        """Mensagem de apresentação do bot."""
        logging.info("/start")
        self.bot.reply_to(message, "Olá! Eu sou o bot do %s! Se precisar de ajuda: /help" % (self.config["group_name"]))

    @commands('/help')
    def help(self, message):
        """Mensagem de ajuda do bot."""
        logging.info("/help")
        help_message = "/help - Exibe essa mensagem.\n" \
            "/book - Informa o ebook gratuito do dia na Packt Publishing.\n" \
            "/events - Informa a lista de próximos eventos do {group_name}."
        self.bot.reply_to(message, help_message.format(group_name=self.config["group_name"]))

    @commands('/events')
    def list_upcoming_events(self, message):
        """Retorna a lista de eventos do Meetup."""
        logging.info("%s: %s", message.from_user.username, "/events")
        try:
            next_events = self.resources.get_events(5)
            response = self._format_events(next_events) if next_events else \
                "Não há nenhum futuro evento do grupo %s." % self.config["group_name"]
            self._smart_reply(message, response,
                              parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logging.exception(e)

    def _format_events(self, events):
        response = []
        for event in events:
            # If the events wasn't in cache, event['time'] is a timestamp.
            # So we format it!
            if isinstance(event['time'], int):
                # convert time returned by Meetup API
                event_dt = datetime.datetime.fromtimestamp(event['time'] / 1000, tz=util.AJU_TZ)

                # create a pretty-looking date
                formatting = '%d/%m %Hh'
                if event_dt.minute:
                    formatting += '%M'
                event['time'] = event_dt.strftime(formatting)

                # When event['time'] is a timestamp, we also know that event['link'] is a long url.
                # So we shorten it!
                event['link'] = self.resources.get_short_url(event['link'])

            response.append("[%(name)s](%(link)s): %(time)s" % event)
        return '\n'.join(response)

    @commands('/book')
    def packtpub_free_learning(self, message, now=None):
        """Retorna o livro disponível no free-learning da editora PacktPub."""
        logging.info("%s: %s", message.from_user.username, "/book")
        # Faz duas tentativas para obter o livro do dia, por questões de possível cache antigo.
        for _ in range(2):
            book = self.resources.get_packt_free_book()
            response = self._book_response(book, now)
            if response:
                break
            Resources.cache.invalidate(Resources.get_packt_free_book, "get_packt_free_book")
        # As tentativas falharam...
        else:
            response = "O livro de hoje ainda não está disponível"
        self._smart_reply(message, response,
                          parse_mode="Markdown", disable_web_page_preview=True)

    timeleft = ((30, '30 segundos'),
                (60, '1 minuto'),
                (600, '10 minutos'),
                (1800, 'meia hora'),
                (3600, '1 hora'))

    def _book_response(self, book, now=None):
        if book is None:
            return Resources.BOOK_URL

        if now is None:
            now = datetime.datetime.now(tz=util.AJU_TZ)

        delta = datetime.datetime.fromtimestamp(book.expires, tz=util.AJU_TZ) - now
        seconds = delta.total_seconds()
        if seconds < 0:
            return

        response = (
            "Confira o livro gratuito de hoje da Packt Publishing 🎁\n\n"
            "📖 [%s](%s)\n"
            "🔎 %s\n"
        ) % (book.name, Resources.BOOK_URL, book.summary)

        for num, in_words in self.timeleft:
            if seconds <= num:
                warning = "⌛️ Menos de %s!" % in_words
                return response + warning
        return response

    def _smart_reply(self, message, text, **kwargs):
        # On groups or supergroups, check if I have a recent previous response to refer
        if message.chat.type in ["group", "supergroup"]:
            # Retrieve from cache and set if necessary
            key = "p%s" % util.extract_command(text)
            previous_cache = Resources.cache.get_cache(key, expire=600)
            previous = previous_cache.get(key=message.chat.id, createfunc=dict)

            # Verify if previous response is the same to send a contextual response
            if previous.get('text') == text:
                self.bot.send_message(message.chat.id, "Clique para ver a última resposta",
                                      reply_to_message_id=previous['message_id'])
            # or, send new response and update the cache
            else:
                sent = self.bot.reply_to(message, text, **kwargs)
                previous.update({'text': text, 'message_id': sent.message_id})
                previous_cache[message.chat.id] = previous  # reset expire time

        # On private chats or channels, send the normal reply...
        else:
            self.bot.reply_to(message, text, **kwargs)

    @commands('/changelog')
    def changelog(self, message):
        logging.info("%s: %s", message.from_user.username, "/changelog")
        self.bot.send_message(message.chat.id, "https://github.com/GDGAracaju/GDGAjuBot/blob/master/CHANGELOG.md")

    def love_ruby(self, message):
        """Easter Egg com o Ruby."""
        logging.info("%s: %s", message.from_user.username, "ruby")
        username = message.from_user.username
        self.bot.send_message(message.chat.id, username + " ama Ruby <3")

    def memory_java(self, message):
        """Easter Egg com o Java."""
        logging.info("%s: %s", message.from_user.username, "java")
        self.bot.send_message(message.chat.id, "Ihh... acabou a RAM")

    def easter_python(self, message):
        """Easter Egg com o Python."""
        logging.info("%s: %s", message.from_user.username, "python")
        self.bot.send_message(message.chat.id, "import antigravity")

    def handle_messages(self, messages):
        for message in messages:
            if message.content_type == "text":
                # Identifica o comando e despacha para a função correta
                command = util.extract_command(message.text)
                if command:
                    commands.handle(command, *(self, message))

                # Easter eggs
                elif find_ruby(message.text):
                    self.love_ruby(message)
                elif find_java(message.text):
                    self.memory_java(message)
                elif find_python(message.text):
                    self.easter_python(message)

    def start(self):
        while True:
            try:
                self.bot.polling(none_stop=True, interval=0, timeout=20)
                break
            except requests.exceptions.RequestException as e:
                logging.exception(e)
                logging.info("Reiniciando bot em 10 segundos")
                time.sleep(10)


def main():
    # Configuring log
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
    )

    # Configuring bot parameters
    logging.info("Configurando parâmetros")
    parser = util.ArgumentParser(description='Bot do GDG Aracaju')
    parser.add_argument('-t', '--telegram_token', help='Token da API do Telegram', required=True)
    parser.add_argument('-m', '--meetup_key', help='Key da API do Meetup', required=True)
    parser.add_argument('-g', '--group_name', help='Grupo do Meetup', required=True)
    parser.add_argument('--url_shortener_key', help='Key da API do URL Shortener')
    parser.add_argument('-d', '--dev', help='Indicador de Debug/Dev mode', action='store_true')
    parser.add_argument('--no-dev', help=argparse.SUPPRESS, dest='dev', action='store_false')

    # Parse command line args and get the config
    _config = parser.parse_args()

    # Starting bot
    logging.info("Iniciando bot")
    gdgbot = GDGAjuBot(_config)
    if _config["dev"]:
        logging.info("Dev mode activated.")
        logging.info("Usando @%s", gdgbot.bot.get_me().username)
        logging.info("Usando telegram_token=%(telegram_token)s", _config)
        logging.info("Usando meetup_key=%(meetup_key)s", _config)
    gdgbot.start()


if __name__ == "__main__":
    main()
