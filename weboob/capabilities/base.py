# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Christophe Benz, Romain Bignon, Julien Hebert
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import warnings
import re
from decimal import Decimal
from copy import deepcopy, copy

from weboob.tools.compat import unicode, long
from weboob.tools.misc import to_unicode
from weboob.tools.ordereddict import OrderedDict


__all__ = ['UserError', 'FieldNotFound', 'NotAvailable',
           'NotLoaded', 'Capability', 'Field', 'IntField', 'DecimalField',
           'FloatField', 'StringField', 'BytesField',
           'empty', 'BaseObject']


def enum(**enums):
    _values = enums.values()
    _keys = enums.keys()
    _items = enums.items()
    _types = list((type(value) for value in enums.values()))
    _index = dict((value if not isinstance(value, dict) else value.itervalues().next(), i) for i, value in enumerate(enums.values()))

    enums['keys'] = _keys
    enums['values'] = _values
    enums['items'] = _items
    enums['index'] = _index
    enums['types'] = _types
    return type('Enum', (), enums)


def empty(value):
    """
    Checks if a value is empty (None, NotLoaded or NotAvailable).

    :rtype: :class:`bool`
    """
    for cls in (None, NotLoaded, NotAvailable):
        if value is cls:
            return True
    return False


def find_object(mylist, error=None, **kwargs):
    """
    Very simple tools to return an object with the matching parameters in
    kwargs.
    """
    for a in mylist:
        found = True
        for key, value in kwargs.iteritems():
            if getattr(a, key) != value:
                found = False
                break
        if found:
            return a

    if error is not None:
        raise error()
    return None


class UserError(Exception):
    """
    Exception containing an error message for user.
    """


class FieldNotFound(Exception):
    """
    A field isn't found.

    :param obj: object
    :type obj: :class:`BaseObject`
    :param field: field not found
    :type field: :class:`Field`
    """

    def __init__(self, obj, field):
        Exception.__init__(self,
                           u'Field "%s" not found for object %s' % (field, obj))


class ConversionWarning(UserWarning):
    """
    A field's type was changed when setting it.
    Ideally, the module should use the right type before setting it.
    """
    pass


class AttributeCreationWarning(UserWarning):
    """
    A non-field attribute has been created with a name not
    prefixed with a _.
    """


class NotAvailableType(object):
    """
    NotAvailable is a constant to use on non available fields.
    """

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self):
        return 'NotAvailable'

    def __unicode__(self):
        return u'Not available'

    def __nonzero__(self):
        return False

NotAvailable = NotAvailableType()


class NotLoadedType(object):
    """
    NotLoaded is a constant to use on not loaded fields.

    When you use :func:`weboob.tools.backend.Module.fillobj` on a object based on :class:`BaseObject`,
    it will request all fields with this value.
    """

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self):
        return 'NotLoaded'

    def __unicode__(self):
        return u'Not loaded'

    def __nonzero__(self):
        return False

NotLoaded = NotLoadedType()


class Capability(object):
    """
    This is the base class for all capabilities.

    A capability may define abstract methods (which raise :class:`NotImplementedError`)
    with an explicit docstring to tell backends how to implement them.

    Also, it may define some *objects*, using :class:`BaseObject`.
    """


class Field(object):
    """
    Field of a :class:`BaseObject` class.

    :param doc: docstring of the field
    :type doc: :class:`str`
    :param args: list of types accepted
    :param default: default value of this field. If not specified, :class:`NotLoaded` is used.
    """
    _creation_counter = 0

    def __init__(self, doc, *args, **kwargs):
        self.types = ()
        self.value = kwargs.get('default', NotLoaded)
        self.doc = doc

        for arg in args:
            if isinstance(arg, type) or isinstance(arg, str):
                self.types += (arg,)
            else:
                raise TypeError('Arguments must be types or strings of type name')

        self._creation_counter = Field._creation_counter
        Field._creation_counter += 1

    def convert(self, value):
        """
        Convert value to the wanted one.
        """
        return value


class IntField(Field):
    """
    A field which accepts only :class:`int` and :class:`long` types.
    """

    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, int, long, **kwargs)

    def convert(self, value):
        return int(value)


class DecimalField(Field):
    """
    A field which accepts only :class:`decimal` type.
    """

    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, Decimal, **kwargs)

    def convert(self, value):
        if isinstance(value, Decimal):
            return value
        return Decimal(value)


