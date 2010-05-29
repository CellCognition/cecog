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
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import os
from ConfigParser import RawConfigParser

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#
NAMING_SCHEMA_FILENAME   = os.path.join('resources', 'naming_schemas.ini')
ANALYZER_CONFIG_FILENAME = os.path.join('resources', 'config.ini')

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
            print section_name
            self.add_section(section_name)

            section = section_registry.get_section(section_name)
            print section, dir(section)
            for trait_name in section.get_trait_names():
                print trait_name
                trait = section.get_trait(trait_name)
                self.set(section_name, trait_name, trait.default_value)

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
        RawConfigParser.read(self, filenames)

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


NAMING_SCHEMAS  = _ConfigParser(NAMING_SCHEMA_FILENAME, 'naming schemas')
ANALYZER_CONFIG = _ConfigParser(ANALYZER_CONFIG_FILENAME, 'analyzer config')

