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
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['TrackingFrame']

from cecog import CH_VIRTUAL, CH_PRIMARY, CH_OTHER
from cecog.gui.analyzer import BaseProcessorFrame, AnalyzerThread


class TrackingFrame(BaseProcessorFrame):

    PROCESS_TRACKING = 'PROCESS_TRACKING'
    ICON = ":tracking.png"

    def __init__(self, settings, parent, name):
        super(TrackingFrame, self).__init__(settings, parent, name)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalyzerThread,
                                     ('Test tracking', 'Stop tracking'))

        self.add_input('region')
        self.add_line()
        
        self.add_group('tracking_visualization',
                       [('tracking_visualize_track_length',),
                        ('tracking_centroid_radius',),
                       ], layout='flow')
        
        self.add_line()
        self.add_plugin_bay(self.plugin_mgr['tracking'], settings)
        
        self.add_expanding_spacer()

        self._init_control()

    def _get_modified_settings(self, name, has_timelapse=True):
        settings = BaseProcessorFrame._get_modified_settings(self, name, has_timelapse)

        settings.set('Processing', 'tracking', True)
        settings.set('Processing', 'eventselection', False)
        settings.set('General', 'rendering_class', {})
        settings.set('General', 'rendering', {})
        settings.set('Classification', 'collectsamples', False)
        settings.set('Output', 'hdf5_create_file', False)

        # tracking only invokes the primary channel
        settings.set('Processing', 'primary_classification', False)
        settings.set('Processing', 'primary_featureextraction', True)
        settings.set('General', 'process_secondary', False)
        settings.set('Processing', 'secondary_featureextraction', False)
        settings.set('Processing', 'secondary_classification', False)
        settings.set('General', 'process_tertiary', False)
        settings.set('Processing', 'tertiary_featureextraction', False)
        settings.set('Processing', 'tertiary_classification', False)
        settings.set('General', 'process_merged', False)
        settings.set('Processing', 'merged_classification', False)
        settings.set('Output', 'events_export_gallery_images', False)

        region_name = settings.get('Tracking', 'region')
        show_ids = settings.get('Output', 'rendering_contours_showids')
        pct = {'primary_contours':
                   {CH_PRIMARY[0].title(): {'raw': ('#FFFFFF', 1.0),
                                         'contours': {region_name: ('#FF0000', 1, show_ids)}}}}

        settings.set('General', 'rendering', pct)
        return settings

    def page_changed(self):
        self.settings_loaded()

    def settings_loaded(self):
        # FIXME: set the trait list data to plugin instances of the current channel
        trait = self._settings.get_trait('Tracking', 'region')
        trait.set_list_data(self.plugin_mgr.region_info.names['primary'])
