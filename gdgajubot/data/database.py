from collections.abc import Mapping
from datetime import datetime
from pony import orm
from pony.utils import throw

db = orm.Database()


class Choice(orm.Required):
    __slots__ = ('__choices',)
    def __init__(self, *args, choices=None, **kwargs):
        if not choices or not isinstance(choices, Mapping):
            throw(
                ValueError,
                'Choices argument must be a Mapping (dict) of sql_value: display_value instance'
            )
        if any(not isinstance(value, str) for value in choices):
            throw(
                ValueError,
                'Choices only support strings for sql_value',
            )
        super().__init__(str, *args, **kwargs)
        self.__choices = dict(**choices)

    def validate(self, val, *args, **kwargs):
        val = super().validate(val, *args, **kwargs)
        if val not in self.__choices.values():
            throw(
                ValueError,
                'Choice {} is not valid. Valid choices are {}.'.format(
                    val, self.__choices.values(),
                )
            )
        return val

    def get_display_value(self, sql_value):
        return self.__choices['sql_value']

    def get_sql_value(self, display_value):
        try:
            value = next(
                value for key, value in self.__choices.items()
                if value == display_value
            )
            return str(value)
        except StopIteration:
            return None


class ChoiceConverter(orm.dbapiprovider.StrConverter):
    def validate(self, val):
        if not isinstance(val, Choice):
            throw(ValueError, 'Must be a Choice. Got {}'.format(type(val)))
        return val

    def py2sql(self, val):
        return val.name

    def sql2py(self, value):
        # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
        return self.py_type[value]


class User(db.Entity):
    telegram_id = orm.PrimaryKey(int)
    telegram_username = orm.Required(str)
    is_bot_admin = orm.Required(bool, default=False)
    messages = orm.Set('Message')

    def __str__(self):
        return 'User - @{}'.format(self.telegram_username)


class Message(db.Entity):
    text = orm.Required(str)
    sent_at = orm.Required(datetime)
    sent_by = orm.Required(User)

    def __str__(self):
        return 'Message - {} @ {}: {}'.format(
            self.sent_by.telegram_username,
            self.sent_at.strftime('%c'),
            self.text,
        )


class Group(db.Entity):
    telegram_id = orm.PrimaryKey(int, size=64)
    telegram_groupname = orm.Optional(str)

    def __str__(self):
        return 'Group - {}'.format(self.telegram_groupname)


class State(db.Entity):
    telegram_id = orm.Required(int, size=64)
    description = orm.Required(str)
    moment = orm.Required(datetime)
    info = orm.Optional(orm.Json)
    orm.composite_key(telegram_id, description)

    @classmethod
    @orm.db_session
    def get_moment(cls, telegram_id, description):
        try:
            return db.get('SELECT moment FROM State WHERE telegram_id = $telegram_id AND description = $description')
        except orm.RowNotFound:
            return None

    def __str__(self):
        return 'State - "{}" : {}'.format(self.description, self.telegram_group)
