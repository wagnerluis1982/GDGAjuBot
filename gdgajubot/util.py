import logging
import re


class HandlerHelper:
    def __init__(self):
        self.map_commands = {}

    def commands(self, *names):
        """Decorator para marcar funções como comandos do bot"""
        def decorator(func):
            def wrapped(*args, **kwargs):
                return func(*args, **kwargs)
            for name in names:
                self.map_commands[name] = func
            return wrapped
        return decorator

    def handle_command(self, name, *args, raises=False, **kwargs):
        """Executa a função associada ao comando passado

        :except: Exceções são relançadas se `raises` é `True`, do contrário, são enviadas ao log.
        :return: `True` ou `False` indicando que o comando foi executado
        """
        function = self.map_commands.get(name)
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
