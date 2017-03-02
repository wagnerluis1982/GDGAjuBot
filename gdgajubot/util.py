from urllib import parse
import requests
import argparse
import datetime
import functools
import logging
import os
import re
import threading
import yaml


class BotConfig:
    def __init__(
        self,
        telegram_token=None,
        meetup_key=None,
        facebook_key=None,
        group_name=None,
        url_shortener_key=None,
        events_source=None,
        dev=True,
        config_file=None
    ):
        if config_file:
            self.load_config_file(config_file)
        self.telegram_token = telegram_token or self.telegram_token
        self.meetup_key = meetup_key or self.meetup_key
        self.facebook_key = facebook_key or self.facebook_key
        self.group_name = group_name.split(',') if group_name else None
        self.url_shortener_key = url_shortener_key
        self.events_source = events_source.split(
            ',') if events_source else self.events_source
        self.debug_mode = dev or self.debug_mode
        self.links = None or self.links
        self.custom_responses = None or self.custom_responses

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

    def open_file_or_url(self, file_or_url):
        if bool(parse.urlparse(file_or_url).netloc):
            return requests.get(file_or_url).text
        else:
            with open(file_or_url, 'r') as config_file:
                return config_file.read()


class HandlerHelper:
    def __init__(self):
        self.functions = {}

    def __call__(self, *names):
        """Decorator para marcar funções como comandos do bot"""
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                return func(*args, **kwargs)
            for name in names:
                self.functions[name] = func
            return wrapped
        return decorator

    def handle(self, name, raises=False, *args, **kwargs):
        """Executa a função associada ao comando passado

        :except: Exceções são relançadas se `raises` é `True`,
                 do contrário, são enviadas ao log.
        :return: `True` ou `False` indicando que o comando foi executado
        """
        function = self.functions.get(name)
        if function:
            try:
                function(*args, **kwargs)
            except Exception as e:
                raise e if raises else logging.exception(e)
            return True
        return False


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
