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
from cecog.plugin.segmentation import REGION_INFO

class TrackingFrame(BaseProcessorFrame):

    PROCESS_TRACKING = 'PROCESS_TRACKING'

    def __init__(self, settings, parent, name):
        super(TrackingFrame, self).__init__(settings, parent, name)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalyzerThread,
                                     ('Test tracking', 'Stop tracking'))

        self.add_input('tracking_regionname')
        self.add_group(None,
                       [('tracking_maxobjectdistance', (0,0,1,1)),
                        ('tracking_maxtrackinggap', (0,1,1,1)),
                        ('tracking_maxsplitobjects', (1,0,1,1)),
                        ], link='tracking', label='Tracking')
        self.add_line()
        self.add_group('tracking_visualization',
                       [('tracking_visualize_track_length',),
                        ('tracking_centroid_radius',),
                       ], layout='flow')
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
        settings.set('Processing', 'secondary_processChannel', False)
        settings.set('Processing', 'secondary_featureextraction', False)
        settings.set('Processing', 'secondary_classification', False)
        settings.set('Processing', 'tertiary_processChannel', False)
        settings.set('Processing', 'tertiary_featureextraction', False)
        settings.set('Processing', 'tertiary_classification', False)
        settings.set('Processing', 'merged_processChannel', False)
        settings.set('Processing', 'merged_classification', False)
        settings.set('Output', 'events_export_gallery_images', False)

        region_name = settings.get('Tracking', 'tracking_regionname')
        show_ids = settings.get('Output', 'rendering_contours_showids')
        pct = {'primary_contours':
                   {CH_PRIMARY[0].title(): {'raw': ('#FFFFFF', 1.0),
                                         'contours': {region_name: ('#FF0000', 1, show_ids)}}}}

        settings.set('General', 'rendering', pct)
        return settings

    # def _channel_render_settings(self, settings, ch_name, show_class_ids):
    #     pfx = ch_name.lower()
    #     if ((settings.get2('%s_featureextraction' %pfx) or pfx in CH_VIRTUAL) and
    #         settings.get2('%s_classification' %pfx) and
    #         settings.get2('%s_processchannel' %pfx)):
    #         settings.get('General', 'rendering_class').update( \
    #             self._class_rendering_params(ch_name.lower(), settings))

    # def _class_rendering_params(self, prefix, settings):
    #     """Setup rendering prameters for images to show classified objects"""
    #     showids = settings.get('Output', 'rendering_class_showids')

    #     if prefix in CH_VIRTUAL:
    #         region = list()
    #         for pfx in (CH_PRIMARY+CH_OTHER):
    #             if settings.get('Classification', 'merge_%s' %pfx):
    #                 region.append(settings.get("Classification", "merged_%s_region" %pfx))
    #         region = tuple(region)
    #         region_str = '-'.join(region)
    #     else:
    #         region = settings.get('Classification',
    #                               '%s_classification_regionname' %prefix)
    #         region_str = region

    #     rpar = {prefix.title():
    #                 {'raw': ('#FFFFFF', 1.0),
    #                  'contours': [(region, 'class_label', 1, False),
    #                               (region, '#000000', 1, showids)]}}
    #     cl_rendering = {'%s_classification_%s' %(prefix, region_str): rpar}
    #    return cl_rendering


    def page_changed(self):
        self.settings_loaded()

    def settings_loaded(self):
        # FIXME: set the trait list data to plugin instances of the current channel
        trait = self._settings.get_trait('Tracking', 'tracking_regionname')
        trait.set_list_data(REGION_INFO.names['primary'])
