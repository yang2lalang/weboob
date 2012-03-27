# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz, Romain Bignon
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
import datetime
from copy import deepcopy

from weboob.tools.misc import to_unicode
from weboob.tools.ordereddict import OrderedDict


__all__ = ['FieldNotFound', 'NotAvailable', 'NotLoaded', 'IBaseCap',
           'Field', 'IntField', 'FloatField', 'StringField', 'BytesField',
           'DateField', 'DeltaField', 'CapBaseObject', 'empty']


def empty(value):
    """
    Checks if a value is empty (None, NotLoaded or NotAvailable).

    :rtype: :class:`bool`
    """
    for cls in (None, NotLoaded, NotAvailable):
        if value is cls:
            return True
    return False


class FieldNotFound(Exception):
    """
    A field isn't found.

    :param obj: object
    :type obj: :class:`CapBaseObject`
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

class NotAvailableMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Not available'

    def __nonzero__(self):
        return False


class NotAvailable(object):
    """
    Constant to use on non available fields.
    """
    __metaclass__ = NotAvailableMeta


class NotLoadedMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Not loaded'

    def __nonzero__(self):
        return False


class NotLoaded(object):
    """
    Constant to use on not loaded fields.

    When you use :func:`weboob.tools.backend.BaseBackend.fillobj` on a object based on :class:`CapBaseObject`,
    it will request all fields with this value.
    """
    __metaclass__ = NotLoadedMeta


class IBaseCap(object):
    """
    This is the base class for all capabilities.

    A capability may define abstract methods (which raise :class:`NotImplementedError`)
    with an explicit docstring to tell backends how to implement them.

    Also, it may define some *objects*, using :class:`CapBaseObject`.
    """


class Field(object):
    """
    Field of a :class:`CapBaseObject` class.

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
            if isinstance(arg, type):
                self.types += (arg,)
            else:
                raise TypeError('Arguments must be types')

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

class DateField(Field):
    """
    A field which accepts only :class:`datetime.date` and :class:`datetime.datetime` types.
    """
    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, datetime.date, datetime.datetime, **kwargs)

class TimeField(Field):
    """
    A field which accepts only :class:`datetime.time` and :class:`datetime.time` types.
    """
    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, datetime.time, datetime.datetime, **kwargs)

class DeltaField(Field):
    """
    A field which accepts only :class:`datetime.timedelta` type.
    """
    def __init__(self, doc, **kwargs):
        Field.__init__(self, doc, datetime.timedelta, **kwargs)

class _CapBaseObjectMeta(type):
    def __new__(cls, name, bases, attrs):
        fields = [(field_name, attrs.pop(field_name)) for field_name, obj in attrs.items() if isinstance(obj, Field)]
        fields.sort(key=lambda x: x[1]._creation_counter)

        new_class = super(_CapBaseObjectMeta, cls).__new__(cls, name, bases, attrs)
        if new_class._fields is None:
            new_class._fields = OrderedDict()
        else:
            new_class._fields = deepcopy(new_class._fields)
        new_class._fields.update(fields)

        if new_class.__doc__ is None:
            new_class.__doc__ = ''
        for name, field in fields:
            doc = '(%s) %s' % (', '.join([':class:`%s`' % v.__name__ for v in field.types]), field.doc)
            if field.value is not NotLoaded:
                doc += ' (default: %s)' % field.value
            new_class.__doc__ += '\n:var %s: %s' % (name, doc)
        return new_class

class CapBaseObject(object):
    """
    This is the base class for a capability object.

    A capability interface may specify to return several kind of objects, to formalise
    retrieved information from websites.

    As python is a flexible language where variables are not typed, we use a system to
    force backends to set wanted values on all fields. To do that, we use the :class:`Field`
    class and all derived ones.

    For example::

        class Transfer(CapBaseObject):
            " Transfer from an account to a recipient.  "

            amount =    FloatField('Amount to transfer')
            date =      Field('Date of transfer', basestring, date, datetime)
            origin =    Field('Origin of transfer', int, long, basestring)
            recipient = Field('Recipient', int, long, basestring)

    The docstring is mandatory.
    """

    __metaclass__ = _CapBaseObjectMeta
    _fields = None

    def __init__(self, id, backend=None):
        self.id = to_unicode(id)
        self.backend = backend
        self._fields = deepcopy(self._fields)

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

        yield 'id', self.id
        for name, field in self._fields.iteritems():
            yield name, field.value

    def __eq__(self, obj):
        if isinstance(obj, CapBaseObject):
            return self.backend == obj.backend and self.id == obj.id
        else:
            return False

    def __getattr__(self, name):
        if self._fields is not None and name in self._fields:
            return self._fields[name].value
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (
                self.__class__.__name__, name)

    def __setattr__(self, name, value):
        try:
            attr = (self._fields or {})[name]
        except KeyError:
            object.__setattr__(self, name, value)
        else:
            if not empty(value):
                try:
                    # Try to convert value to the wanted one.
                    nvalue = attr.convert(value)
                    # If the value was converted
                    if nvalue is not value:
                        warnings.warn('Value %s was converted from %s to %s' %
                            (name, type(value), type(nvalue)), ConversionWarning, stacklevel=2)
                    value = nvalue
                except Exception:
                    # error during conversion, it will probably not
                    # match the wanted following types, so we'll
                    # raise ValueError.
                    pass

            if not isinstance(value, attr.types) and not empty(value):
                raise ValueError(
                    'Value for "%s" needs to be of type %r, not %r' % (
                        name, attr.types, type(value)))
            attr.value = value
