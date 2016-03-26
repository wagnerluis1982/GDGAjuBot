#!/usr/bin/env python3
#!encoding:utf-8
"""Bot do GDG-Aracaju."""
import argparse
import logging
import telebot
import re
import os
import datetime
from lxml import html
import requests
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

# Configuring log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
    )

# Configuring cache
cache = CacheManager(**parse_cache_config_options({ 'cache.type': 'memory' }))

# Configuring bot parameters
logging.info("Configurando parâmetros")
params = ['telegram_token', 'meetup_key', 'group_name']
parser = argparse.ArgumentParser(description='Bot do GDG Aracaju')
parser.add_argument('-t', '--telegram_token', help='Token da API do Telegram')
parser.add_argument('-m', '--meetup_key', help='Key da API do Meetup')
parser.add_argument('-g', '--group_name', help='Grupo do Meetup')
namespace = parser.parse_args()
command_line_args = {k: v for k, v in vars(namespace).items() if v}

_config = {k: command_line_args.get(k, '') or os.environ.get(k.upper(), '')
           for k in params}

# Starting bot
logging.info("Iniciando bot")
logging.info("Usando telegram_token=%s" % (_config["telegram_token"]))
logging.info("Usando meetup_key=%s" % (_config["meetup_key"]))
bot = telebot.TeleBot(_config["telegram_token"])


@cache.cache('get_events', expire=600)
def get_events():
    return list(generate_events())


def generate_events():
    """Obtém eventos do Meetup."""
    default_payload = {'status': 'upcoming'}
    offset = 0
    while True:
        offset_payload = {'offset': offset,
                          'key': _config["meetup_key"],
                          'group_urlname': _config["group_name"]}
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
def get_packt_free_book():
    r = requests.get("https://www.packtpub.com/packt/offers/free-learning")
    page = html.fromstring(r.content)
    book = page.xpath('//*[@id="deal-of-the-day"]/div/div/div[2]/div[2]/h2')
    return book[0].text.strip()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Mensagem de apresentação do bot."""
    logging.info("/start")
    bot.reply_to(message, "Este bot faz buscas no Meetup do %s" % (_config["group_name"]))


@bot.message_handler(commands=['events'])
def list_upcoming_events(message):
    """Retorna a lista de eventos do Meetup."""
    logging.info("%s: %s" % (message.from_user.username, "/events"))
    try:
        all_events = get_events()
        response = []
        for event in all_events[:5]:
            # convert time returned by Meetup API
            time = int(event['time'])/1000
            time_obj = datetime.datetime.fromtimestamp(time)

            # create a pretty-looking date
            date_pretty = time_obj.strftime('%d/%m')

            event['date_pretty'] = date_pretty
            response.append("%s: %s %s" % (event["name"],
                                           event["date_pretty"],
                                           event["event_url"]))

        response = '\n'.join(response)
        bot.reply_to(message, response)
    except Exception as e:
        print(e)


@bot.message_handler(commands=['book'])
def packtpub_free_learning(message):
    """Retorna o livro disponível no free-learning da editora PacktPub."""
    logging.info("%s: %s" % (message.from_user.username, "/book"))
    book = get_packt_free_book()
    bot.send_message(message.chat.id, "[O livro de hoje é: %s](https://www.packtpub.com/packt/offers/free-learning)." % book, parse_mode="Markdown")


# Funções de busca usadas nas easter eggs
find_ruby = re.compile("(?i)RUBY").search
find_java = re.compile("(?i)JAVA").search
find_python = re.compile("(?i)PYTHON").search

@bot.message_handler(func=lambda message:
                     find_ruby(message.text))
def love_ruby(message):
    """Easter Egg com o Ruby."""
    logging.info("%s: %s" % (message.from_user.username, "ruby"))
    username = message.from_user.username
    bot.send_message(message.chat.id, username + " ama Ruby <3")


@bot.message_handler(func=lambda message:
                     find_java(message.text))
def memory_java(message):
    """Easter Egg com o Java."""
    logging.info("%s: %s" % (message.from_user.username, "java"))
    bot.send_message(message.chat.id, "Ihh... acabou a RAM")


@bot.message_handler(func=lambda message:
                     find_python(message.text))
def easter_python(message):
    """Easter Egg com o Python."""
    logging.info("%s: %s" % (message.from_user.username, "python"))
    bot.send_message(message.chat.id, "import antigravity")


@bot.message_handler(commands=['changelog'])
def changelog(message):
    logging.info("%s: %s" % (message.from_user.username, "/changelog"))
    bot.send_message(message.chat.id, "https://github.com/GDGAracaju/GDGAjuBot/blob/master/CHANGELOG.md")


bot.polling(none_stop=True, interval=0, timeout=20)