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

__all__ = ['TrackingFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                )
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
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
class TrackingFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_TRACKING
    PROCESS_TRACKING = 'PROCESS_TRACKING'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        super(TrackingFrame, self).__init__(settings, parent)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalzyerThread,
                                     ('Test tracking', 'Stop tracking'))
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalzyerThread,
                                     ('Apply event selection',
                                      'Stop event selection'))

        self.add_input('tracking_regionname')
        self.add_group(None,
                       [('tracking_maxobjectdistance', (0,0,1,1)),
                        ('tracking_maxtrackinggap', (0,1,1,1)),
                        ('tracking_maxsplitobjects', (1,0,1,1)),
                        ], link='tracking', label='Tracking')
        self.add_line()
        self.add_group(None,
                       [('tracking_labeltransitions', (0,0,1,4)),
                        ('tracking_backwardrange', (1,0,1,1)),
                        ('tracking_forwardrange', (1,1,1,1)),
                        ('tracking_backwardlabels', (2,0,1,1)),
                        ('tracking_forwardlabels', (2,1,1,1)),
                        ('tracking_backwardcheck', (3,0,1,1)),
                        ('tracking_forwardcheck', (3,1,1,1)),
                        ('tracking_duration_unit', (4,0,1,6)),
                        ], link='tracking_eventselection',
                        label='Event selection')
        self.add_line()
        self.add_group('tracking_visualization',
                       [('tracking_visualize_track_length',),
                        ('tracking_centroid_radius',),
                       ], layout='flow')
        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings(self, name, has_timelapse)

        settings.set_section('ObjectDetection')
        prim_id = PrimaryChannel.NAME
        sec_id = SecondaryChannel.NAME
        settings.set_section('Processing')
        settings.set2('tracking', True)
        settings.set2('tracking_synchronize_trajectories', False)
        settings.set_section('Tracking')
        region_name = settings.get2('tracking_regionname')
        settings.set_section('General')
        settings.set2('rendering_class', {})
        settings.set2('rendering', {})
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        sec_region = settings.get2('secondary_classification_regionname')

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        if name == self.PROCESS_TRACKING:
            settings.set_section('Processing')
            settings.set2('primary_featureextraction', False)
            settings.set2('secondary_featureextraction', False)
            settings.set2('primary_classification', False)
            settings.set2('secondary_classification', False)
            settings.set2('secondary_processChannel', False)
            settings.set('Output', 'events_export_gallery_images', False)
            settings.set('General', 'rendering', {'primary_contours':
                                                  {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                             'contours': {region_name: ('#FF0000', 1, show_ids)}}}})
        else:
            settings.set_section('Processing')
            settings.set2('primary_featureextraction', True)
            settings.set2('primary_classification', True)
            settings.set2('tracking_synchronize_trajectories', True)
            settings.set('General', 'rendering_class', {'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                             'contours': [('primary', 'class_label', 1, False),
                                                                                                          ('primary', '#000000', 1, show_ids_class)]}},
                                                        })

            settings.set_section('Processing')
            if (settings.get2('secondary_featureextraction') and
                settings.get2('secondary_classification') and
                settings.get2('secondary_processchannel')):
                settings.get('General', 'rendering_class').update({'secondary_classification_%s' % sec_region: {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                              'contours': [(sec_region, 'class_label', 1, False),
                                                                                                                           (sec_region, '#000000', 1, show_ids_class)]}
                                                                                                              }
                                                                   })
        return settings

    def page_changed(self):
        self.settings_loaded()

    def settings_loaded(self):
        # FIXME: set the trait list data to plugin instances of the current channel
        prefix = 'primary'
        trait = self._settings.get_trait(SECTION_NAME_TRACKING, 'tracking_regionname')
        trait.set_list_data(REGION_INFO.names[prefix])
