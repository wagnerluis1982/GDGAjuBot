import functools
import random
import re
from collections import defaultdict

from telegram.ext import CommandHandler, MessageHandler, Filters

from gdgajubot.util import BotDecorator, bot_callback

__all__ = ('do_not_spam', 'command', 'on_message')


def do_not_spam(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if random.randint(0, 100) < 10:
            return func(*args, **kwargs)

    return wrapper


class command(BotDecorator):
    _arguments_ = (1, ...)
    _keywords_ = (0, 1)

    @classmethod
    def do_process(cls, target, method, dispatcher, *args, **kwargs):
        names = [(k[1:] if k[0] == '/' else k)
                 for k in args]
        handler = CommandHandler(names, bot_callback(method))

        from gdgajubot.bot import AdminFilter
        if kwargs.get('admin', False):
            handler.filters = AdminFilter(names[0], target.resources)

        dispatcher.add_handler(handler)


class on_message(BotDecorator):
    _arguments_ = 1
    _keywords_ = 0

    _instances_ = defaultdict(dict)

    @classmethod
    def do_process(cls, target, method, dispatcher, *args):
        instance = cls._instances_[target]
        action = (re.compile(*args).search, method)

        try:
            instance['actions'] += (action,)
        except KeyError:
            instance['actions'] = (action,)

        if 'sub_dispatcher' not in instance:
            instance['sub_dispatcher'] = True

            def sub_dispatcher(_, update):
                for search, func in instance['actions']:
                    if search(update.message.text):
                        func(update.message)

            dispatcher.add_handler(
                MessageHandler(
                    filters=Filters.text,
                    callback=sub_dispatcher,
                ),
                group=1,
            )
