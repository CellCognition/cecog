"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Qing Zhong'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['EventSelectionFrame']

from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.gui.analyzer import BaseProcessorFrame, AnalzyerThread
from cecog.analyzer.channel import PrimaryChannel


class EventSelectionFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION
    DISPLAY_NAME = 'Event Selection'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        super(EventSelectionFrame, self).__init__(settings, parent)

        # IMPORTANT LINE HERE: DESIGN NEW EVENT SELECTION PROCESSING
        # THREAD BY TEARING APPART THE OLD TRACKING
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalzyerThread,
                                     ('Start', 'Stop'))

        self.add_line()
        self.add_group(None,
                       [('tracking_backwardrange', (0,0,1,1)),
                        ('tracking_forwardrange', (0,1,1,1)),
                        ('tracking_duration_unit', (0,2,1,1)),
                        ], link='tracking_eventselection', label='Event selection')
        self.add_group('supervised_event_selection',
                       [('tracking_labeltransitions', (0,0,1,1)),
                         ('tracking_backwardlabels', (1,0,1,1)),
                        ('tracking_forwardlabels', (1,1,1,1)),
                        ('tracking_backwardcheck', (3,0,1,1)),
                        ('tracking_forwardcheck', (3,1,1,1)),
                       ], layout='grid')
        self.add_group('unsupervised_event_selection',
                       [('min_event_duration',),
                       ], layout='flow')
        self.add_line()
        self.add_group('tc3_analysis', [
                ('num_clusters', (0,0,1,1)),
                ('min_cluster_size', (0,1,1,1)),
                ('tc3_algorithms', (0,2,1,1)),
                ],
                layout='grid', link='tc3_analysis')
        self.add_expanding_spacer()

        self._init_control(has_images=False)


    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings( \
            self, name, has_timelapse)

        settings.set('Processing', 'tracking', True)
        settings.set('Processing', 'tracking_synchronize_trajectories', False)
        settings.set('General', 'rendering_class', {})
        settings.set('General', 'rendering', {})

        settings.set('Classification', 'collectsamples', False)

#       settings.set('Output', 'hdf5_create_file', False)
        settings.set('Output', 'events_export_gallery_images', False)

        # only primary channel for event selection
        settings.set('Processing', 'secondary_featureextraction', False)
        settings.set('Processing', 'secondary_classification', False)
        settings.set('Processing', 'secondary_processChannel', False)
        settings.set('Processing', 'tertiary_featureextraction', False)
        settings.set('Processing', 'tertiary_classification', False)
        settings.set('Processing', 'tertiary_processChannel', False)

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        # setting up primary channel and live rendering
        if settings.get('EventSelection', 'unsupervised_event_selection'):
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'primary_classification', False)
            rdn =  {'primary_contours':
                    {PrimaryChannel.NAME: {'raw': ('#FFFFFF', 1.0),
                                           'contours': {'primary': ('#FF0000', 1, show_ids)}}}}
            settings.set('General', 'rendering', rdn)

        elif settings.get('EventSelection', 'supervised_event_selection'):
            settings.set('Processing', 'primary_featureextraction', True)
            settings.set('Processing', 'primary_classification', True)
            rdn = {'primary_classification':
                   {PrimaryChannel.NAME: {'raw': ('#FFFFFF', 1.0),
                                          'contours': [('primary', 'class_label', 1, False),
                                                       ('primary', '#000000', 1, show_ids_class)]}}}
            settings.set('General', 'rendering_class', rdn)
        return settings
