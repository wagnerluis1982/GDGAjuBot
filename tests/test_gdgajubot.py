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
        pass


class MockResources:
    def get_events(self):
        pass

    def get_packt_free_book(self):
        pass


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
