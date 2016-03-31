#!/usr/bin/env python3
"""Bot do GDG-Aracaju."""
import argparse
import logging
import re
import os
import datetime
import itertools

import requests
import telebot
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from bs4 import BeautifulSoup


class Resources:
    # Configuring cache
    cache = CacheManager(**parse_cache_config_options({'cache.type': 'memory'}))

    def __init__(self, config):
        self.config = config

    @cache.cache('get_events', expire=600)
    def get_events(self, list_size=5):
        return list(itertools.islice(self.generate_events(), list_size))

    def generate_events(self):
        """Obtém eventos do Meetup."""
        default_payload = {'status': 'upcoming'}
        offset = 0
        while True:
            offset_payload = {'offset': offset,
                              'key': self.config["meetup_key"],
                              'group_urlname': self.config["group_name"]}
            payload = default_payload.copy()
            payload.update(offset_payload)
            # Above is the equivalent of jQuery.extend()
            # for Python 3.5: payload = {**default_payload, **offset_payload}

            r = requests.get('https://api.meetup.com/2/events', params=payload)
            json = r.json()

            results, meta = json['results'], json['meta']
            for item in results:
                yield item

            # if we no longer have more results pages, stop…
            if not meta['next']:
                return

            offset = offset + 1

    @cache.cache('get_packt_free_book', expire=600)
    def get_packt_free_book(self):
        r = requests.get("https://www.packtpub.com/packt/offers/free-learning")
        return self.extract_packt_free_book(r.content)

    @staticmethod
    def extract_packt_free_book(content):
        page = BeautifulSoup(content, 'html.parser')
        book = page.select_one('#deal-of-the-day div div div:nth-of-type(2) div:nth-of-type(2) h2')
        return book.text.strip()


# Funções de busca usadas nas easter eggs
find_ruby = re.compile(r"(?i)\bRUBY\b").search
find_java = re.compile(r"(?i)\bJAVA\b").search
find_python = re.compile(r"(?i)\bPYTHON\b").search


class GDGAjuBot:
    def __init__(self, bot, resources, config):
        self.bot = bot
        self.resources = resources
        self.config = config
        bot.set_update_listener(self.handle_messages)

    def send_welcome(self, message):
        """Mensagem de apresentação do bot."""
        logging.info("/start")
        self.bot.reply_to(message, "Este bot faz buscas no Meetup do %s" % (self.config["group_name"]))

    def list_upcoming_events(self, message):
        """Retorna a lista de eventos do Meetup."""
        logging.info("%s: %s" % (message.from_user.username, "/events"))
        try:
            response = []
            for event in self.resources.get_events():
                # convert time returned by Meetup API
                time = int(event['time'])/1000
                time_obj = datetime.datetime.utcfromtimestamp(time)
                # adjust time to UTC-3
                time_obj -= datetime.timedelta(hours=3)

                # create a pretty-looking date
                date_pretty = time_obj.strftime('%d/%m')

                event['date_pretty'] = date_pretty
                response.append("%s: %s %s" % (event["name"],
                                               event["date_pretty"],
                                               event["event_url"]))

            response = '\n'.join(response)
            self.bot.reply_to(message, response, disable_web_page_preview=True)
        except Exception as e:
            print(e)

    def packtpub_free_learning(self, message):
        """Retorna o livro disponível no free-learning da editora PacktPub."""
        logging.info("%s: %s" % (message.from_user.username, "/book"))
        book = self.resources.get_packt_free_book()
        self.bot.reply_to(message,
                          "O livro de hoje é: [%s](https://www.packtpub.com/packt/offers/free-learning)" % book,
                          parse_mode="Markdown", disable_web_page_preview=True)

    def love_ruby(self, message):
        """Easter Egg com o Ruby."""
        logging.info("%s: %s" % (message.from_user.username, "ruby"))
        username = message.from_user.username
        self.bot.send_message(message.chat.id, username + " ama Ruby <3")

    def memory_java(self, message):
        """Easter Egg com o Java."""
        logging.info("%s: %s" % (message.from_user.username, "java"))
        self.bot.send_message(message.chat.id, "Ihh... acabou a RAM")

    def easter_python(self, message):
        """Easter Egg com o Python."""
        logging.info("%s: %s" % (message.from_user.username, "python"))
        self.bot.send_message(message.chat.id, "import antigravity")

    def changelog(self, message):
        logging.info("%s: %s" % (message.from_user.username, "/changelog"))
        self.bot.send_message(message.chat.id, "https://github.com/GDGAracaju/GDGAjuBot/blob/master/CHANGELOG.md")

    def handle_messages(self, messages):
        for message in messages:
            if message.content_type == "text":
                # Identifica o comando e despacha para a função correta
                command = telebot.util.extract_command(message.text)
                if command in ['start', 'help']:
                    self.send_welcome(message)
                elif command == 'events':
                    self.list_upcoming_events(message)
                elif command == 'book':
                    self.packtpub_free_learning(message)
                elif command == 'changelog':
                    self.changelog(message)

                # Easter eggs
                elif find_ruby(message.text):
                    self.love_ruby(message)
                elif find_java(message.text):
                    self.memory_java(message)
                elif find_python(message.text):
                    self.easter_python(message)

    def start(self):
        self.bot.polling(none_stop=True, interval=0, timeout=20)


def main():
    # Configuring log
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
    )

    # Configuring bot parameters
    logging.info("Configurando parâmetros")
    parser = argparse.ArgumentParser(description='Bot do GDG Aracaju')
    parser.add_argument('-t', '--telegram_token', help='Token da API do Telegram')
    parser.add_argument('-m', '--meetup_key', help='Key da API do Meetup')
    parser.add_argument('-g', '--group_name', help='Grupo do Meetup')
    namespace = parser.parse_args()

    _config = {k: v or os.environ.get(k.upper(), '')
               for k, v in vars(namespace).items()}

    # Starting bot
    logging.info("Iniciando bot")
    logging.info("Usando telegram_token=%s" % (_config["telegram_token"]))
    logging.info("Usando meetup_key=%s" % (_config["meetup_key"]))
    bot = telebot.TeleBot(_config['telegram_token'])
    resources = Resources(_config)
    gdgbot = GDGAjuBot(bot, resources, _config)
    gdgbot.start()


if __name__ == "__main__":
    main()
