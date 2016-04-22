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

## Modo de uso

### Pré-requisitos

Antes de começar, é necessário um token do Telegram [obtido com o @BotFather](https://core.telegram.org/bots#6-botfather),
que vincula ao seu bot, e uma [chave do Meetup](https://secure.meetup.com/pt-BR/meetup_api/key/),
para ter permissões de acesso à API do Meetup.

### Iniciar o bot

Para o bot ser iniciado, execute

    $ gdgajubot -t 'TELEGRAM_TOKEN' -m 'MEETUP_KEY' -g 'GROUP_NAME'

onde `TELEGRAM_TOKEN` é o token do seu bot, `MEETUP_KEY` a chave do Meetup e `GROUP_NAME` o nome do
grupo do Meetup onde o bot irá buscar os eventos.

O bot também pode ser executado definindo variáveis de ambiente

    $ export TELEGRAM_TOKEN='token do bot'
    $ export MEETUP_KEY='chave do meetup'
    $ export GROUP_NAME='grupo do meetup'
    $ gdgajubot

Usando as variáveis de ambiente, é possível pôr as credenciais em um arquivo separado e importar
para o shell antes de executar:

    $ . credenciais_bot
    $ gdgajubot -g 'GROUP_NAME'

### Testando

O `gdgajubot` é desenvolvido com testes automatizados, porém usando dados estáticos. Para verificar
se o seu bot está funcionando de verdade, inicie uma conversa com ele com um cliente Telegram.
Escreva `/events` ou `/book` e veja se ele responde.
