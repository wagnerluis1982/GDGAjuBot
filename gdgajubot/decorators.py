import functools
import random
import re
from collections import defaultdict

from telegram.ext import CommandHandler, MessageHandler, Filters

from gdgajubot.util import BotDecorator, bot_callback

__all__ = ('do_not_spam', 'command', 'on_message', 'task', 'easter_egg')


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
    _keywords_ = (0, 1)

    _instances_ = defaultdict(dict)

    @classmethod
    def do_process(cls, target, method, dispatcher, *args, **kwargs):
        to_spam = kwargs.get('to_spam', True)
        instance = cls._instances_[target, to_spam]

        search = re.compile(*args).search
        if not to_spam:
            search = do_not_spam(search)

        action = (search, method)

        try:
            instance['actions'] += (action,)
        except KeyError:
            instance['actions'] = (action,)

        if 'sub_dispatcher' not in instance:
            instance['sub_dispatcher'] = True

            must_do = cls._instances_[target, True]
            no_spam = cls._instances_[target, False]

            def sub_dispatcher(_, update):
                for search, func in must_do.get('actions', ()):
                    if search(update.message.text):
                        func(update.message)
                for search, func in no_spam.get('actions', ()):
                    if search(update.message.text):
                        func(update.message)
                        return

            dispatcher.add_handler(
                MessageHandler(
                    filters=Filters.text,
                    callback=sub_dispatcher,
                ),
                group=1,
            )


easter_egg = functools.partial(on_message, to_spam=False)


class task(BotDecorator):
    _arguments_ = 0
    _keywords_ = 1

    @classmethod
    def do_process(cls, target, method, dispatcher, **kwargs):

        scheduler = target.updater.job_queue
        # repeating task
        if 'each' in kwargs:
            kwargs['interval'] = kwargs.pop('each')
            scheduler.run_repeating(cls.job_callback(method), **kwargs)
        # one time task
        elif 'once' in kwargs:
            kwargs['when'] = kwargs.pop('once')
            scheduler.run_once(cls.job_callback(method), **kwargs)
        # daily task
        elif 'daily' in kwargs:
            kwargs['time'] = kwargs.pop('daily')
            scheduler.run_daily(cls.job_callback(method), **kwargs)
        # error
        else:
            raise ValueError("Use @task with either 'interval', 'once', or 'daily' keyword argument")

    @staticmethod
    def job_callback(method):
        return lambda bot, job: method()