class FloatField(Field):
    """
    A field which accepts only :class:`float` type.
    """

    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, float, **kwargs)

    def convert(self, value):
        return float(value)


class StringField(Field):
    """
    A field which accepts only :class:`unicode` strings.
    """

    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, unicode, **kwargs)

    def convert(self, value):
        return to_unicode(value)


class BytesField(Field):
    """
    A field which accepts only :class:`str` strings.
    """

    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, str, **kwargs)

    def convert(self, value):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return str(value)


class _BaseObjectMeta(type):
    def __new__(cls, name, bases, attrs):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in attrs.items() if isinstance(obj, Field)]
        fields.sort(key=lambda x: x[1]._creation_counter)

        new_class = super(_BaseObjectMeta, cls).__new__(cls, name, bases, attrs)
        if new_class._fields is None:
            new_class._fields = OrderedDict()
        else:
            new_class._fields = deepcopy(new_class._fields)
        new_class._fields.update(fields)

        if new_class.__doc__ is None:
            new_class.__doc__ = ''
        for name, field in fields:
            doc = '(%s) %s' % (', '.join([':class:`%s`' % v.__name__ if isinstance(v, type) else v for v in field.types]), field.doc)
            if field.value is not NotLoaded:
                doc += ' (default: %s)' % field.value
            new_class.__doc__ += '\n:var %s: %s' % (name, doc)
        return new_class


class BaseObject(object):
    """
    This is the base class for a capability object.

    A capability interface may specify to return several kind of objects, to formalise
    retrieved information from websites.

    As python is a flexible language where variables are not typed, we use a system to
    force backends to set wanted values on all fields. To do that, we use the :class:`Field`
    class and all derived ones.

    For example::

        class Transfer(BaseObject):
            " Transfer from an account to a recipient.  "

            amount =    DecimalField('Amount to transfer')
            date =      Field('Date of transfer', basestring, date, datetime)
            origin =    Field('Origin of transfer', int, long, basestring)
            recipient = Field('Recipient', int, long, basestring)

    The docstring is mandatory.
    """

    __metaclass__ = _BaseObjectMeta

    id = None
    backend = None
    url = StringField('url')
    _fields = None

    def __init__(self, id=u'', url=NotLoaded, backend=None):
        self.id = to_unicode(id)
        self.backend = backend
        self._fields = deepcopy(self._fields)
        self.__setattr__('url', url)

    @property
    def fullid(self):
        """
        Full ID of the object, in form '**ID@backend**'.
        """
        return '%s@%s' % (self.id, self.backend)

    def __iscomplete__(self):
        """
        Return True if the object is completed.

        It is usefull when the object is a field of an other object which is
        going to be filled.

        The default behavior is to iter on fields (with iter_fields) and if
        a field is NotLoaded, return False.
        """
        for key, value in self.iter_fields():
            if value is NotLoaded:
                return False
        return True

    def copy(self):
        obj = copy(self)
        obj._fields = copy(self._fields)
        return obj

    def __deepcopy__(self, memo):
        return self.copy()

    def set_empty_fields(self, value, excepts=()):
        """
        Set the same value on all empty fields.

        :param value: value to set on all empty fields
        :param excepts: if specified, do not change fields listed
        """
        for key, old_value in self.iter_fields():
            if empty(old_value) and key not in excepts:
                setattr(self, key, value)

    def iter_fields(self):
        """
        Iterate on the fields keys and values.

        Can be overloaded to iterate on other things.

        :rtype: iter[(key, value)]
        """

        if hasattr(self, 'id') and self.id is not None:
            yield 'id', self.id
        for name, field in self._fields.iteritems():
            yield name, field.value

    def __eq__(self, obj):
        if isinstance(obj, BaseObject):
            return self.backend == obj.backend and self.id == obj.id
        else:
            return False

    def __getattr__(self, name):
        if self._fields is not None and name in self._fields:
            return self._fields[name].value
        else:
            raise AttributeError("'%s' object has no attribute '%s'" % (
                self.__class__.__name__, name))

    def __setattr__(self, name, value):
        try:
            attr = (self._fields or {})[name]
        except KeyError:
            if name not in dir(self) and not name.startswith('_'):
                warnings.warn('Creating a non-field attribute %s. Please prefix it with _' % name,
                              AttributeCreationWarning, stacklevel=2)
            object.__setattr__(self, name, value)
        else:
            if not empty(value):
                try:
                    # Try to convert value to the wanted one.
                    nvalue = attr.convert(value)
                    # If the value was converted
                    if nvalue is not value:
                        warnings.warn('Value %s was converted from %s to %s' %
                                      (name, type(value), type(nvalue)),
                                      ConversionWarning, stacklevel=2)
                    value = nvalue
                except Exception:
                    # error during conversion, it will probably not
                    # match the wanted following types, so we'll
                    # raise ValueError.
                    pass
            from collections import deque
            actual_types = ()
            for v in attr.types:
                if isinstance(v, str):
                    # the following is a (almost) copy/paste from
                    # https://stackoverflow.com/questions/11775460/lexical-cast-from-string-to-type
                    q = deque([object])
                    while q:
                        t = q.popleft()
                        if t.__name__ == v:
                            actual_types += (t,)
                        else:
                            try:
                                # keep looking!
                                q.extend(t.__subclasses__())
                            except TypeError:
                                # type.__subclasses__ needs an argument for
                                # whatever reason.
                                if t is type:
                                    continue
                                else:
                                    raise
                else:
                    actual_types += (v,)

            if not isinstance(value, actual_types) and not empty(value):
                raise ValueError(
                    'Value for "%s" needs to be of type %r, not %r' % (
                        name, actual_types, type(value)))
            attr.value = value

    def __delattr__(self, name):
        try:
            self._fields.pop(name)
        except KeyError:
            object.__delattr__(self, name)

    def to_dict(self):
        def iter_decorate(d):
            for key, value in d:
                if key == 'id' and self.backend is not None:
                    value = self.fullid
                yield key, value

        fields_iterator = self.iter_fields()
        return OrderedDict(iter_decorate(fields_iterator))

    @classmethod
    def from_dict(cls, values, backend=None):
        self = cls()

        for attr in values:
            setattr(self, attr, values[attr])

        return self


