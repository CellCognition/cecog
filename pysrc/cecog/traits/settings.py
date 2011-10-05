"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2011 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date: $'
__revision__ = '$Rev:  $'
__source__ = '$URL: $'

__all__ = ['ConfigSettings',
           '_Section'
           'SectionRegistry'
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import copy, \
       cStringIO
from ConfigParser import RawConfigParser

#-------------------------------------------------------------------------------
# extension module imports:
#
from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.traits import StringTrait
from cecog import PLUGIN_MANAGERS

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

    def register_trait(self, section_name, group_name, trait_name, trait):
        section = self._section_registry.get_section(section_name)
        section.register_trait(group_name, trait_name, trait)

    def unregister_trait(self, section_name, group_name, trait_name):
        section = self._section_registry.get_section(section_name)
        section.unregister_trait(group_name, trait_name)
        self.remove_option(section_name, trait_name)

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
        for plugin_manager in PLUGIN_MANAGERS:
            plugin_manager.clear()

        for section in self.sections():
            self.remove_section(section)

        result = RawConfigParser.readfp(self, fp)

        for section_name in self.sections():
            if section_name in self._section_registry.get_section_names():
                section = self._section_registry.get_section(section_name)
                for option_name in self.options(section_name):
                    if option_name in section.get_trait_names():
                        # convert values according to traits
                        value = self.get_value(section_name, option_name)
                        self.set(section_name, option_name, value)
                    elif option_name.find('plugin') == 0:
                        pass
#                    else:
#                        print("Warning: option '%s' in section '%s' is not "
#                              "defined and will be deleted" %\
#                              (option_name, section_name))
#                        self.remove_option(section_name, option_name)
            else:
                print("Warning: section '%s' is not defined and will be "
                      "deleted" % section_name)
                self.remove_section(section_name)

        for plugin_manager in PLUGIN_MANAGERS:
            plugin_manager.init_from_settings(self)

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

    def unregister_trait(self, name):
        del self._registry[name]

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

        for group_name, grp_items in self.OPTIONS:
            grp = TraitGroup(group_name)
            self._registry[group_name] = grp
            for trait_name, trait in grp_items:
                trait_name = trait_name.lower()
                self.register_trait(group_name, trait_name, trait)

    def get_group(self, name):
        return self._registry[name]

    def register_trait(self, group_name, trait_name, trait):
        if not group_name in self._registry:
            self._registry[group_name] = TraitGroup(group_name)
        grp = self._registry[group_name]
        self._traitname_grpname[trait_name] = group_name
        grp.register_trait(trait_name, trait)

    def unregister_trait(self, group_name, trait_name):
        grp = self._registry[group_name]
        del self._traitname_grpname[trait_name]
        grp.unregister_trait(trait_name)

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


#-------------------------------------------------------------------------------
# main:
#

