import argparse
import datetime
import functools
import os
import random
import re
from collections import defaultdict

import requests
import threading
from urllib import parse
import yaml

import dj_database_url

DEFAULT_DATABASE = {
    'provider': 'sqlite',
    'filename': 'database.sqlite',
    'create_db': True,
}


class BotConfig:
    def __init__(
        self,
        telegram_token=None,
        meetup_key=None,
        facebook_key=None,
        database_url=None,
        group_name=None,
        url_shortener_key=None,
        events_source=None,
        dev=True,
        config_file=None,
    ):
        self.telegram_token = telegram_token
        self.meetup_key = meetup_key
        self.facebook_key = facebook_key
        self.group_name = group_name.split(',') if group_name else None
        self.url_shortener_key = url_shortener_key
        self.events_source = events_source.split(
            ',') if events_source else None
        self.debug_mode = dev
        self.links = None
        self.custom_responses = None
        self.database = (
            self.parse_database_url(database_url)
            if database_url else DEFAULT_DATABASE
        )
        if config_file:
            self.load_config_file(config_file)

    def load_config_file(self, config_file):
        stream = self.open_file_or_url(config_file)
        contents = yaml.load(stream)
        self.debug_mode = contents.get('debug_mode', None)
        self.events_source = contents.get('events_source', None)
        self.links = contents.get('links', ())
        self.custom_responses = contents.get('custom_responses', None)
        if 'tokens' in contents:
            self.telegram_token = contents['tokens'].get('telegram', None)
            self.meetup_key = contents['tokens'].get('meetup', None)
            self.facebook_key = contents['tokens'].get('facebook', None)
        if 'database' in contents:
            self.database = contents['database']
        if 'database_url' in contents:
            self.database = self.parse_database_url(contents['database_url'])

    def open_file_or_url(self, file_or_url):
        if bool(parse.urlparse(file_or_url).netloc):
            return requests.get(file_or_url).text
        else:
            with open(file_or_url, 'r') as config_file:
                return config_file.read()

    def parse_database_url(self, database_url):
        def parse_postgres(database_dict):
            database = dict(database_dict)
            return {
                'provider': 'postgres',
                'database': database.get('NAME'),
                'user': database.get('USER'),
                'password': database.get('PASSWORD'),
                'host': database.get('HOST'),
                'port': database.get('PORT'),
            }

        def parse_sqlite(database_dict):
            return {
                'provider': 'sqlite',
                'filename': database_dict['PATH'],
            }

        try:
            dj_engine_to_pony_provider = {
                'django.db.backends.postgresql_psycopg2': parse_postgres,
                'django.db.backends.sqlite3': parse_sqlite,
            }
            parsed = dj_database_url.parse(database_url)
            return dj_engine_to_pony_provider[parsed['ENGINE']](parsed)
        except KeyError:
            raise Exception('There was an error parsing the database_url configuration.')


class HandlerHelper:
    def __init__(self, use_options=False, force_options=True):
        self.use_options = use_options
        self.force_options = force_options
        self.functions = []

    def __call__(self, *names, **options):
        """Decorator para anotar funções para usar como handlers do bot"""
        assert not self.use_options or not self.force_options or options, "Expecting keyword arguments, but none set"

        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                return func(*args, **kwargs)

            if self.functions:
                last = self.functions[-1]
                if names:
                    assert callable(last[1]), "This decorator should be called with *args"
                elif self.use_options:
                    assert callable(last[0]), "This decorator should be called with **kwargs"
                else:
                    assert callable(last), "This decorator should be called with no arguments"

            if names:
                for name in names:
                    self.functions += [(name, func, options)] if self.use_options else [(name, func)]
            elif self.use_options:
                self.functions += [(func, options)]
            else:
                self.functions += [func]

            return wrapped

        return decorator


def match_command(text):
    """Verifica se o texto passado representa um comando

    :return: um objeto regex match ou `None`
    """
    return re.match(r'(/[^\s]+ ?[^\s]+(?:\s+[^\s]+)*)', text)


def extract_command(text):
    """Extrai o nome do comando, incluindo a barra '/'

    :return: nome do comando ou `None`
    """
    match = match_command(text)
    if match:
        return match.group(1).split()[0].split('@')[0]


def do_not_spam(func):
    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        if random.randint(0,100) < 10:
            return func(*args, **kwargs)
    return func_wrapper


class TimeZone:
    class TZ(datetime.tzinfo):
        ZERO = datetime.timedelta(0)

        def __init__(self, hours):
            self._utcoffset = datetime.timedelta(hours=hours)
            self._tzname = 'GMT%d' % hours

        def utcoffset(self, dt):
            return self._utcoffset

        def tzname(self, dt):
            return self._tzname

        def dst(self, dt):
            return self.ZERO

        def __repr__(self):
            return self._tzname

    # cache de fusos horários
    timezones = {}

    @classmethod
    def gmt(cls, hours):
        if hours not in cls.timezones:
            cls.timezones[hours] = cls.TZ(hours)
        return cls.timezones[hours]


# aliases úteis
AJU_TZ = TimeZone.gmt(-3)


class Atomic:
    def __init__(self, value=None):
        self._value = value
        self._lock = threading.RLock()

    def set(self, value, on_diff=False):
        with self._lock:
            if on_diff:
                if value == self._value:
                    return False
            self._value = value
            return True

    def get(self, on_none_f=None):
        with self._lock:
            if self._value is None:
                self.set(on_none_f())
            return self._value


class MissingDict(defaultdict):
    def __init__(self, default_factory, **kwargs):
        super().__init__(default_factory, **kwargs)

    def __missing__(self, key):
        if self.default_factory is not None:
            self[key] = value = self.default_factory(key)
            return value
        return super().__missing__(key)


class StateDict(dict):
    def __init__(self, data, dump_function):
        super().__init__()
        self.dump_function = dump_function
        self.update(data)
        self.contexts = 0

    def __enter__(self):
        self.contexts += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.contexts -= 1
        if self.contexts == 0:
            self.dump()

    def dump(self):
        self.dump_function(self)


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._required_actions = []

    def add_argument(self, *args, **kwargs):
        action = super().add_argument(*args, **kwargs)
        if action.required:
            action.required = False
            self._required_actions += [action]

    def parse_args(self, *args, **kwargs):
        namespace = super().parse_args(*args, **kwargs)

        # Mounting config
        config_dict = {
            k: v or os.environ.get(k.upper(), '')
            for k, v in vars(namespace).items()
        }

        # Verifying required arguments
        missing_args = [
            argparse._get_action_name(a)
            for a in self._required_actions if not config_dict[a.dest]
        ]
        if missing_args:
            self.error("missing arguments: " + ", ".join(missing_args))

        return BotConfig(**config_dict)
