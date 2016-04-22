# GDG Aracaju Bot

[![Build Status](https://travis-ci.org/GDGAracaju/GDGAjuBot.svg?branch=master)](https://travis-ci.org/GDGAracaju/GDGAjuBot)

O GDG Aracaju Bot, ou `gdgajubot` é um bot de [Telegram](https://telegram.me/) com a função
principal de fazer buscas no [Meetup](http://www.meetup.com/).

## Funcionalidades

O bot atende aos seguintes comandos:

- `/events`: listagem dos próximos eventos registrados no meetup.
- `/book`: livro gratuito do dia da editora [Packt Publishing](https://www.packtpub.com/).

Há também alguns recursos escondidos: olhem os fontes!!!

## Instalação

A instalação é simples, basta baixar o projeto, descompactar e executar:

    $ python setup.py install

Ou, se estiver usando `pip`, basta executar diretamente:

    $ pip install git+https://github.com/GDGAracaju/GDGAjuBot.git

Em qualquer um dos métodos, o script `gdgajubot` será instalado. Verifique se ele está disponível
chamando pela linha de comando:

    $ gdgajubot --help

### Dependências

O `gdgajubot` precisa no mínimo do Python 3.4.

No momento da instalação, as dependências mínimas listadas no arquivo `setup.py` serão baixadas
automaticamente. Para desenvolver o `gdgajubot`, recomendamos a instalação das dependências listadas
no arquivo `requirements.txt` via:

    $ pip install -r requirements.txt

## Uso:

- Instalar as dependências
- Falar com o @BotFather no Telegram e criar seu bot através dos comandos disponíveis nele
- Inserir o token de uma das formas:
  - Sobrescrever o dicionário defaults
  - Passar por parâmetros via --telegram_token, --meetup_key, --group_name
  - Incluir nas variáveis de ambiente via TELEGRAM_TOKEN, MEETUP_KEY, GROUP_NAME
- Rodar o código `python gdgajubot.py`
- Falar com o seu bot no Telegram para testar

