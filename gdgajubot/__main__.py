import argparse
import logging

import os

from gdgajubot import util
from gdgajubot.bot import GDGAjuBot


def main():
    log_format = os.environ.get('LOG_FORMAT', '%(asctime)s %(message)s')
    log_datefmt = os.environ.get('LOG_DATE_FORMAT', '%m/%d/%Y %I:%M:%S %p')

    # Configuring log
    logging.basicConfig(
        level=logging.INFO,
        format=log_format, datefmt=log_datefmt
    )

    # Configuring bot parameters
    logging.info("Configurando parâmetros")
    parser = util.ArgumentParser(description='Bot do GDG Aracaju')
    parser.add_argument(
        '-c', '--config_file',
        help='Arquivo de configuração')
    parser.add_argument(
        '-t', '--telegram_token',
        help='Token da API do Telegram')
    parser.add_argument(
        '-m', '--meetup_key',
        help='Key da API do Meetup')
    parser.add_argument(
        '-f', '--facebook_key',
        help='Key da API do Facebook')
    parser.add_argument(
        '-db', '--database_url',
        help='URL de configuração do banco de dados',
    )
    parser.add_argument(
        '-g', '--group_name',
        help='Grupo(s) do Meetup/Facebook, separados por vírgulas',
    )
    parser.add_argument(
        '--url_shortener_key',
        help='Key da API do URL Shortener')
    parser.add_argument(
        '--events_source', choices=['meetup', 'facebook'])
    parser.add_argument(
        '-d', '--dev',
        help='Indicador de Debug/Dev mode', action='store_true')
    parser.add_argument(
        '--no-dev',
        help=argparse.SUPPRESS, dest='dev', action='store_false')

    # Parse command line args and get the config
    _config = parser.parse_args()

    # Define the events source if needed
    if not _config.events_source:
        if _config.meetup_key:
            _config.events_source = 'meetup'
        elif _config.facebook_key:
            _config.events_source = 'facebook'
        else:
            parser.error('an API key is needed to get events')

    # Starting bot
    gdgbot = GDGAjuBot(_config)
    gdgbot.start()


if __name__ == "__main__":
    main()
