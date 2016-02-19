#!/usr/bin/env python3
#!encoding:utf-8
"""Bot do GDG-Aracaju."""
import argparse
import logging
import telebot
import re
import os
import collections
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
defaults = {
    'telegram_token': '',
    'meetup_key': '',
    'group_name': ''
}
parser = argparse.ArgumentParser(description='Bot do GDG Aracaju')
parser.add_argument('-t', '--telegram_token', help='Token da API do Telegram')
parser.add_argument('-m', '--meetup_key', help='Key da API do Meetup')
parser.add_argument('-g', '--group_name', help='Grupo do Meetup')
namespace = parser.parse_args()
command_line_args = {k: v for k, v in vars(namespace).items() if v}

_config = collections.ChainMap(command_line_args, os.environ, defaults)

# Starting bot
logging.info("Iniciando bot")
logging.info("Usando telegram_token=%s" % (_config["telegram_token"]))
logging.info("Usando meetup_key=%s" % (_config["meetup_key"]))
bot = telebot.TeleBot(_config["telegram_token"])


def find_match(expression, string):
    match = re.search(expression, string)
    return match is not None


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
        response = ""
        for event in all_events:
            # convert time returned by Meetup API
            time = int(event['time'])/1000
            time_obj = datetime.datetime.fromtimestamp(time)

            # create a pretty-looking date
            date_pretty = time_obj.strftime('%d/%m')

            event['date_pretty'] = date_pretty
            response = response + ("%s: %s %s \n" % (event["name"],
                                                     event["date_pretty"],
                                                     event["event_url"]))

        bot.reply_to(message, response)
    except Exception as e:
        print(e)


@bot.message_handler(commands=['book'])
def packtpub_free_learning(message):
    """Retorna o livro disponível no free-learning da editora PacktPub."""
    logging.info("%s: %s" % (message.from_user.username, "/book"))
    r = requests.get("https://www.packtpub.com/packt/offers/free-learning")
    page = html.fromstring(r.content)
    book = page.xpath('//*[@id="deal-of-the-day"]/div/div/div[2]/div[2]/h2')
    # time_left = page.xpath('//*[@id="deal-of-the-day"]/div/div/div[2]/div[1]/span')
    bot.send_message(message.chat.id, "O livro de hoje é: " +
                     book[0].text.strip()+"\n"+"acesse:" +
                     "https://www.packtpub.com/packt/offers/free-learning")


@bot.message_handler(func=lambda message:
                     find_match("RUBY", message.text.upper()))
def love_ruby(message):
    """Easter Egg com o Ruby."""
    logging.info("%s: %s" % (message.from_user.username, "ruby"))
    username = message.from_user.username
    bot.send_message(message.chat.id, username + " ama Ruby <3")


@bot.message_handler(func=lambda message:
                     find_match("JAVA", message.text.upper()))
def memory_java(message):
    """Easter Egg com o Java."""
    logging.info("%s: %s" % (message.from_user.username, "java"))
    bot.send_message(message.chat.id, "Ihh... acabou a RAM")


@bot.message_handler(func=lambda message:
                     find_match("PYTHON", message.text.upper()))
def memory_java(message):
    """Easter Egg com o Python."""
    logging.info("%s: %s" % (message.from_user.username, "python"))
    bot.send_message(message.chat.id, "import antigravity")


@bot.message_handler(commands=['changelog'])
def changelog(message):
    logging.info("%s: %s" % (message.from_user.username, "/changelog"))
    bot.send_message(message.chat.id, "https://github.com/GDGAracaju/GDGAjuBot/blob/master/CHANGELOG.md")


bot.polling()
