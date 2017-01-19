# -*- coding: utf-8 -*-
import unittest
import os
from datetime import datetime
from unittest import mock

from gdgajubot import gdgajubot
from gdgajubot import util

AJU_TZ = util.AJU_TZ


# Aliases
MockTeleBot = mock.NonCallableMock
MockMessage = mock.NonCallableMock


class MockResources:
    def __init__(self):
        # Falso cache de eventos
        self.cache_events = [
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229313880/',
             'name': 'Hackeando sua Carreira #Hangout',
             'time': 1459378800000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229623381/',
             'name': 'Android Jam 2: Talks Dia 2',
             'time': 1459612800000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvgbjb/',
             'name': 'Coding Dojo',
             'time': 1459980000000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229591464/',
             'name': 'O Caminho para uma Arquitetura Elegante #Hangout',
             'time': 1460160000000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229770309/',
             'name': 'Android Jam 2: #Curso Dia 2',
             'time': 1460217600000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvhbgb/',
             'name': 'Coding Dojo',
             'time': 1462399200000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229951204/',
             'name': 'Google I/O Extended',
             'time': 1463587200000},
            {'link': 'http://www.meetup.com/GDG-Aracaju/events/229951264/',
             'name': 'Google IO Extended 2016',
             'time': 1463608800000},
        ]

    def get_events(self, n):
        return self.cache_events[:n]

    # Valor fixo para get_packt_free_book
    book = util.AttributeDict(
        name="Android 2099",
        summary="Good practices with Miguel O’Hara",
        expires=4091565600,
    )

    def get_packt_free_book(self):
        return self.book

    def get_short_url(self, long_url):
        return long_url


