import datetime
import json
import logging
from typing import Dict

import threading

import requests
import requests.exceptions

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from bs4 import BeautifulSoup

from gdgajubot import util
from gdgajubot.data.database import db, orm, Message, User, Choice, ChoiceConverter, State, Group
from gdgajubot.util import StateDict, MissingDict


def json_encode(info):
    return JSONCodec().encode(info)


def json_decode(info):
    return JSONCodec().decode(info)


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

    def get_discounts(self):
        ''' 
        discountsglobal pode bloquear as requisições 
        Comentar linha caso aconteça
        '''
        # lista de funções de coleta
        site_functions = [
                self.__get_all_onlinetutorials_links,
                self.__get_all_discountsglobal_links, 
                self.__get_all_learnviral_links,
        ]

        # dict que irá receber os resultados das threads
        self.__coupon_results = {} 

        thread_list = []
        for f in site_functions:
            thread = threading.Thread(target=f)
            thread.start()
            thread_list.append(thread)
        [thread.join() for thread in thread_list]

        # remove cupons iguais e que não possuem desconto
        coupons_dict = {}
        for url,name in self.__coupon_results.items():
            if 'https://www.udemy.com/course/' and \
                '?couponCode=' not in url: # não possui desconto
                continue
            coupons_dict[url.strip()] = name.strip()
        del self.__coupon_results 

        return coupons_dict

    # função de coleta 1
    def __get_all_discountsglobal_links(self): 
        url = "http://udemycoupon.discountsglobal.com/coupon-category/free-2/"
        try:
            r = requests.get(url,headers=self.HEADERS)
            soup = BeautifulSoup(r.text,'html5lib')
            for div in soup.findAll('div',{'class':'item-panel'})[:7]:
                name = div.find('h3').find('a').text 
                name = name.replace('Discount: 100% off – ','')
                name = name.replace('Discount: 75% off – ','')
                name = name.replace('100% off ','')
                url = div.find('div',{'class':'link-holder'}).find('a').get('href') 
                self.__coupon_results.update({url:name})
        except Exception as e:
            print('get_all_discountsglobal_links',e)      

    # função de coleta 2
    def __get_all_learnviral_links(self): 
        url = "https://udemycoupon.learnviral.com/coupon-category/free100-discount/"
        try:
            r = requests.get(url,headers=self.HEADERS)
            soup = BeautifulSoup(r.text,'html5lib')
            titles = [
                title.text.replace('[Free]','') for title in \
                soup.findAll('h3',{'class':'entry-title'})
            ]
            urls = [
                a.get('href') for a in \
                soup.findAll('a',{'class':'coupon-code-link btn promotion'})
            ]
            self.__coupon_results.update({url:name for (url,name) in zip(urls[:7],titles[:7])})
        except Exception as e:
            print('get_all_learnviral_links',e)      

    # função de coleta 3
    def __get_all_onlinetutorials_links(self): 
        url = "https://onlinetutorials.org"
        try:
            r = requests.get(url,headers=self.HEADERS)
            soup = BeautifulSoup(r.text,'html5lib')
            titles = [
                title.find('a').text for title in \
                soup.findAll('h3',{'class':'entry-title'})
            ]
            urls = [
                a.get('href') for a in \
                soup.findAll('a',{'class':'coupon-code-link button promotion'})
            ]
            self.__coupon_results.update({url:name for (url,name) in zip(urls[:7],titles[:7])})
        except Exception as e:
            print('get_all_onlinetutorials_links',e)  

    @cache.cache('get_packt_free_book', expire=600)
    def get_packt_free_book(self):
        date_from = datetime.datetime.utcnow().date()
        date_to = date_from + datetime.timedelta(days=1)

        # Primeira requisição obtém o ID do livro do dia
        r = requests.get(
            url="https://services.packtpub.com/free-learning-v1/offers",
            params={
                "dateFrom": date_from.strftime("%Y-%m-%dT00:00:00.000Z"),
                "dateTo": date_to.strftime("%Y-%m-%dT00:00:00.000Z")
            },
        )
        book_id = r.json()['data'][0]['productId']

        # Segunda requisição obtém as informações do livro do dia
        r = requests.get(url="https://static.packt-cdn.com/products/%s/summary" % book_id)
        data = r.json()

        book = util.AttributeDict()
        book['name'] = data['title']
        book['summary'] = data['oneLiner']
        book['cover'] = data['coverImage']
        book['expires'] = datetime.datetime.combine(date_to, datetime.time.min).replace(tzinfo=util.UTC_TZ).timestamp()

        return book

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

    ChatState = dict

    @orm.db_session
    def set_state(self, state_id: str, chat_id: int, chat_state: ChatState):
        # to not dump memory-only state
        chat_state = chat_state.copy()
        chat_state.pop('__memory__', None)

        try:
            state = State[chat_id, state_id]
            info = json_decode(state.info)
            info.update(chat_state)
            state.info = json_encode(info)
        except orm.ObjectNotFound:
            State(telegram_id=chat_id, description=state_id, info=json_encode(chat_state))

    @orm.db_session
    def get_state(self, state_id: str, chat_id: int) -> ChatState:
        state = State.get(telegram_id=chat_id, description=state_id)
        if state:
            return json_decode(state.info)
        return {}

    @orm.db_session
    def update_states(self, states: Dict[str, Dict[int, ChatState]]):
        for state_id, data in states.items():
            for chat_id, chat_state in data.items():
                self.set_state(state_id, chat_id, chat_state)

    @orm.db_session
    def load_states(self) -> Dict[str, Dict[int, ChatState]]:
        states = MissingDict(
            lambda state_id: MissingDict(
                lambda chat_id: self.__state_dict(state_id, chat_id,
                                                  self.get_state(state_id, chat_id))
            )
        )

        for state in State.select():
            state_id, chat_id, info = state.description, state.telegram_id, state.info
            states[state_id][chat_id] = self.__state_dict(state_id, chat_id, json_decode(info))

        return states

    def __state_dict(self, state_id, chat_id, data):
        # reserve a memory-only key
        if '__memory__' not in data:
            data['__memory__'] = {}

        return StateDict(
            data, dump_function=lambda state: self.set_state(state_id, chat_id, state)
        )

    @cache.cache('db.get_group', expire=600)
    @orm.db_session
    def get_group(self, group_id: int, group_name: str) -> Group:
        return self.__get_group(group_id, group_name)

    def __get_group(self, group_id, group_name):
        try:
            return Group[group_id]
        except orm.ObjectNotFound:
            return Group(telegram_id=group_id, telegram_groupname=group_name)

    @orm.db_session
    def set_group(self, group_id: int, group_name: str, **kwargs):
        if not kwargs:
            return

        group = self.__get_group(group_id, group_name)
        for k, v in kwargs.items():
            setattr(group, k, v)

        self.cache.invalidate(self.get_group, "db.get_group")

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


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


class JSONCodec:
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return {'__datetime__': obj.strftime(DATETIME_FORMAT)}
            return super().default(obj)

    class Decoder(json.JSONDecoder):
        def __init__(self):
            super().__init__(object_hook=self.object_hook)

        @staticmethod
        def object_hook(obj):
            if '__datetime__' in obj:
                return datetime.datetime.strptime(obj['__datetime__'], DATETIME_FORMAT)
            return obj

    # singleton
    def __new__(cls, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
            cls.instance.encode = cls.Encoder().encode
            cls.instance.decode = cls.Decoder().decode
        return cls.instance
