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
           'PATH_MAPPER'
           'map_path_to_os',
           'is_path_mappable',
           'ConfigSettings',
           '_Section'
           'SectionRegistry'
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       copy, \
       cStringIO, \
       shutil

from ConfigParser import RawConfigParser
#from collections import OrderedDict

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict
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
from cecog.traits.traits import StringTrait

#-------------------------------------------------------------------------------
# constants:
#
PACKAGE_PATH = ''
RESOURCE_PATH            = 'resources'
if not os.path.isdir(RESOURCE_PATH):
    RESOURCE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'apps',
                                 'CecogAnalyzer', 'resources')
    if not os.path.isdir(RESOURCE_PATH):
        raise IOError("Resource path '%s' not found." % RESOURCE_PATH)

R_SOURCE_PATH = os.path.join(RESOURCE_PATH, 'rsrc')
if not os.path.isdir(R_SOURCE_PATH):
    R_SOURCE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, 'rsrc')
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

def get_package_path():
    return PACKAGE_PATH

def set_package_path(dest_path):
    global PACKAGE_PATH
    demo_data_src_path = os.path.join(RESOURCE_PATH, 'battery_package')
    if not os.path.isdir(dest_path) and os.path.isdir(demo_data_src_path):
        shutil.copytree(demo_data_src_path, dest_path)
    PACKAGE_PATH = dest_path

def convert_package_path(path):
    return os.path.normpath(os.path.join(PACKAGE_PATH, path))

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


class ConfigSettings(RawConfigParser):
    """
    Extension of RawConfigParser which maps sections to parameter sections e.g.
    GUI modules and options to values in these modules.
    Values are stored internally in a representation as defined by value traits.
    Only sections and options as defined by the sections_registry (corresponding
    to modules and traits) are allowed.
    """

    def __init__(self, section_registry):
        RawConfigParser.__init__(self,
                                 dict_type=OrderedDict,
                                 allow_no_value=True)
        self._registry = OrderedDict()
        self._current_section = None

        self._section_registry = section_registry
        for section_name in section_registry.get_section_names():
            self.add_section(section_name)
            section = section_registry.get_section(section_name)
            for trait_name in section.get_trait_names():
                trait = section.get_trait(trait_name)
                self.set(section_name, trait_name, trait.default_value)

    def copy(self):
        return copy.deepcopy(self)

    def set_section(self, section_name):
        if self.has_section(section_name):
            self._current_section = section_name

    def get_section(self, section_name):
        return self._section_registry.get_section(section_name)

    def get_section_names(self):
        return self._section_registry.get_section_names()

    def get_trait(self, section_name, trait_name):
        section = self._section_registry.get_section(section_name)
        return section.get_trait(trait_name)

    def get_value(self, section_name, trait_name):
        return self.get(section_name, trait_name)

    def get(self, section_name, trait_name):
        trait_name = trait_name.lower()
        return RawConfigParser.get(self, section_name, trait_name)

    def get2(self, trait_name):
        return self.get(self._current_section, trait_name)

    def set(self, section_name, trait_name, value):
        trait_name = trait_name.lower()
        trait = self.get_trait(section_name, trait_name)
        RawConfigParser.set(self, section_name, trait_name,
                            trait.convert(value))

    def set2(self, trait_name, value):
        self.set(self._current_section, trait_name, value)

    def read(self, filename):
        fp = file(filename, 'r')
        self.readfp(fp)
        fp.close()

    def readfp(self, fp):
        result = RawConfigParser.readfp(self, fp)

        for section_name in self.sections():
            if section_name in self._section_registry.get_section_names():
                section = self._section_registry.get_section(section_name)
                for option_name in self.options(section_name):
                    if option_name in section.get_trait_names():
                        # convert values according to traits
                        value = self.get_value(section_name, option_name)
                        self.set(section_name, option_name, value)
                    else:
                        print("Warning: option '%s' in section '%s' is not "
                              "defined and will be deleted" %\
                              (option_name, section_name))
                        self.remove_option(section_name, option_name)
            else:
                print("Warning: section '%s' is not defined and will be "
                      "deleted" % section_name)
                self.remove_section(section_name)
        return result

    def to_string(self):
        stringio = cStringIO.StringIO()
        self.write(stringio)
        s = stringio.getvalue()
        stringio.close()
        return s

    def from_string(self, s):
        stringio = cStringIO.StringIO()
        stringio.writelines(s)
        stringio.seek(0)
        self.readfp(stringio)
        stringio.close()

    def compare(self, settings, section_name, grp_name):
        section = self.get_section(section_name)
        names = section.get_trait_names_for_group(grp_name)
        equal = True
        for name in names:
            if (self.get(section_name, name) !=
                settings.get(section_name, name)):
                equal = False
                break
        return equal


class SectionRegistry(object):

    def __init__(self):
        self._registry = OrderedDict()

    def register_section(self, section):
        self._registry[section.SECTION_NAME] = section

    def unregister_section(self, name):
        del self._registry[name]

    def get_section(self, name):
        return self._registry[name]

    def get_section_names(self):
        return self._registry.keys()

    def get_path_settings(self):
        result = []
        for section_name, section in self._registry.iteritems():
            for trait_name in section.get_trait_names():
                trait = section.get_trait(trait_name)
                if (isinstance(trait, StringTrait) and
                    trait.widget_info in [StringTrait.STRING_FILE,
                                          StringTrait.STRING_PATH]):
                    result.append((section_name, trait_name, trait))
        return result


class TraitGroup(object):

    def __init__(self, name):
        self.name = name
        self._registry = OrderedDict()

    def register_trait(self, name, trait):
        self._registry[name] = trait

    def get_trait(self, name):
        return self._registry[name]

    def get_trait_names(self):
        return self._registry.keys()


class _Section(object):

    SECTION_NAME = None
    OPTIONS = None

    def __init__(self):
        self._registry = OrderedDict()
        self._traitname_grpname = OrderedDict()

        for grp_name, grp_items in self.OPTIONS:
            grp = TraitGroup(grp_name)
            self._registry[grp_name] = grp
            for trait_name, trait in grp_items:
                trait_name = trait_name.lower()
                grp.register_trait(trait_name, trait)
                self._traitname_grpname[trait_name] = grp_name

    def get_group(self, name):
        return self._registry[name]

    def get_group_names(self):
        return self._registry.keys()

    def get_trait(self, trait_name):
        grp_name = self._traitname_grpname[trait_name]
        grp = self._registry[grp_name]
        return grp.get_trait(trait_name)

    def get_trait_names(self):
        names = []
        for grp in self._registry.values():
            names += grp.get_trait_names()
        return set(names)

    def get_trait_names_for_group(self, name):
        grp = self.get_group(name)
        return grp.get_trait_names()


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



