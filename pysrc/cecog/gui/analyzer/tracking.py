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

from cecog import CHANNEL_PREFIX, CH_VIRTUAL, CH_PRIMARY, CH_OTHER
from cecog.traits.analyzer.tracking import SECTION_NAME_TRACKING
from cecog.gui.analyzer import BaseProcessorFrame, AnalyzerThread

from cecog.analyzer.channel import PrimaryChannel, SecondaryChannel
from cecog.analyzer.channel import TertiaryChannel, MergedChannel

from cecog.plugin.segmentation import REGION_INFO

class TrackingFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_TRACKING
    PROCESS_TRACKING = 'PROCESS_TRACKING'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        super(TrackingFrame, self).__init__(settings, parent)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalyzerThread,
                                     ('Test tracking', 'Stop tracking'))
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalyzerThread,
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
        ter_id = TertiaryChannel.NAME

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
        ter_region = settings.get2('tertiary_classification_regionname')

        settings.set('Output', 'hdf5_create_file', False)
        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        if name == self.PROCESS_TRACKING:
            # tracking only invokes the primary channel
            settings.set_section('Processing')
            settings.set2('primary_classification', False)
            settings.set2('primary_featureextraction', True)

            settings.set2('secondary_processChannel', False)
            settings.set2('secondary_featureextraction', False)
            settings.set2('secondary_classification', False)

            settings.set2('tertiary_processChannel', False)
            settings.set2('tertiary_featureextraction', False)
            settings.set2('tertiary_classification', False)

            settings.set2('merged_processChannel', False)
            settings.set2('merged_classification', False)

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
            self._channel_render_settings(settings, SecondaryChannel.NAME, show_ids_class)
            self._channel_render_settings(settings, TertiaryChannel.NAME, show_ids_class)
            self._channel_render_settings(settings, MergedChannel.NAME, show_ids_class)

        return settings

    def _channel_render_settings(self, settings, ch_name, show_class_ids):
        pfx = ch_name.lower()
        chreg = settings.get('Classification', '%s_classification_regionname' %pfx)
        if ((settings.get2('%s_featureextraction' %pfx) or pfx in CH_VIRTUAL) and
            settings.get2('%s_classification' %pfx) and
            settings.get2('%s_processchannel' %pfx)):
            settings.get('General', 'rendering_class').update( \
                self._class_rendering_params(ch_name.lower(), settings))

    def _class_rendering_params(self, prefix, settings):
        """Setup rendering prameters for images to show classified objects"""
        showids = settings.get('Output', 'rendering_class_showids')

        if prefix in CH_VIRTUAL:
            region = [settings.get("Classification", \
                                       "merged_%s_region" %pfx) \
                          for pfx in (CH_PRIMARY+CH_OTHER)]
            region = tuple(region)
            region_str = '-'.join(region)
        else:
            region = settings.get('Classification',
                                  '%s_classification_regionname' %prefix)
            region_str = region

        rpar = {prefix.title():
                    {'raw': ('#FFFFFF', 1.0),
                     'contours': [(region, 'class_label', 1, False),
                                  (region, '#000000', 1, showids)]}}
        cl_rendering = {'%s_classification_%s' %(prefix, region_str): rpar}
        return cl_rendering


    def page_changed(self):
        self.settings_loaded()

    def settings_loaded(self):
        # FIXME: set the trait list data to plugin instances of the current channel
        prefix = 'primary'
        trait = self._settings.get_trait(SECTION_NAME_TRACKING, 'tracking_regionname')
        trait.set_list_data(REGION_INFO.names[prefix])
