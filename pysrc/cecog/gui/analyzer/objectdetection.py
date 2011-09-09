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
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                )
from cecog.traits.analyzer.objectdetection import SECTION_NAME_OBJECTDETECTION
from cecog.plugin.segmentation import (PRIMARY_SEGMENTATION_MANAGER,
                                       SECONDARY_SEGMENTATION_MANAGER,
                                       TERTIARY_SEGMENTATION_MANAGER,
                                       )
from cecog.plugin.segmentation import REGION_INFO

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class ObjectDetectionFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_OBJECTDETECTION
    DISPLAY_NAME = 'Object Detection'
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']

    def __init__(self, settings, parent):
        super(ObjectDetectionFrame, self).__init__(settings, parent)

        self.register_control_button('detect',
                                     AnalzyerThread,
                                     ('Detect %s objects', 'Stop %s detection'))

        self.set_tab_name('Primary Channel')

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
                        ('primary_zslice_projection_step', None, None, True),
                        ], layout='flow')
        self.add_line()
        self.add_plugin_bay(PRIMARY_SEGMENTATION_MANAGER, settings)

        self.add_expanding_spacer()

        for tab_name, prefix in [('Secondary Channel', 'secondary'),
                                 ('Tertiary Channel',  'tertiary')
                                 ]:
            self.set_tab_name(tab_name)

            self.add_input('%s_channelid' % prefix)
            self.add_group(None,
                           [('%s_normalizemin' % prefix,),
                            ('%s_normalizemax' % prefix,),
                            ], layout='flow', link='%s_channel_conversion' % prefix,
                            label='16 to 8 bit conversion')
            self.add_group(None,
                           [('%s_channelregistration_x' % prefix,),
                            ('%s_channelregistration_y' % prefix,),
                            ], layout='flow', link='%s_channel_registration' % prefix,
                            label='Channel registration')
            self.add_line()
            self.add_group('%s_zslice_selection' % prefix,
                           [('%s_zslice_selection_slice' % prefix,)], layout='flow')
            self.add_group('%s_zslice_projection' % prefix,
                           [('%s_zslice_projection_method' % prefix,),
                            ('%s_zslice_projection_begin' % prefix,),
                            ('%s_zslice_projection_end' % prefix,),
                            ('%s_zslice_projection_step' % prefix, None, None, True),
                            ], layout='flow')

            self.add_line()
            if prefix == 'secondary':
                self.add_plugin_bay(SECONDARY_SEGMENTATION_MANAGER, settings)
            else:
                self.add_plugin_bay(TERTIARY_SEGMENTATION_MANAGER, settings)


#            self.add_line()
#            self.add_pixmap(QPixmap(':cecog_secondary_regions'), Qt.AlignRight)
#            self.add_group(None,
#                           [('%s_regions_expanded' % prefix, (0,0,1,1)),
#                            ('%s_regions_expanded_expansionsize' % prefix, (0,1,1,1), None, True),
#                            (None, (1,0,1,8)),
#
#                            ('%s_regions_inside' % prefix, (2,0,1,1)),
#                            ('%s_regions_inside_shrinkingsize' % prefix, (2,1,1,1), None, True),
#                            (None, (3,0,1,8)),
#
#                            ('%s_regions_outside' % prefix, (4,0,1,1)),
#                            ('%s_regions_outside_expansionsize' % prefix, (4,1,1,1)),
#                            ('%s_regions_outside_separationsize' % prefix, (4,2,1,1), None, True),
#                            (None, (5,0,1,8)),
#
#                            ('%s_regions_rim' % prefix, (6,0,1,1)),
#                            ('%s_regions_rim_expansionsize' % prefix, (6,1,1,1)),
#                            ('%s_regions_rim_shrinkingsize' % prefix, (6,2,1,1), None, True),
#                            (None, (7,0,1,8)),
#
#                            ], link='%s_region_definition' % prefix,
#                            label='Region definition')
#
#            self.add_line()
#            self.add_group('%s_regions_constrained_watershed' % prefix,
#                           [('%s_regions_constrained_watershed_gauss_filter_size' % prefix, (0,0,1,1)),
#                            ])
#
#            self.add_line()
#            self.add_group('%s_regions_propagate' % prefix,
#                           [('%s_presegmentation_medianradius' % prefix, (0,0,1,1)),
#                            ('%s_presegmentation_alpha' % prefix, (0,1,1,1)),
#                            ('%s_regions_propagate_lambda' % prefix, (0,2,1,1)),
#                            ('%s_regions_propagate_deltawidth' % prefix, (0,3,1,1), None, True),
#                            ])

            self.add_expanding_spacer()

        self._init_control()


    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings(self, name, has_timelapse)

        settings.set_section('ObjectDetection')

        settings.set_section('Processing')
        for prefix in ['primary', 'secondary', 'tertiary']:
            settings.set2('%s_featureextraction' % prefix, False)
            settings.set2('%s_classification' % prefix, False)
        settings.set2('tracking', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)

        settings.set_section('General')
        settings.set2('rendering_class', {})
        #settings.set2('rendering_discwrite', True)
        #settings.set2('rendering_class_discwrite', True)

        settings.set('Output', 'events_export_gallery_images', False)
        show_ids = settings.get('Output', 'rendering_contours_showids')
        #settings.set('Output', 'export_object_details', False)
        #settings.set('Output', 'export_object_counts', False)


        current_tab = self._tab.currentIndex()
        if current_tab == 0:
            settings.set('Processing', 'secondary_processchannel', False)
            settings.set('Processing', 'tertiary_processchannel', False)
            prefix = 'primary'
        elif current_tab == 1:
            settings.set('Processing', 'secondary_processchannel', True)
            settings.set('Processing', 'tertiary_processchannel', False)
            prefix = 'secondary'
        else:
            settings.set('Processing', 'secondary_processChannel', True)
            settings.set('Processing', 'tertiary_processchannel', True)
            prefix = 'tertiary'

        colors = REGION_INFO.colors
        print 'REGION', prefix, REGION_INFO.names[prefix]
        settings.set('General', 'rendering', dict([('%s_contours_%s' % (prefix, x),
                                                    {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                                                            'contours': [(x, colors[x] , 1, show_ids)]
                                                    }})
                                                  for x in REGION_INFO.names[prefix]]))

        return settings

