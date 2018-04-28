from telegram.ext import CommandHandler

from gdgajubot.util import BotDecorator, bot_callback

__all__ = ('command',)


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