class Currency(object):
    CURRENCIES = {u'EUR': (u'€', u'EURO'),
                  u'CHF': (u'CHF',),
                  u'USD': (u'$',),
                  u'GBP': (u'£',),
                  u'LBP': (u'ل.ل',),
                  u'AED': (u'AED',),
                  u'XOF': (u'XOF',),
                  u'RUB': (u'руб',),
                  u'SGD': (u'SGD',),
                  u'BRL': (u'R$',),
                  u'MXN': (u'$',),
                  u'JPY': (u'¥',),
                  u'TRY': (u'₺',),
                  u'RON': (u'lei',),
                  u'COP': (u'$',),
                  u'NOK': (u'kr',),
                  u'CNY': (u'¥',),
                  u'RSD': (u'din',),
                  u'ZAR': (u'rand',),
                  u'MYR': (u'RM',),
                  u'HUF': (u'Ft',),
                  u'HKD': (u'HK$',),
                  u'QAR': (u'QR',),
                  u'MAD': (u'MAD',),
                  u'ARS': (u'ARS',),
                  u'AUD': (u'AUD',),
                  u'CAD': (u'CAD',),
                  u'NZD': (u'NZD',),
                  u'BHD': (u'BHD',),
                  u'SEK': (u'SEK',),
                  u'DKK': (u'DKK',),
                  u'LUF': (u'F', u'fr.', u'LUF',),
                  u'KZT': (u'KZT',),
                  u'PLN': (u'PLN',),
                  u'ILS': (u'ILS',),
                  u'THB': (u'THB',),
                 }

    EXTRACTOR = re.compile(r'[\d\s,\.\-]', re.UNICODE)

    @classmethod
    def get_currency(klass, text):
        u"""
        >>> Currency.get_currency(u'42')
        None
        >>> Currency.get_currency(u'42 €')
        u'EUR'
        >>> Currency.get_currency(u'$42')
        u'USD'
        >>> Currency.get_currency(u'42.000,00€')
        u'EUR'
        >>> Currency.get_currency(u'$42 USD')
        u'USD'
        >>> Currency.get_currency(u'%42 USD')
        u'USD'
        >>> Currency.get_currency(u'US1D')
        None
        """
        curtexts = klass.EXTRACTOR.sub(' ', text.upper()).split()
        for curtext in curtexts:
            for currency, symbols in klass.CURRENCIES.iteritems():
                if curtext in currency:
                    return currency
                for symbol in symbols:
                    if curtext in symbol or symbol in curtext:
                        return currency
        return None

    @classmethod
    def currency2txt(klass, currency):
        _currency = klass.CURRENCIES.get(currency, (u' '))
        return _currency[0]
