# -*- coding: utf-8 -*-
"""
environment.py - provides os independent path settings
                 e.g. path for ini-files

The basic frame work is supposed to work without calling the __init__ method
of the CecogEnvironment class. The __init__ method copies all the config files
including the battery_package to the users home directory. i.e. the gui should
call the __init__ the batch script not.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import os
import sys
import csv
import atexit
import shutil
from os.path import join, isdir, isfile, dirname, normpath, abspath, realpath, \
    expanduser, basename

from cecog.traits.config import _ConfigParser as ConfigParser
from cecog import VERSION
from cecog import ccore


# XXX - wrong module for design pattern
class Singleton(type):

    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(cls, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance

class BatteryPackage(object):

    def __init__(self, resource_path, path = None, ):
        super(BatteryPackage, self).__init__()
        self._path = path
        self._demodata = resource_path

    @property
    def package_path(self):
        return self._path

    def copy_demodata(self, dest_path):
        self._path = dest_path
        if not isdir(dest_path) and isdir(self._demodata):
            shutil.copytree(self._demodata, dest_path)
            os.mkdir(join(dest_path, 'Analysis'))

    @package_path.deleter
    def package_path(self):
        del self._path


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
        with open(filename, "r") as fp:
            pmp = csv.DictReader(fp, delimiter="\t")
            self._path_mappings = [row for row in pmp]
            self._column_names = pmp.fieldnames

    def write(self, filename):
        with open(filename, "w") as fp:
            pmp = csv.DictWriter(fp, fieldnames=self._column_names,
                                 delimiter="\t")
            for row in self._path_mappings:
                pmp.writerow(row)

class CecogEnvironment(object):

    __metaclass__ = Singleton

    VERSION = VERSION
    RESOURCE_DIR = 'resources'
    BATTERY_PACKAGE_DIR = join(RESOURCE_DIR, "battery_package")

    FONT12_FILENAME = "font12.png"
    NAMING_SCHEMA = join(RESOURCE_DIR, "naming_schemas.ini")
    PATH_MAPPINGS = "path_mappings.txt"
    CONFIG = join(RESOURCE_DIR, "config.ini")

    R_SOURCE_DIR = 'rsrc'

    _config_files = {'CONFIG': CONFIG,
                     'NAMING_SCHEMA': NAMING_SCHEMA,
                     'PATH_MAPPING': PATH_MAPPINGS,
                     'FONT12': FONT12_FILENAME}

    # XXX want this away from class level
    naming_schema = ConfigParser(NAMING_SCHEMA, 'naming_schemas')
    analyzer_config = ConfigParser(CONFIG, 'analyzer_config')

    def __init__(self, version, redirect=False, debug=False):
        super(CecogEnvironment, self).__init__()
        self._user_config_dir = None
        self.version = version
        self._check_resources()
        self._copy_config()

        if redirect:
            self._redirect()

        self.path_mapper = PathMapper(self._config_files['PATH_MAPPING'])

        self.battery_package = BatteryPackage(self.BATTERY_PACKAGE_DIR)
        self.battery_package.copy_demodata(
            join(self.user_config_dir, basename(self.BATTERY_PACKAGE_DIR)))

        fontfile = join(self.user_config_dir, self.FONT12_FILENAME)
        ccore.Config.strFontFilepath = realpath(fontfile)
        if debug:
            print 'ccorce.Config.strFontFilepath(FONT12_FILENAME) called'

    @classmethod
    def convert_package_path(cls, path):
        return normpath(join(cls.BATTERY_PACKAGE_DIR, path))

    def _redirect(self):

        import pdb; pdb.set_trace()

        logpath = join(self.user_config_dir, 'log')
        if not isdir(logpath):
            os.mkdir(logpath)

        sys.stdout = file(join(logpath, 'stdout.log'), 'w')
        sys.stderr = file(join(logpath, 'stderr.log'), 'w')

        # may cause troubles on windows
        atexit.register(sys.stderr.close)
        atexit.register(sys.stdout.close)

    @property
    def PATH_MAPPING_FILENAME(self):
        return self._config_files['PATH_MAPPING']

    @property
    def NAMING_SCHEMA_FILENAME(self):
        return self._config_files['NAMING_SCHEMA']

    @property
    def ANALYZER_CONFIG_FILENAME(self):
        return self._config_files['CONFIG']

    @property
    def PACKAGE_DIR(self):
        return self.battery_package.package_path

    def _copy_config(self):
        """Copy configuration files to user_config_dir

        Note: No file will be overwritten.
        """

        if not isdir(self.user_config_dir):
            os.mkdir(self.user_config_dir)

        for key, file_ in self._config_files.iteritems():
            src = join(self.RESOURCE_DIR, basename(file_))
            target = join(self.user_config_dir, basename(file_))
            self._config_files[key] = target
            if not isfile(target):
                shutil.copy2(src, target)

    def _check_resources(self):
        # ugly since resource will never be in the working directory
        # if it is found therer, it's by accident!
        self.RESOURCE_DIR = abspath(self.RESOURCE_DIR)
        if not isdir(self.RESOURCE_DIR):
            self.RESOURCE_DIR = join(dirname(__file__),
                                      os.pardir, os.pardir, 'apps',
                                     'CecogAnalyzer', 'resources')
            self.RESOURCE_DIR = normpath(self.RESOURCE_DIR)
            if not isdir(self.RESOURCE_DIR):
                raise IOError("Resource directory not found (%s)."
                              % self.RESOURCE_DIR)

        self.R_SOURCE_PATH = normpath(join(self.RESOURCE_DIR, 'rsrc'))
        if not isdir(self.R_SOURCE_PATH):
            self.R_SOURCE_PATH = join(dirname(__file__), os.pardir,
                                      os.pardir, 'rsrc')
            if not isdir(self.R_SOURCE_PATH):
                raise IOError("R-source directory not found (%s)."
                          % self.R_SOURCE_PATH)

    @property
    def user_config_dir(self):
        """Return the absolute path to cellcognition to the user
        config directory dependent on the user version.
        """
        if self._user_config_dir is None:
            cecog_dir = 'CellCognition%s' %self.version
            if sys.platform.startswith('win'):
                path = join(expanduser('~'), "Application Data", cecog_dir)
            elif sys.platform.startswith("darwin"):
                path = join(expanduser('~'), "Library", "Application Support",
                            cecog_dir)
            else:
                path = abspath(join(expanduser('~'), '.'+cecog_dir))
            self._user_config_dir = path
        return self._user_config_dir

    @staticmethod
    def map_path_to_os(*args, **kw):
        return self.path_mapper.map_path_to_os(*args, **kw)

    @staticmethod
    def is_path_mapable(*args, **kw):
        return self.path_mapper.is_path_mappable(*args, **kw)

    def pprint(self):
        print 'r-source-path: ', self.R_SOURCE_PATH
        print 'resource-dir: ', self.RESOURCE_DIR
        print 'config.ini: ', self.ANALYZER_CONFIG_FILENAME
        print 'font12-file: ', self.FONT12_FILENAME
        print 'path-mapping-file:', self.PATH_MAPPING_FILENAME
        print 'naming-scheme: ', self.NAMING_SCHEMA_FILENAME
        print 'battery_package: ', self.PACKAGE_DIR
