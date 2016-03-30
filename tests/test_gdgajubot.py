# -*- coding: utf-8 -*-
import sys

sys.path.append('../')

import time
import unittest
import os
import gdgajubot


class MetaCall:
    def __call__(self, item, *args, **kwargs):
        return item, args, kwargs

    def __getattr__(self, item):
        def _call(*args, **kwargs):
            return self(item, *args, **kwargs)
        return _call

# Usado nos testes para identificar o método chamado (nome e argumentos)
CALL = MetaCall()


class MockTeleBot:
    calls = []

    # Registra cada método chamado da classe
    def __getattr__(self, item):
        def _call(*args, **kwargs):
            self.calls.append(CALL(item, *args, **kwargs))
        return _call


class MockMessage:
    # Método definido para não ter AttributeError
    def __getattribute__(self, item):
        return self


class MockResources:
    def get_events(self):
        return [
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229313880/',
             'name': 'Hackeando sua Carreira #Hangout',
             'time': 1459378800000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229623381/',
             'name': 'Android Jam 2: Talks Dia 2',
             'time': 1459612800000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvgbjb/',
             'name': 'Coding Dojo',
             'time': 1459980000000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229591464/',
             'name': 'O Caminho para uma Arquitetura Elegante #Hangout',
             'time': 1460160000000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229770309/',
             'name': 'Android Jam 2: #Curso Dia 2',
             'time': 1460217600000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvhbgb/',
             'name': 'Coding Dojo',
             'time': 1462399200000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229951204/',
             'name': 'Google I/O Extended',
             'time': 1463587200000},
            {'event_url': 'http://www.meetup.com/GDG-Aracaju/events/229951264/',
             'name': 'Google IO Extended 2016',
             'time': 1463608800000},
        ]

    def get_packt_free_book(self):
        return "Android 2099"


class TestGDGAjuBot(unittest.TestCase):
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

    def test_send_welcome(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        config = {'group_name': 'Test-Bot'}
        g_bot = gdgajubot.GDGAjuBot(bot, resources, config)
        g_bot.send_welcome(message)
        self.assertEqual(bot.calls[-1],
                         CALL.reply_to(message, "Este bot faz buscas no Meetup do Test-Bot"))

    def test_list_upcoming_events(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(bot, resources, {})
        g_bot.list_upcoming_events(message)
        r = ("Hackeando sua Carreira #Hangout: 30/03 http://www.meetup.com/GDG-Aracaju/events/229313880/\n"
             "Android Jam 2: Talks Dia 2: 02/04 http://www.meetup.com/GDG-Aracaju/events/229623381/\n"
             "Coding Dojo: 06/04 http://www.meetup.com/GDG-Aracaju/events/mwnsrlyvgbjb/\n"
             "O Caminho para uma Arquitetura Elegante #Hangout: 08/04 http://www.meetup.com/GDG-Aracaju/events/229591464/\n"
             "Android Jam 2: #Curso Dia 2: 09/04 http://www.meetup.com/GDG-Aracaju/events/229770309/")
        self.assertEqual(bot.calls[-1],
                         CALL.reply_to(message, r, disable_web_page_preview=True))

    def test_packtpub_free_learning(self):
        bot, resources, message = MockTeleBot(), MockResources(), MockMessage()
        g_bot = gdgajubot.GDGAjuBot(bot, resources, {})
        g_bot.packtpub_free_learning(message)
        r = "O livro de hoje é: [Android 2099](https://www.packtpub.com/packt/offers/free-learning)"
        self.assertEqual(bot.calls[-1],
                         CALL.reply_to(message, r, parse_mode="Markdown", disable_web_page_preview=True))


class TestResources(unittest.TestCase):
    cd = os.path.dirname(__file__)

    def test_extract_packt_free_book(self):
        content = open(os.path.join(self.cd, 'packtpub-free-learning.html'))
        self.assertEqual(gdgajubot.Resources.extract_packt_free_book(content),
                         "Oracle Enterprise Manager 12c Administration Cookbook")
