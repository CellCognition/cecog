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
from os.path import join, isdir, isfile, dirname, normpath, abspath, \
    realpath, expanduser, basename

from ConfigParser import RawConfigParser

import cecog
from cecog.util.pattern import Singleton
from cecog.util.mapping import map_path_to_os as _map_path_to_os
from cecog import ccore

def find_resource_dir():
    """Return a normalized absolute path to the resource directory.

    Function defines the search order for different locations i.e.
    installations, bundeled binaries and the the source tree.
    """
    rdirs = [join(dirname(sys.executable), 'resources'),
             join(dirname(abspath(sys.argv[0])).replace('bin', 'share'),
                  'cellcognition', 'resources'),
	     join(sys.exec_prefix, 'share', 'cellcognition', 'resources'),
             'resources',
             join(dirname(__file__), os.pardir, 'resources')]

    for rdir in rdirs:
        if isdir(rdir):
            break
    rdir = normpath(abspath(rdir))

    if not isdir(rdir):
        raise IOError("Resource path '%s' not found." %rdir)
    return rdir


class ConfigParser(RawConfigParser):
    """Custom config parser with sanity check."""

    def __init__(self, filename, name):
        RawConfigParser.__init__(self)
        self.filename = filename
        self.name = name
        if not os.path.isfile(filename):
            raise IOError("File for %s with name '%s' not found." %
                          (name, filename))
        self.read(filename)


class BatteryPackage(object):

    def __init__(self, resource_path, path = None, ):
        super(BatteryPackage, self).__init__()
        self._path = path
        self._demodata = resource_path

    @property
    def package_path(self):
        return self._path

    @property
    def demo_settings(self):
        return join(self.package_path, "Settings", "demo_settings.conf")
        
    
    def copy_demodata(self, dest_path):
        self._path = dest_path

        if not isdir(dest_path) and isdir(self._demodata):
            shutil.copytree(self._demodata, dest_path)

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

    # need to refer to the executable path, or working directory...
    RESOURCE_DIR = find_resource_dir()
    BATTERY_PACKAGE_DIR = join(RESOURCE_DIR, "battery_package")

    FONT12 = join(RESOURCE_DIR, "font12.png")
    NAMING_SCHEMA = join(RESOURCE_DIR, "naming_schemas.ini")
    PATH_MAPPINGS = join(RESOURCE_DIR, "path_mappings.txt")
    CONFIG = join(RESOURCE_DIR, "config.ini")

    PALETTES = join('palettes', 'zeiss')

    # XXX want this away from class level
    naming_schema = ConfigParser(NAMING_SCHEMA, 'naming_schemas')
    analyzer_config = ConfigParser(CONFIG, 'analyzer_config')
    path_mapper = PathMapper(PATH_MAPPINGS)

    def __init__(self, version=cecog.VERSION, redirect=False, debug=False):
        super(CecogEnvironment, self).__init__()
        self._user_config_dir = None
        self.version = version
        self._copy_config(self)

        if redirect:
            self._redirect()

        self.battery_package = BatteryPackage(self.BATTERY_PACKAGE_DIR)
        self.battery_package.copy_demodata(
            join(self.user_config_dir, basename(self.BATTERY_PACKAGE_DIR)))

        fontfile = join(self.user_config_dir, self.FONT12)
        ccore.Config.strFontFilepath = realpath(fontfile)
        if debug:
            print 'ccore.Config.strFontFilepath(%s) called' %self.FONT12

    @classmethod
    def map_path_to_os(cls, *args, **kw):
        return cls.path_mapper.map_path_to_os(*args, **kw)

    @classmethod
    def is_path_mapable(cls, *args, **kw):
        return cls.path_mapper.is_path_mappable(*args, **kw)

    @property
    def demo_settings(self):
        return normpath(self.battery_package.demo_settings)

    @classmethod
    def _copy_config(cls, self):
        """Copy configuration files to user_config_dir

        Note: No file will be overwritten.
        """

        if not isdir(self.user_config_dir):
            os.mkdir(self.user_config_dir)

        cfiles = ('FONT12', 'CONFIG', 'PATH_MAPPINGS', 'NAMING_SCHEMA')
        # copy the config config and update class attributes
        for key in cfiles:
            file_ = getattr(cls, key)
            src = join(cls.RESOURCE_DIR, basename(file_))
            target = join(self.user_config_dir, basename(file_))
            setattr(cls, key, target)

            if not isfile(target):
                shutil.copy2(src, target)

        target = join(self.user_config_dir, cls.PALETTES)
        src = join(cls.RESOURCE_DIR, cls.PALETTES)
        if not isdir(target):
            shutil.copytree(src, target)

        # changing resource directory after copying the files
        # copy also the r sources
        cls.RESOURCE_DIR = self.user_config_dir

    @property
    def palettes_dir(self):
        return join(self.user_config_dir, self.PALETTES)

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

    def _redirect(self):

        logpath = join(self.user_config_dir, 'log')
        if not isdir(logpath):
            os.mkdir(logpath)

        sys.stdout = file(join(logpath, 'stdout.log'), 'w')
        sys.stderr = file(join(logpath, 'stderr.log'), 'w')

        # may cause troubles on windows
        atexit.register(sys.stderr.close)
        atexit.register(sys.stdout.close)

    @property
    def package_dir(self):
        return self.battery_package.package_path

    def pprint(self):
        print 'resource-dir: ', self.RESOURCE_DIR
        print 'config.ini: ', self.CONFIG
        print 'font12-file: ', self.FONT12
        print 'path-mapping-file:', self.PATH_MAPPINGS
        print 'naming-scheme: ', self.NAMING_SCHEMA
        print 'battery_package: ', self.package_dir
