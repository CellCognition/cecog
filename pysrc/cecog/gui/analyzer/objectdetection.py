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

__all__ = ['ObjectDetectionFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.analyzer import (_BaseFrame,
                                _ProcessorMixin,
                                AnalzyerThread
                                )
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.analyzer import (SECONDARY_COLORS,
                            SECONDARY_REGIONS,
                            )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class ObjectDetectionFrame(_BaseFrame, _ProcessorMixin):

    SECTION_NAME = SECTION_NAME_OBJECTDETECTION
    DISPLAY_NAME = 'Object Detection'
    TABS = ['PrimaryChannel', 'SecondaryChannel']

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

        self.register_control_button('detect',
                                     AnalzyerThread,
                                     ('Detect %s objects', 'Stop %s detection'))

        self.set_tab_name('PrimaryChannel')

        self.add_input('primary_channelid')
        self.add_group(None,
                       [('primary_normalizemin',),
                        ('primary_normalizemax',),
                        ], layout='flow', link='primary_channel_conversion',
                        label='16 to 8 bit conversion')
        self.add_line()
        self.add_group('primary_zslice_selection',
                       [('primary_zslice_selection_slice',)], layout='flow')
        self.add_group('primary_zslice_projection',
                       [('primary_zslice_projection_method',),
                        ('primary_zslice_projection_begin',),
                        ('primary_zslice_projection_end',),
                        ('primary_zslice_projection_step',),
                        ], layout='flow')
        self.add_line()
        self.add_input('primary_medianradius')
        self.add_group(None,
                       [('primary_latwindowsize', (1,0,1,1)),
                        ('primary_latlimit', (1,1,1,1)),
                        ], link='primary_lat', label='Local adaptive threshold')
        self.add_group('primary_lat2',
                       [('primary_latwindowsize2', (0,0,1,1)),
                        ('primary_latlimit2', (0,1,1,1)),
                        ])
        self.add_input('primary_holefilling')
        self.add_group('primary_shapewatershed',
                       [('primary_shapewatershed_gausssize', (0,0,1,1)),
                        ('primary_shapewatershed_maximasize', (0,1,1,1)),
                        ('primary_shapewatershed_minmergesize', (1,0,1,1)),
                        ])
        self.add_group('primary_postprocessing',
                        [('primary_postprocessing_roisize_min', (0,0,1,1)),
                          ('primary_postprocessing_roisize_max', (0,1,1,1)),
                          ('primary_postprocessing_intensity_min', (1,0,1,1)),
                          ('primary_postprocessing_intensity_max', (1,1,1,1)),
                        ])

        self.add_expanding_spacer()
        self.set_tab_name('SecondaryChannel')

        self.add_input('secondary_channelid')
        self.add_group(None,
                       [('secondary_normalizemin',),
                        ('secondary_normalizemax',),
                        ], layout='flow', link='secondary_channel_conversion',
                        label='16 to 8 bit conversion')
        self.add_group(None,
                       [('secondary_channelregistration_x',),
                        ('secondary_channelregistration_y',),
                        ], layout='flow', link='secondary_channel_registration',
                        label='Channel registration')
        self.add_line()
        self.add_group('secondary_zslice_selection',
                       [('secondary_zslice_selection_slice',)], layout='flow')
        self.add_group('secondary_zslice_projection',
                       [('secondary_zslice_projection_method',),
                        ('secondary_zslice_projection_begin',),
                        ('secondary_zslice_projection_end',),
                        ('secondary_zslice_projection_step',),
                        ], layout='flow')
        self.add_line()
        self.add_pixmap(QPixmap(':cecog_secondary_regions'), Qt.AlignRight)
        self.add_group(None,
                       [('secondary_regions_expanded', (0,0,1,1)),
                        ('secondary_regions_expanded_expansionsize', (0,1,1,1)),
                        (None, (1,0,1,9)),

                        ('secondary_regions_inside', (2,0,1,1)),
                        ('secondary_regions_inside_shrinkingsize', (2,1,1,1)),
                        (None, (3,0,1,9)),

                        ('secondary_regions_outside', (4,0,1,1)),
                        ('secondary_regions_outside_expansionsize', (4,1,1,1)),
                        ('secondary_regions_outside_separationsize', (4,2,1,1)),
                        (None, (5,0,1,9)),

                        ('secondary_regions_rim', (6,0,1,1)),
                        ('secondary_regions_rim_expansionsize', (6,1,1,1)),
                        ('secondary_regions_rim_shrinkingsize', (6,2,1,1)),

                        ], link='secondary_region_definition',
                        label='Region definition')

        self.add_expanding_spacer()
        self._init_control()

    def _get_modified_settings(self, name):
        settings = _ProcessorMixin._get_modified_settings(self, name)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        sec_regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                       if settings.get2(k)]

        settings.set_section('Processing')
        settings.set2('secondary_processChannel', False)
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('tracking', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set2('primary_simplefeatures_texture', False)
        settings.set2('primary_simplefeatures_shape', False)
        settings.set2('secondary_simplefeatures_texture', False)
        settings.set2('secondary_simplefeatures_shape', False)
        settings.set_section('General')
        settings.set2('rendering_class', {})
        #settings.set2('rendering_discwrite', True)
        #settings.set2('rendering_class_discwrite', True)

        show_ids = settings.get('Output', 'rendering_contours_showids')
        #settings.set('Output', 'export_object_details', False)
        #settings.set('Output', 'export_object_counts', False)


        if self._tab.currentIndex() == 0:
            settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, show_ids)}}}})
        else:
            settings.set('Processing', 'secondary_processChannel', True)
            settings.get('General', 'rendering').update(dict([('secondary_contours_%s' % x, {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                      'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                             }})
                                                              for x in sec_regions]))
        return settings