class TestGDGAjuBot(unittest.TestCase):
    config = {'group_name': 'Test-Bot'}

    # Regular expressions tests

    def test_find_ruby(self):
        assert gdgajubot.find_ruby("Olá ruby GDG")
        assert gdgajubot.find_ruby("Olá RUBY GDG")
        assert gdgajubot.find_ruby("Olá Ruby GDG")
        assert not gdgajubot.find_ruby("OlárubyGDG")

    def test_find_java(self):
        assert gdgajubot.find_java("Olá java GDG")
        assert gdgajubot.find_java("Olá Java GDG")
        assert gdgajubot.find_java("Olá JAVA GDG")
        assert not gdgajubot.find_java("OlájavaGDG")

    def test_find_python(self):
        assert gdgajubot.find_python("Olá python GDG")
        assert gdgajubot.find_python("Olá Python GDG")
        assert gdgajubot.find_python("Olá PYTHON GDG")
        assert not gdgajubot.find_python("OlápythonGDG")

    # Bot commands tests

    def test_send_welcome(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        g_bot.send_welcome(message)
        self._assert_send_welcome(bot, message)

    def test_help(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        g_bot.help(message)
        self._assert_help_message(bot, message)

    def test_list_upcoming_events(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        g_bot.list_upcoming_events(message)

        # Verifica se o response criado está correto
        self._assert_list_upcoming_events(bot, message)

        # Garante que o cache mutável não gerará uma exceção
        n_calls = len(bot.method_calls)
        g_bot.list_upcoming_events(message)
        self.assertGreater(len(bot.method_calls), n_calls)

    def test_packtpub_free_learning(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        ts = resources.book.expires

        # Sem warning
        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 10*3600, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message)

        # Os próximos testes verificam cada um dos warnings
        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 59*60, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message, warning="1 hora")

        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 29*60, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message, warning="meia hora")

        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 9*60, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message, warning="10 minutos")

        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 59, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message, warning="1 minuto")

        g_bot.packtpub_free_learning(message, now=datetime.fromtimestamp(ts - 29, tz=AJU_TZ))
        self._assert_packtpub_free_learning(bot, message, warning="30 segundos")

    def test_changelog(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage(id=0xB00B)
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        g_bot.changelog(message)
        self._assert_changelog(bot, message)

    def _assert_send_welcome(self, bot, message):
        self._assert_mockbot(bot)
        bot.reply_to.assert_called_with(message, "Olá! Eu sou o bot do %s! Se precisar de ajuda: /help" % (self.config["group_name"]))

    def _assert_help_message(self, bot, message):
        self._assert_mockbot(bot)
        help_message = "/help - Exibe essa mensagem.\n" \
            "/book - Informa o ebook gratuito do dia na Packt Publishing.\n" \
            "/events - Informa a lista de próximos eventos do {group_name}."
        help_message = help_message.format(group_name=self.config["group_name"])
        bot.reply_to.assert_called_with(message, help_message)

    def _assert_list_upcoming_events(self, bot, message):
        self._assert_mockbot(bot)
        r = ("[Hackeando sua Carreira #Hangout](http://www.meetup.com/GDG-Aracaju/events/229313880/): 30/03 20h\n"
             "[Android Jam 2: Talks Dia 2](http://www.meetup.com/GDG-Aracaju/events/229623381/): 02/04 13h\n"
             "[Coding Dojo](http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvgbjb/): 06/04 19h\n"
             "[O Caminho para uma Arquitetura Elegante #Hangout](http://www.meetup.com/GDG-Aracaju/events/229591464/): 08/04 21h\n"
             "[Android Jam 2: #Curso Dia 2](http://www.meetup.com/GDG-Aracaju/events/229770309/): 09/04 13h")
        bot.reply_to.assert_called_with(message, r, parse_mode="Markdown", disable_web_page_preview=True)

    def _assert_packtpub_free_learning(self, bot, message, warning=''):
        self._assert_mockbot(bot)
        warning = '' if not warning else '⌛️ Menos de %s!' % warning

        r = ("Confira o livro gratuito de hoje da Packt Publishing 🎁\n\n"
             "📖 [Android 2099](https://www.packtpub.com/packt/offers/free-learning)\n"
             "🔎 Good practices with Miguel O’Hara\n") + warning
        bot.reply_to.assert_called_with(message, r, parse_mode="Markdown", disable_web_page_preview=True)

    def _assert_changelog(self, bot, message):
        self._assert_mockbot(bot)
        r = "https://github.com/GDGAracaju/GDGAjuBot/blob/master/CHANGELOG.md"
        bot.send_message.assert_called_with(message.chat.id, r)

    def _assert_mockbot(self, bot):
        self.assertIsInstance(bot, MockTeleBot)

    # Internals tests

    def test_smart_reply(self):
        bot, resources = MockTeleBot(), MockResources()
        message = MockMessage(id=0x6D6)
        g_bot = gdgajubot.GDGAjuBot(self.config, bot, resources)
        text = "I <3 GDG Aracaju"

        # Mensagens privadas não fazem link
        message.chat.type = "private"
        g_bot._smart_reply(message, text)
        bot.reply_to.assert_called_with(message, text)
        g_bot._smart_reply(message, text)
        bot.reply_to.assert_called_with(message, text)

        # Configurando MockTeleBot.reply_to() para retornar um MockMessage com um message_id
        bot.reply_to.return_value = MockMessage(message_id=82)

        # Mensagens de grupo fazem link
        message.chat.type = "group"
        g_bot._smart_reply(message, text)
        bot.reply_to.assert_called_with(message, text)
        g_bot._smart_reply(message, text)
        bot.send_message.assert_called_with(message.chat.id, "Clique para ver a última resposta",
                                            reply_to_message_id=82)


class TestResources(unittest.TestCase):
    cd = os.path.dirname(__file__)

    def test_extract_packt_free_book(self):
        content = open(os.path.join(self.cd, 'packtpub-free-learning.html.fixture'), 'rb')
        self.assertEqual(gdgajubot.Resources.extract_packt_free_book(content),
                         {'name': "Oracle Enterprise Manager 12c Administration Cookbook",
                          'summary': "Over 50 practical recipes to install, configure, and monitor your Oracle setup using Oracle Enterprise Manager",
                          'expires': 1459378800})
