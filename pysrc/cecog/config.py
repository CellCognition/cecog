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

__all__ = ['NAMING_SCHEMAS',
           'ANALYZER_CONFIG',
           'PATH_MAPPER',
           'RESOURCE_PATH',
           'map_path_to_os',
           'is_path_mappable',
           'init_constants',
           'init_application_support_path',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import os
import shutil
from ConfigParser import RawConfigParser

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.fileutils import safe_mkdirs
from pdk.platform import (is_mac,
                          is_windows,
                          is_linux,
                          )

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.util.util import (read_table,
                             write_table,
                             get_appdata_path,
                             )
from cecog.util.mapping import map_path_to_os as _map_path_to_os

#-------------------------------------------------------------------------------
# constants:
#
RESOURCE_PATH            = 'resources'
if not os.path.isdir(RESOURCE_PATH):
    RESOURCE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'apps',
                                 'CecogAnalyzer', 'resources')
    if not os.path.isdir(RESOURCE_PATH):
        raise IOError("Resource path '%s' not found." % RESOURCE_PATH)

R_SOURCE_PATH = os.path.join(RESOURCE_PATH, 'rsrc')
if not os.path.isdir(R_SOURCE_PATH):
    R_SOURCE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'rsrc')
    if not os.path.isdir(R_SOURCE_PATH):
        raise IOError("R-source path '%s' not found." % R_SOURCE_PATH)


# forward declarations defined in init_constants() (called upon import of cecog)
APPLICATION_SUPPORT_PATH = None
ANALYZER_CONFIG_FILENAME = None
NAMING_SCHEMA_FILENAME   = None
PATH_MAPPING_FILENAME    = None
FONT12_FILENAME          = None

NAMING_SCHEMAS = None
ANALYZER_CONFIG = None
PATH_MAPPER = None
map_path_to_os = None
is_path_mappable = None

#-------------------------------------------------------------------------------
# functions:
#
def init_application_support_path2():
    global APPLICATION_SUPPORT_PATH
    folder = 'CellCognition'
    if APPLICATION_SUPPORT_PATH is None:
        path = get_appdata_path()
        if is_mac or is_windows:
            path = os.path.join(path, folder)
        else:
            path = os.path.join(path, '.%s' % folder.lower())
        safe_mkdirs(path)
        APPLICATION_SUPPORT_PATH = path
    return APPLICATION_SUPPORT_PATH

def init_application_support_path(version=''):
    global APPLICATION_SUPPORT_PATH
    folder = 'CellCognition%s' % version
    if APPLICATION_SUPPORT_PATH is None:
        path = get_appdata_path()
        if is_mac or is_windows:
            path = os.path.join(path, folder)
        else:
            path = os.path.join(path, '.%s' % folder.lower())
        safe_mkdirs(path)
        APPLICATION_SUPPORT_PATH = path

def get_application_support_path():
    return APPLICATION_SUPPORT_PATH

def get_package_path():
    return PACKAGE_PATH


def init_constants():
    global ANALYZER_CONFIG_FILENAME
    ANALYZER_CONFIG_FILENAME = _copy_check_file(RESOURCE_PATH,
                                                APPLICATION_SUPPORT_PATH,
                                                'config.ini')
    global NAMING_SCHEMA_FILENAME
    NAMING_SCHEMA_FILENAME = _copy_check_file(RESOURCE_PATH,
                                              APPLICATION_SUPPORT_PATH,
                                              'naming_schemas.ini')
    global PATH_MAPPING_FILENAME
    PATH_MAPPING_FILENAME = _copy_check_file(RESOURCE_PATH,
                                             APPLICATION_SUPPORT_PATH,
                                             'path_mappings.txt')
    global FONT12_FILENAME
    FONT12_FILENAME = _copy_check_file(RESOURCE_PATH,
                                       APPLICATION_SUPPORT_PATH,
                                       'font12.png')

    global NAMING_SCHEMAS
    NAMING_SCHEMAS  = _ConfigParser(NAMING_SCHEMA_FILENAME, 'naming schemas')
    global ANALYZER_CONFIG
    ANALYZER_CONFIG = _ConfigParser(ANALYZER_CONFIG_FILENAME, 'analyzer config')
    global PATH_MAPPER
    PATH_MAPPER = PathMapper(PATH_MAPPING_FILENAME)

    # define global functions which are in fact methods
    global map_path_to_os
    map_path_to_os = PATH_MAPPER.map_path_to_os
    global is_path_mappable
    is_path_mappable = PATH_MAPPER.is_path_mappable


def _copy_check_file(path_in, path_out, filename):
    fn_in = os.path.abspath(os.path.join(path_in, filename))
    fn_out = os.path.abspath(os.path.join(path_out, filename))
    if not os.path.isfile(fn_out):
        shutil.copy2(fn_in, fn_out)
    return fn_out

#-------------------------------------------------------------------------------
# classes:
#
class _ConfigParser(RawConfigParser):

    def __init__(self, filename, name):
        RawConfigParser.__init__(self)
        self.filename = filename
        self.name = name
        if not os.path.isfile(filename):
            raise IOError("File for %s with name '%s' not found." %
                          (name, filename))
        self.read(filename)

class PathMapper(object):

    def __init__(self, filename):
        self._column_names, self._path_mappings = None, None
        self.read(filename)

    def map_path_to_os(self, path, target_os=None, force=True):
        path2 = _map_path_to_os(path, self._path_mappings, target_os=target_os)
        if path2 is None and force:
            path2 = path
        return path2

    def is_path_mappable(self, path, target_os=None):
        path2 = _map_path_to_os(path, self._path_mappings, target_os=target_os)
        return not path2 is None

    def read(self, filename):
        self._column_names, self._path_mappings = read_table(filename)

    def write(self, filename):
        write_table(filename, self._path_mappings,
                    column_names=self._column_names)

    @property
    def column_names(self):
        return self._column_names[:]
