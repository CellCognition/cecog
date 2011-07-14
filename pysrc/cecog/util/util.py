"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

#-------------------------------------------------------------------------------
# standard library imports:
#

import logging, \
       types, \
       os, \
       bz2, \
       gzip

#-------------------------------------------------------------------------------
# extension module imports:
#

from pdk.options import Option
from pdk.optionmanagers import OptionManager
from pdk.platform import is_linux, is_mac, is_windows

#-------------------------------------------------------------------------------
# constants:
#
PACKAGE_PATH = ''

OS_WINDOWS = 'windows'
OS_MAC = 'mac'
OS_LINUX = 'linux'

#-------------------------------------------------------------------------------
# functions:
#

def singleton(cls):
    '''
    singleton class decorator
    Example:
    @singleton
    class Foo():
        pass

    foo1 = Foo()
    foo2 = Foo()
    assert foo1 is foo2
    '''
    instances = {}
    def getinstance(*args, **options):
        if cls not in instances:
            instances[cls] = cls(*args, **options)
        return instances[cls]
    return getinstance

def hexToRgb(string):
    hex = eval(string.replace('#','0x'))
    b = hex & 0xff
    g = hex >> 8 & 0xff
    r = hex >> 16 & 0xff
    return (r,g,b)

def rgbToHex(r,g,b, scale=1):
    r,g,b = [int(x*float(scale)) for x in (r,g,b)]
    return "#%s" % "".join(map(lambda c: hex(c)[2:].zfill(2), (r, g, b)))


def get_file_handle(filename, mode, guess_compression=True, compress_level=6):
    ext = os.path.splitext(filename)[1].lower()
    if guess_compression:
        if ext == '.gz':
            fh = gzip.GzipFile(filename, mode=mode,
                               compresslevel=compress_level)
        elif ext == '.bz2':
            fh = bz2.BZ2File(filename, mode=mode,
                             compresslevel=compress_level)
        else:
            fh = file(filename, mode)
    else:
        fh = file(filename, mode)
    return fh


def read_table(filename, has_column_names=True, skip=0, sep='\t',
               guess_compression=True):
    '''
    Reads a list of dicts ordered by header_names to file.
    Unfortunately Python's csv is unable of writing headers.
    '''
    f = get_file_handle(filename, 'rbU', guess_compression=guess_compression)
    for i in range(skip):
        f.readline()
    if has_column_names:
        column_names = f.readline().split(sep)
        column_names = [x.strip() for x in column_names]
    else:
        column_names = None
    rows = []
    for line in f:
        items = line.split(sep)
        items = [x.strip() for x in items]
        if column_names is None:
            column_names = range(len(items))
        rows.append(dict(zip(column_names, items)))
    f.close()
    return column_names, rows

def write_table(filename, rows, column_names=None, sep='\t',
                guess_compression=True):
    '''
    Write a list of dicts ordered by header_names to file, or a list of lists
    if no column_names are specified.

    Unfortunately Python's csv is unable of writing headers
    (changed in Python 2.7)
    '''
    f = get_file_handle(filename, 'wb', guess_compression=guess_compression)
    if not column_names is None:
        f.write('%s\n' % sep.join(column_names))
        for row in rows:
            f.write('%s\n' % sep.join([str(row[n]) for n in column_names]))
    else:
        for row in rows:
            if type(row) == types.DictType:
                func = lambda x: x.values()
            else:
                func = lambda x: x
            f.write('%s\n' % sep.join(map(str, func(row))))
    f.close()

def get_package_path():
    return PACKAGE_PATH

def set_package_path(name):
    global PACKAGE_PATH
    PACKAGE_PATH = name

def convert_package_path(path):
    return os.path.normpath(os.path.join(PACKAGE_PATH, path))

def unlist(a):
    b = []
    for x in a:
        b += x
    return b

def yesno(state):
    return 'yes' if state else 'no'

def resolve_os_name():
    os_str = None
    if is_windows:
        os_str = OS_WINDOWS
    elif is_mac:
        os_str = OS_MAC
    elif is_linux:
        os_str = OS_LINUX
    return os_str

def get_appdata_path():
    if is_windows:
        if 'APPDATA' in os.environ:
            path = os.environ['APPDATA']
        else:
            path = os.path.expanduser("~/Application Data")
    elif is_mac:
        path = os.path.expanduser("~/Library/Application Support")
    else:
        path = os.path.expanduser("~")
    return os.path.abspath(path)

#-------------------------------------------------------------------------------
# classes:
#


class ReverseDict(dict):

    def __init__(self, dataD={}):
        super(ReverseDict, self).__init__(dataD)
        self._reverseD = {}
        for k, v in self.iteritems():
            if not v in self._reverseD:
                self._reverseD[v] = k

    def __call__(self):
        return self._reverseD


class LoggerMixin(OptionManager):

    OPTIONS = {"strLoggerName": Option("", callback="_onLoggerName"),
              }

    def __init__(self, **dctOptions):
        super(LoggerMixin, self).__init__(**dctOptions)

    def _onLoggerName(self, strLoggerName):
        self.oLogger = logging.getLogger(strLoggerName)

