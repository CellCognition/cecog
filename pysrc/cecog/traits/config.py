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

__all__ = []

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
from cecog.util.util import convert_package_path

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ConfigSettings(RawConfigParser):

    def __init__(self):
        RawConfigParser.__init__(self, {}, OrderedDict)
        self._registry = OrderedDict()
        self._current_section = None
        self.naming_schemes = RawConfigParser({}, OrderedDict)
        filename = os.path.join('resources', 'naming_schemes.conf')
        if not os.path.isfile(filename):
            raise IOError("Naming scheme file '%s' not found." % filename)
        self.naming_schemes.read(filename)

    def set_section(self, section):
        if self.has_section(section):
            self._current_section = section

    def register_section(self, section):
        self._registry[section] = OrderedDict()
        self.add_section(section)

    def register_trait(self, section, option, trait):
        option = option.lower()
        self._registry[section][option] = trait
        self.set(section, option, trait.value)

    def get_trait(self, section, option):
        return self._registry[section][option]

    def get_value(self, section, option):
        #trait = self._registry[section][option]
        return self.get(section, option)

    def get(self, section, option):
        option = option.lower()
        return RawConfigParser.get(self, section, option)

    def get2(self, option):
        return self.get(self._current_section, option)

    def set(self, section, option, value):
        option = option.lower()
        trait = self.get_trait(section, option)
        RawConfigParser.set(self, section, option, trait.convert(value))

    def set2(self, option, value):
        self.set(self._current_section, option, value)

    def read(self, filenames):
        RawConfigParser.read(self, filenames)
        for section, options in self._registry.iteritems():
            for option in options:
                value = self.get_value(section, option)
                self.set(section, option, value)

    def convert_package_path(self, section, option):
        path = convert_package_path(self.get(section, option))
        self.set(section, option, path)


#-------------------------------------------------------------------------------
# main:
#

