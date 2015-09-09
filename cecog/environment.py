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
import atexit
import shutil
from os.path import join, isdir, isfile, dirname, normpath, abspath, \
    realpath, expanduser, basename

from ConfigParser import RawConfigParser

from cecog import version
from cecog.util.pattern import Singleton

from cecog import ccore

class LogFile(file):
    """Custom file class that flushes always after write method is called"""

    def write(self, *args, **kw):
        super(LogFile, self).write(*args, **kw)
        self.flush()


def find_resource_dir():
    """Return a normalized absolute path to the resource directory.

    Function defines the search order for different locations i.e.
    installations, bundeled binaries and the source tree.
    """

    rdirs = []
            
    rdirs.extend([join(dirname(sys.executable), 'resources'),
                  join(dirname(abspath(sys.argv[0])).replace('bin', 'share'),
                       'cellcognition', 'resources'),
                  join(sys.exec_prefix, 'share', 'cellcognition', 'resources'),
                  'resources',
                  join(dirname(__file__), os.pardir, 'resources')])

    environment_paths = filter(lambda x: os.path.basename(os.path.abspath(x)) == 'site-packages',
                               os.environ['PYTHONPATH'].split(':'))

    if len(environment_paths) > 0:
        env_path_candidates = [join(x, os.pardir, os.pardir, os.pardir, 'share', 'cellcognition', 'resources')
                               for x in environment_paths]
        rdirs.extend(filter(lambda x: isdir(normpath(abspath(x))), env_path_candidates))

    for rdir in rdirs:
        print '%s\t%s\t%s' % (rdir, normpath(abspath(rdir)), isdir(normpath(abspath(rdir))))
            
    for rdir in rdirs:
        if isdir(rdir):
            break
    rdir = normpath(abspath(rdir))

    if not isdir(rdir):
        raise IOError("Resource path '%s' not found." % rdir)
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

class CecogEnvironment(object):

    __metaclass__ = Singleton

    # need to refer to the executable path, or working directory...
    RESOURCE_DIR = find_resource_dir()
    BATTERY_PACKAGE_DIR = join(RESOURCE_DIR, "battery_package")
    ONTOLOGY_DIR = join(RESOURCE_DIR, "ontologies")
    UI_DIR = join(RESOURCE_DIR, "ui")
    DOC_DIR = "doc"

    FONT12 = join(RESOURCE_DIR, "font12.png")
    NAMING_SCHEMA = join(RESOURCE_DIR, "naming_schemas.ini")
    PALETTES = join('palettes', 'zeiss')

    # XXX want this away from class level
    naming_schema = ConfigParser(NAMING_SCHEMA, 'naming_schemas')

    def __init__(self, version=version.version, redirect=False, debug=False):
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

        cfiles = ('FONT12', 'NAMING_SCHEMA')
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

        target = join(self.user_config_dir, cls.DOC_DIR)
        src = join(cls.RESOURCE_DIR, cls.DOC_DIR)
        if not isdir(target):
            shutil.copytree(src, target)

        # changing resource directory after copying the files
        # copy also the r sources
        cls.RESOURCE_DIR = self.user_config_dir

    @property
    def doc_dir(self):
        return join(self.user_config_dir, self.DOC_DIR)

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

        sys.stdout = LogFile(join(logpath, 'stdout.log'), 'w')
        sys.stderr = LogFile(join(logpath, 'stderr.log'), 'w')

        # may cause troubles on windows
        atexit.register(sys.stderr.close)
        atexit.register(sys.stdout.close)

    @property
    def package_dir(self):
        return self.battery_package.package_path

    def pprint(self):
        print 'resource-dir: ', self.RESOURCE_DIR
        print 'font12-file: ', self.FONT12
        print 'naming-scheme: ', self.NAMING_SCHEMA
        print 'battery_package: ', self.package_dir
