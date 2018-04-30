import argparse
import datetime
import inspect
import os
import re
from collections import defaultdict

import requests
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


# Bot handler decorator internals

def bot_callback(method):
    return lambda bot, update: method(update.message)


class BotDecorator:
    _arguments_ = (0, ...)
    _keywords_ = (0, ...)
    _optional_args_ = True

    _noargs_call = None

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __call__(self, func):
        try:
            func.decorators
        except AttributeError:
            func.decorators = defaultdict(tuple)
        func.decorators[self.__class__] += ((self._args, self._kwargs),)

        return func

    def __new__(cls, *args, **kwargs):
        cls._validate(args)
        cls._validate(kwargs)

        if cls._optional_args_ and not kwargs and len(args) == 1 and callable(args[0]):
            return cls._noargs_call(args[0])

        decorator = super().__new__(cls)
        decorator.__init__(*args, **kwargs)

        return decorator

    def __init_subclass__(cls):
        for attr in '_arguments_', '_keywords_':
            spec = getattr(cls, attr)
            if spec is ...:
                start, stop = 0, float('inf')
            elif isinstance(spec, int):
                start = stop = spec
            else:
                start, stop = spec

                if stop is ...:
                    stop = float('inf')
                    valid = isinstance(start, int)
                else:
                    valid = isinstance(start, int) and isinstance(stop, int)

                if not valid or not (0 <= start <= stop):
                    raise TypeError("Attribute %r must have a format such as (a, b) and 0 <= a <= b" % attr)

            setattr(cls, attr, (start, stop))

        if cls._optional_args_:
            cls._optional_args_ = cls._arguments_[0] == 0 and cls._keywords_[0] == 0

        if cls._optional_args_:
            cls._noargs_call = super().__new__(cls).__call__

    @classmethod
    def _validate(cls, args_or_kwargs):
        if isinstance(args_or_kwargs, dict):
            kind, (start, stop) = '**kwargs', cls._keywords_
        else:
            kind, (start, stop) = '*args', cls._arguments_

        length = len(args_or_kwargs)
        if length < start:
            raise ValueError("This decorator must have at least %d %s: got %d" % (start, kind, length))
        if length > stop:
            raise ValueError("This decorator accepts up to %d %s: got %d" % (start, kind, length))

    @classmethod
    def is_decorated(cls, func):
        try:
            return inspect.ismethod(func) and cls in func.decorators
        except AttributeError:
            return False

    @classmethod
    def process(cls, target):
        from gdgajubot.bot import GDGAjuBot
        assert isinstance(target, GDGAjuBot)

        for (_, method) in inspect.getmembers(target, cls.is_decorated):
            for args, kwargs in method.decorators[cls]:
                cls.do_process(target, method, target.updater.dispatcher, *args, **kwargs)

    @classmethod
    def do_process(cls, target, method, dispatcher, *args, **kwargs):
        raise NotImplementedError
