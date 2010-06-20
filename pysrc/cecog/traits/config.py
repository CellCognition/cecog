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
       copy

from ConfigParser import RawConfigParser

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.util.util import (read_table,
                             write_table,
                             )
from cecog.util.mapping import map_path_to_os as _map_path_to_os
from cecog.traits.traits import StringTrait

#-------------------------------------------------------------------------------
# constants:
#
ANALYZER_CONFIG_FILENAME = os.path.join('resources', 'config.ini')
FONT12_FILENAME = os.path.join('resources', 'font12.png')
NAMING_SCHEMA_FILENAME   = os.path.join('resources', 'naming_schemas.ini')
PATH_MAPPING_FILENAME = os.path.join('resources', 'path_mappings.txt')

#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class _ConfigParser(RawConfigParser):

    def __init__(self, filename, name):
        RawConfigParser.__init__(self, {}, OrderedDict)
        self.filename = filename
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
        RawConfigParser.__init__(self, {}, OrderedDict)
        self._registry = OrderedDict()
        self._current_section = None
        #self.naming_schemes = RawConfigParser({}, OrderedDict)
        #filename = os.path.join('resources', 'naming_schemes.conf')
        #if not os.path.isfile(filename):
        #    raise IOError("Naming scheme file '%s' not found." % filename)
        #self.naming_schemes.read(filename)

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

    def read(self, filenames):
        result = RawConfigParser.read(self, filenames)

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


class _Section(object):

    SECTION_NAME = None
    OPTIONS = None

    def __init__(self):
        self._registry = OrderedDict()
        for trait_name, trait in self.OPTIONS:
            trait_name = trait_name.lower()
            self._registry[trait_name] = trait

    def get_trait(self, name):
        return self._registry[name]

    def get_trait_names(self):
        return self._registry.keys()


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


NAMING_SCHEMAS  = _ConfigParser(NAMING_SCHEMA_FILENAME, 'naming schemas')
ANALYZER_CONFIG = _ConfigParser(ANALYZER_CONFIG_FILENAME, 'analyzer config')

PATH_MAPPER = PathMapper(PATH_MAPPING_FILENAME)

# define global functions which are in fact methods
map_path_to_os = PATH_MAPPER.map_path_to_os
is_path_mappable = PATH_MAPPER.is_path_mappable

