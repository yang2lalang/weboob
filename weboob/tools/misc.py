# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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


from time import time, sleep
import locale
import os
import sys
import traceback
import types
# keep compatibility
from .compat import unicode


__all__ = ['get_backtrace', 'get_bytes_size', 'iter_fields',
            'to_unicode', 'limit', 'find_exe']


def get_backtrace(empty="Empty backtrace."):
    """
    Try to get backtrace as string.
    Returns "Error while trying to get backtrace" on failure.
    """
    try:
        info = sys.exc_info()
        trace = traceback.format_exception(*info)
        sys.exc_clear()
        if trace[0] != "None\n":
            return "".join(trace)
    except:
        return "Error while trying to get backtrace"
    return empty


def get_bytes_size(size, unit_name):
    r"""Converts a unit and a number into a number of bytes.

    >>> get_bytes_size(2, 'KB')
    2048.0
    """
    unit_data = {
        'bytes': 1,
        'KB': 1024,
        'KiB': 1024,
        'MB': 1024 * 1024,
        'MiB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'GiB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024,
        'TiB': 1024 * 1024 * 1024 * 1024,
        }
    return float(size * unit_data.get(unit_name, 1))


def iter_fields(obj):
    for attribute_name in dir(obj):
        if attribute_name.startswith('_'):
            continue
        attribute = getattr(obj, attribute_name)
        if not isinstance(attribute, types.MethodType):
            yield attribute_name, attribute


def to_unicode(text):
    r"""
    >>> to_unicode('ascii')
    u'ascii'
    >>> to_unicode(u'utf\xe9'.encode('UTF-8'))
    u'utf\xe9'
    >>> to_unicode(u'unicode')
    u'unicode'
    """
    if isinstance(text, unicode):
        return text
    if not isinstance(text, str):
        try:
            text = str(text)
        except UnicodeError:
            return unicode(text)
    try:
        return unicode(text, 'utf-8')
    except UnicodeError:
        try:
            return unicode(text, 'iso-8859-15')
        except UnicodeError:
            return unicode(text, 'windows-1252', 'replace')


def guess_encoding(stdio):
    try:
        encoding = stdio.encoding or locale.getpreferredencoding()
    except AttributeError:
        encoding = None
    # ASCII or ANSII is most likely a user mistake
    if not encoding or encoding.lower() == 'ascii' or encoding.lower().startswith('ansi'):
        encoding = 'UTF-8'
    return encoding


def limit(iterator, lim):
    """Iterate on the lim first elements of iterator."""
    count = 0
    iterator = iter(iterator)
    while count < lim:
        yield iterator.next()
        count += 1


def ratelimit(group, delay):
    """
    Simple rate limiting.

    Waits if the last call of lastlimit with this group name was less than
    delay seconds ago. The rate limiting is global, shared between any instance
    of the application and any call to this function sharing the same group
    name. The same group name should not be used with different delays.

    This function is intended to be called just before the code that should be
    rate-limited.

    This function is not thread-safe. For reasonably non-critical rate
    limiting (like accessing a website), it should be sufficient nevertheless.

    @param group [string]  rate limiting group name, alphanumeric
    @param delay [int]  delay in seconds between each call
    """

    from tempfile import gettempdir
    path = os.path.join(gettempdir(), 'weboob_ratelimit.%s' % group)
    while True:
        try:
            offset = time() - os.stat(path).st_mtime
        except OSError:
            with open(path, 'w'):
                pass
            offset = 0

        if delay < offset:
            break

        sleep(delay - offset)

    os.utime(path, None)


def find_exe(basename):
    """
    Find the path to an executable by its base name (such as 'gpg').

    The executable can be overriden using an environment variable in the form
    `NAME_EXECUTABLE` where NAME is the specified base name in upper case.

    If the environment variable is not provided, the PATH will be searched
    both without and with a ".exe" suffix for Windows compatibility.

    If the executable can not be found, None is returned.
    """

    env_exe = os.getenv('%s_EXECUTABLE' % basename.upper())
    if env_exe and os.path.exists(env_exe) and os.access(env_exe, os.X_OK):
        return env_exe

    paths = os.getenv('PATH', os.defpath).split(os.pathsep)
    for path in paths:
        for ex in (basename, basename + '.exe'):
            fpath = os.path.join(path, ex)
            if os.path.exists(fpath) and os.access(fpath, os.X_OK):
                return fpath

