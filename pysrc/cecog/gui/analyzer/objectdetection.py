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
                            TERTIARY_REGIONS,
                            )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
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
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

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
        self.add_group(None,
                       [('primary_medianradius', (0,0,1,1)),
                        ('primary_latwindowsize', (0,1,1,1)),
                        ('primary_latlimit', (0,2,1,1)),
                        ], link='primary_lat', label='Local adaptive threshold')
        self.add_group('primary_lat2',
                       [('primary_latwindowsize2', (0,0,1,1)),
                        ('primary_latlimit2', (0,1,1,1)),
                        ])
        self.add_input('primary_holefilling')
        self.add_input('primary_removeborderobjects')
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
            self.add_pixmap(QPixmap(':cecog_secondary_regions'), Qt.AlignRight)
            self.add_group(None,
                           [('%s_regions_expanded' % prefix, (0,0,1,1)),
                            ('%s_regions_expanded_expansionsize' % prefix, (0,1,1,1), None, True),
                            (None, (1,0,1,8)),

                            ('%s_regions_inside' % prefix, (2,0,1,1)),
                            ('%s_regions_inside_shrinkingsize' % prefix, (2,1,1,1), None, True),
                            (None, (3,0,1,8)),

                            ('%s_regions_outside' % prefix, (4,0,1,1)),
                            ('%s_regions_outside_expansionsize' % prefix, (4,1,1,1)),
                            ('%s_regions_outside_separationsize' % prefix, (4,2,1,1), None, True),
                            (None, (5,0,1,8)),

                            ('%s_regions_rim' % prefix, (6,0,1,1)),
                            ('%s_regions_rim_expansionsize' % prefix, (6,1,1,1)),
                            ('%s_regions_rim_shrinkingsize' % prefix, (6,2,1,1), None, True),
                            (None, (7,0,1,8)),

                            ], link='%s_region_definition' % prefix,
                            label='Region definition')

            self.add_group('%s_regions_propagate' % prefix,
                           [('%s_presegmentation_medianradius' % prefix, (0,0,1,1)),
                            ('%s_presegmentation_alpha' % prefix, (0,1,1,1)),
                            ('%s_regions_propagate_lambda' % prefix, (0,2,1,1)),
                            ('%s_regions_propagate_deltawidth' % prefix, (0,3,1,1), None, True),
                            ])

            self.add_expanding_spacer()

        self._init_control()


    def _get_modified_settings(self, name):
        settings = _ProcessorMixin._get_modified_settings(self, name)

        settings.set_section('ObjectDetection')
        prim_id = PrimaryChannel.NAME
        sec_id = SecondaryChannel.NAME
        sec_regions = [v for k,v in SECONDARY_REGIONS.iteritems()
                       if settings.get2(k)]
        tert_id = TertiaryChannel.NAME
        tert_regions = [v for k,v in TERTIARY_REGIONS.iteritems()
                       if settings.get2(k)]

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
        print current_tab
        if current_tab == 0:
            settings.set('Processing', 'secondary_processchannel', False)
            settings.set('Processing', 'tertiary_processchannel', False)
            settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, show_ids)}}}})
        elif current_tab == 1:
            settings.set('Processing', 'secondary_processchannel', True)
            settings.set('Processing', 'tertiary_processchannel', False)
            settings.set('General', 'rendering', dict([('secondary_contours_%s' % x, {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                      'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                             }})
                                                              for x in sec_regions]))
        else:
            settings.set('Processing', 'secondary_processChannel', True)
            settings.set('Processing', 'tertiary_processchannel', True)
            settings.set('General', 'rendering', dict([('tertiary_contours_%s' % x, {tert_id: {'raw': ('#FFFFFF', 1.0),
                                                                                               'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                             }})
                                                              for x in tert_regions]))
        return settings

