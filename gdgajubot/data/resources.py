import datetime
import logging
import requests
import requests.exceptions

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from bs4 import BeautifulSoup

from gdgajubot import util
from gdgajubot.data.database import db, orm, Message, User, Choice, ChoiceConverter, State


class Resources:
    BOOK_URL = "https://www.packtpub.com/packt/offers/free-learning"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/51.0.2704.79 Safari/537.36"
    }

    # Configuring cache
    cache = CacheManager(
        **parse_cache_config_options({'cache.type': 'memory'}))

    def __init__(self, config):
        self.config = config
        self.db = self.__initialize_database(**config.database)

        # create delegate method based on choice
        if 'meetup' in config.events_source:
            self.generate_events = self.meetup_events
        else:
            self.generate_events = self.facebook_events

    def __initialize_database(self, **config):
        db.bind(**config)
        db.provider.converter_classes.append((Choice, ChoiceConverter))
        db.generate_mapping(create_tables=True)
        return db

    @cache.cache('get_events', expire=60)
    def get_events(self, list_size=5):
        return list(self.generate_events(list_size))

    def meetup_events(self, n):
        """Obtém eventos do Meetup."""
        # api v3 base url
        all_events = []
        for group in self.config.group_name:
            url = "https://api.meetup.com/{group}/events".format(
                group=group
            )

            # response for the events
            r = requests.get(url, params={
                'key': self.config.meetup_key,
                'status': 'upcoming',
                'only': 'name,time,link',  # filter response to these fields
                'page': n,                 # limit to n events
            })

            # API output
            events = r.json()

            for event in events:
                # convert time returned by Meetup API
                event['time'] = datetime.datetime.fromtimestamp(
                    event['time'] / 1000, tz=util.AJU_TZ)
                # shorten url!
                event['link'] = self.get_short_url(event['link'])

            all_events.extend(events)
        return sorted(all_events, key=lambda x: x['time'])

    def facebook_events(self, n):
        """Obtém eventos do Facebook."""
        all_events = []
        for group in self.config.group_name:
            # api v2.8 base url
            url = "https://graph.facebook.com/v2.8/%s/events" % group

            # response for the events
            r = requests.get(url, params={
                'access_token': self.config.facebook_key,
                'since': 'today',
                'fields': 'name,start_time',  # filter response to these fields
                'limit': n,                   # limit to n events
            })

            # API output
            events = r.json().get('data', [])

            for event in events:
                # convert time returned by Facebook API
                event['time'] = datetime.datetime.strptime(
                    event.pop('start_time'), "%Y-%m-%dT%H:%M:%S%z")
                # create event link
                link = "https://www.facebook.com/events/%s" % event.pop('id')
                # shorten url!
                event['link'] = self.get_short_url(link)
            all_events.extend(events)

        return sorted(all_events, key=lambda x: x['time'])

    @cache.cache('get_packt_free_book', expire=600)
    def get_packt_free_book(self):
        r = requests.get(self.BOOK_URL, headers=self.HEADERS)
        return self.extract_packt_free_book(r.content, r.encoding)

    @staticmethod
    def extract_packt_free_book(content, encoding='utf-8'):
        if hasattr(content, 'read'):    # file-type
            content = content.read()
        if isinstance(content, bytes):  # convert to str
            content = content.decode(encoding)

        # Extracting information with html parser
        page = BeautifulSoup(content, 'html.parser')
        dealoftheday = page.select_one(
            '#deal-of-the-day div div div:nth-of-type(2)')

        if not dealoftheday:
            return None

        book = util.AttributeDict()
        try:
            book['name'] = dealoftheday.select_one(
                'div:nth-of-type(2) h2').text.strip()
            book['summary'] = dealoftheday.select_one(
                'div:nth-of-type(3)').text.strip()
            book['expires'] = int(dealoftheday.select_one(
                'span.packt-js-countdown').attrs['data-countdown-to']
            )
            image_source = page.select_one(
                '#deal-of-the-day > div > div > '
                'div.dotd-main-book-image.float-left > a > img'
            ).attrs.get('data-original', None)
            if image_source and image_source.startswith('//'):
                image_source = 'https:{0}'.format(image_source)
            book['cover'] = image_source
            return book
        except:
            return None

    @cache.cache('get_short_url')
    def get_short_url(self, long_url):
        # Faz a requisição da URL curta somente se houver uma key configurada
        if self.config.url_shortener_key:
            r = requests.post(
                "https://www.googleapis.com/urlshortener/v1/url",
                params={
                    'key': self.config.url_shortener_key,
                    'fields': 'id'
                },
                json={'longUrl': long_url}
            )
            if r.status_code == 200:
                return r.json()['id']
            else:
                logging.exception(r.text)

        # Caso tenha havido algum problema usa a própria URL longa
        return long_url

    @orm.db_session
    def last_book_sent(self, chat_id: int, chat_name: str = None, update=False) -> datetime.datetime:
        description = 'daily:/book'
        if update:
            now = datetime.datetime.now(util.UTC_TZ)
            state = State.get(telegram_id=chat_id, description=description)

            if state:
                state.moment = now
            else:
                State(telegram_id=chat_id, description=description, moment=now,
                      info={'chat': chat_name} if chat_name else None)
        else:
            moment = State.get_moment(chat_id, description)
            if moment:
                return moment.astimezone(util.UTC_TZ)

    @orm.db_session
    def log_message(self, message, *args, **kwargs):
        try:
            user = User[message.from_user.id]
        except orm.ObjectNotFound:
            user = User(
                telegram_id=message.from_user.id,
                telegram_username=message.from_user.name,
            )
        message = Message(
            sent_by=user, text=message.text, sent_at=message.date,
        )
        print(
            'Logging message: {}'.format(message),
        )

    @orm.db_session
    def list_all_users(self):
        users = User.select().order_by(User.telegram_username)[:]
        return tuple(users)

    @orm.db_session
    def is_user_admin(self, user_id):
        try:
            user = User[user_id]
        except orm.ObjectNotFound:
            return False
        return user.is_bot_admin
