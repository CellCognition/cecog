"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

__all__ = ['ConfigSettings']


import copy
import cStringIO
from collections import OrderedDict
from ConfigParser import RawConfigParser

from cecog import VERSION
from cecog.plugin.metamanager import MetaPluginManager
from cecog.traits.analyzer.section_registry import SectionRegistry

class ConfigSettings(RawConfigParser):
    """Extension of RawConfigParser which maps sections to parameter sections e.g.
    GUI modules and options to values in these modules.
    Values are stored internally in a representation as defined by value traits.
    Only sections and options as defined by the sections_registry (corresponding
    to modules and traits) are allowed.
    """

    def __init__(self):
        RawConfigParser.__init__(self, allow_no_value=True)
        self._registry = OrderedDict()
        self._current_section = None
        self._old_file_format = False

        self._section_registry = SectionRegistry()
        for section_name in self._section_registry.section_names():
            self.add_section(section_name)
            section = self._section_registry.get_section(section_name)
            for trait_name in section.get_trait_names():
                trait = section.get_trait(trait_name)
                self.set(section_name, trait_name, trait.default_value)

    def __call__(self, section, parameter):
        return self.get(section, parameter)

    def was_old_file_format(self):
        return self._old_file_format

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
        return self._section_registry.section_names()

    def get_trait(self, section_name, trait_name):
        section = self._section_registry.get_section(section_name)
        return section.get_trait(trait_name)

    def get_value(self, section_name, trait_name):
        return self.get(section_name, trait_name)

    def get(self, section, option):
        if section not in self.sections():
            raise RuntimeError("Section %s does not exists" %section)
        return RawConfigParser.get(self, section, option)

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

    def _merge_registry(self):
        """
        Merge sections and options, that are in the section registry
        but not in the file.
        """
        section_names = self._section_registry.section_names()
        for sec_name in section_names:
            if not self.has_section(sec_name):
                self.add_section(sec_name)
            section = self._section_registry.get_section(sec_name)
            for opt_name in section.get_trait_names():
                if not self.has_option(sec_name, opt_name):
                    value = section.get_trait(opt_name).default_value
                    self.set(sec_name, opt_name, value)

    def readfp(self, fp):
        for plugin_manager in MetaPluginManager():
            plugin_manager.clear()
        for section in self.sections():
            self.remove_section(section)

        result = RawConfigParser.readfp(self, fp)
        self._old_file_format = False
        if not self.has_option('General', 'version') or \
                self.get('General', 'version') < VERSION:
            self._old_file_format = True

        for section_name in self.sections():
            if section_name in self._section_registry.section_names():
                section = self._section_registry.get_section(section_name)
                for option_name in self.options(section_name):
                    if option_name in section.get_trait_names():
                        # convert values according to traits
                        value = self.get_value(section_name, option_name)
                        self.set(section_name, option_name, value)

                    elif option_name.startswith('plugin'):
                        # plugins are okay, because they do not
                        # obey the old trait concept
                        pass
                    else:
                        self._update_option_to_version(section_name, option_name)
                        print("Warning: option '%s' in section '%s' is not "
                              "defined and will be deleted" %\
                                  (option_name, section_name))
                        self.remove_option(section_name, option_name)
            else:
                print("Warning: section '%s' is not defined and will be "
                      "deleted" % section_name)
                self.remove_section(section_name)

        self._merge_registry()
        for plugin_manager in MetaPluginManager():
            plugin_manager.init_from_settings(self)

        return result

    def to_dict(self):
        settings = dict()
        for section in self.sections():
            settings[section] = dict()
            for option in self.options(section):
                settings[section][option] = self.get(section, option)
        return settings

    def from_dict(self, settings):
        for section, group in settings.iteritems():
            for option, value in group.iteritems():
                RawConfigParser.set(self, section, option, value)

        # # update the plugins
        for plugin_manager in MetaPluginManager():
            plugin_manager.clear()
            plugin_manager.init_from_settings(self)

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

    def _update_option_to_version(self, section_name, option_name):
        VERSION_130_TO_140 = {}
        VERSION_130_TO_140['ObjectDetection'] = {
            'primary_holefilling' : 'plugin__primary_segmentation__primary__primary__holefilling',
            'primary_intensitywatershed' : 'plugin__primary_segmentation__primary__primary__intensitywatershed',
            'primary_intensitywatershed_gausssize' : 'plugin__primary_segmentation__primary__primary__intensitywatershed_gausssize',
            'primary_intensitywatershed_maximasize' : 'plugin__primary_segmentation__primary__primary__intensitywatershed_maximasize',
            'primary_intensitywatershed_minmergesize' : 'plugin__primary_segmentation__primary__primary__intensitywatershed_minmergesize',
            'primary_lat2' : 'plugin__primary_segmentation__primary__primary__lat2',
            'primary_latlimit' : 'plugin__primary_segmentation__primary__primary__latlimit',
            'primary_latlimit2' : 'plugin__primary_segmentation__primary__primary__latlimit2',
            'primary_latwindowsize' : 'plugin__primary_segmentation__primary__primary__latwindowsize',
            'primary_latwindowsize2' : 'plugin__primary_segmentation__primary__primary__latwindowsize2',
            'primary_medianradius' : 'plugin__primary_segmentation__primary__primary__medianradius',
            'primary_postprocessing' : 'plugin__primary_segmentation__primary__primary__postprocessing',
            'primary_postprocessing_intensity_max' : 'plugin__primary_segmentation__primary__primary__postprocessing_intensity_max',
            'primary_postprocessing_intensity_min' : 'plugin__primary_segmentation__primary__primary__postprocessing_intensity_min',
            'primary_postprocessing_roisize_max' : 'plugin__primary_segmentation__primary__primary__postprocessing_roisize_max',
            'primary_postprocessing_roisize_min' : 'plugin__primary_segmentation__primary__primary__postprocessing_roisize_min',
            'primary_removeborderobjects' : 'plugin__primary_segmentation__primary__primary__removeborderobjects',
            'primary_shapewatershed' : 'plugin__primary_segmentation__primary__primary__shapewatershed',
            'primary_shapewatershed_gausssize' : 'plugin__primary_segmentation__primary__primary__shapewatershed_gausssize',
            'primary_shapewatershed_maximasize' : 'plugin__primary_segmentation__primary__primary__shapewatershed_maximasize',
            'primary_shapewatershed_minmergesize' : 'plugin__primary_segmentation__primary__primary__shapewatershed_minmergesize',
        }

        if section_name in VERSION_130_TO_140:
            if option_name in VERSION_130_TO_140[section_name]:
                value = self.get(section_name, option_name)
                new_option_name = VERSION_130_TO_140[section_name][option_name]
                RawConfigParser.set(self, section_name, new_option_name, value)
                print 'Converted', option_name, 'into', new_option_name, '=', value

        if section_name == 'ObjectDetection':
            for prefix in ['secondary', 'tertiary']:
                if option_name == '%s_regions_expanded' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name
                            value = self.get(section_name, '%s_regions_expanded_expansionsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__expanded__expanded__expansion_size' % prefix , value)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__expanded__expanded__require00' % prefix , 'primary')

                elif option_name == '%s_regions_inside' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name
                            value = self.get(section_name, '%s_regions_inside_shrinkingsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__inside__inside__shrinking_size' % prefix , value)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__inside__inside__require00' % prefix , 'primary')

                elif option_name == '%s_regions_outside' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name, '%s_regions_outside_expansionsize' % prefix
                            value = self.get(section_name, '%s_regions_outside_expansionsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__outside__outside__expansion_size' % prefix , value)
                            value = self.get(section_name, '%s_regions_outside_separationsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__outside__outside__separation_size' % prefix , value)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__outside__outside__require00' % prefix , 'primary')

                elif option_name == '%s_regions_rim' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name
                            value = self.get(section_name, '%s_regions_rim_expansionsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__rim__rim__expansion_size' % prefix , value)
                            value = self.get(section_name, '%s_regions_rim_shrinkingsize' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__rim__rim__shrinking_size' % prefix , value)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__rim__rim__require00' % prefix , 'primary')

                elif option_name == '%s_regions_constrained_watershed' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name
                            value = self.get(section_name, '%s_regions_constrained_watershed_gauss_filter_size' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__constrained_watershed__constrained_watershed__gauss_filter_size' % prefix , value)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__constrained_watershed__constrained_watershed__require00' % prefix , 'primary')

                elif option_name == '%s_regions_propagate' % prefix:
                    if self.has_option(section_name, option_name):
                        if self.get(section_name, option_name):
                            print 'Converted', option_name
                            value = self.get(section_name, '%s_regions_propagate_deltawidth' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__propagate__propagate__delta_width' % prefix , value)

                            value = self.get(section_name, '%s_regions_propagate_lambda' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__propagate__propagate__lambda' % prefix , value)

                            value = self.get(section_name, '%s_presegmentation_medianradius' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__propagate__propagate__presegmentation_median_radius' % prefix , value)

                            value = self.get(section_name, '%s_presegmentation_alpha' % prefix)
                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__propagate__propagate__presegmentation_alpha' % prefix , value)

                            RawConfigParser.set(self, section_name, 'plugin__%s_segmentation__constrained_watershed__constrained_watershed__require00' % prefix , 'primary')
