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

__all__ = ['ObjectDetectionFrame']

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from cecog.gui.analyzer import BaseProcessorFrame
from cecog.threads.analyzer import AnalyzerThread

class ObjectDetectionFrame(BaseProcessorFrame):

    DISPLAY_NAME = 'Object Detection'
    TABS = ['Primary Channel', 'Secondary Channel', 'Tertiary Channel']
    ICON = ":segmentation.png"

    def __init__(self, settings, parent, name):
        super(ObjectDetectionFrame, self).__init__(settings, parent, name)

        self.register_control_button('detect', AnalyzerThread,
                                     ('Test Object Detection', 'Abort Object Detection'))

        self.set_tab_name('Primary Channel')

        self.add_input('primary_channelid')
        self.add_group(None,
                       [('primary_normalizemin',),
                        ('primary_normalizemax',),
                        ], layout='flow', link='primary_channel_conversion',
                        label='Gray-value normalization')
        self.add_line()
        self.add_group('primary_zslice_selection',
                       [('primary_zslice_selection_slice',)], layout='flow')
        self.add_group('primary_zslice_projection',
                       [('primary_zslice_projection_method',),
                        ('primary_zslice_projection_begin',),
                        ('primary_zslice_projection_end',),
                        ('primary_zslice_projection_step', None, None, True),
                        ], layout='flow')
        self.add_group('primary_flat_field_correction',
                       [('primary_flat_field_correction_image_dir',),
                        ], layout='flow')
        self.add_line()
        self.add_plugin_bay(self.plugin_mgr['primary'], settings)

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
                            label='Gray-value normalization')
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
            self.add_group('%s_flat_field_correction' % prefix,[('%s_flat_field_correction_image_dir' % prefix,)],layout='flow')

            self.add_line()
            self.add_plugin_bay(self.plugin_mgr[prefix], settings)
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

        settings.set('Output', 'events_export_gallery_images', False)
        settings.set('Output', 'hdf5_create_file', False)
        settings.set('Output', 'export_object_counts', False)
        settings.set('Output', 'export_file_names', False)
        settings.set('Output', 'export_object_details', False)
        settings.set('Output', 'export_tracking_as_dot', False)
        settings.set('Output', 'export_track_data', False)

        show_ids = settings.get('Output', 'rendering_contours_showids')


        current_tab = self._tab.current_index
        # turn of merged channel
        settings.set('General', 'process_merged', False)
        if current_tab == 0:
            settings.set('General', 'process_secondary', False)
            settings.set('General', 'process_tertiary', False)
            prefix = 'primary'
        elif current_tab == 1:
            settings.set('General', 'process_secondary', True)
            settings.set('General', 'process_tertiary', False)
            prefix = 'secondary'
        else:
            settings.set('General', 'process_secondary', True)
            settings.set('General', 'process_tertiary', True)
            prefix = 'tertiary'

        region_info = self.plugin_mgr.region_info
        colors = region_info.colors
        rdn = dict([('%s_contours_%s' % (prefix, x),
                     {prefix.capitalize(): {'raw': ('#FFFFFF', 1.0),
                                            'contours': [(x, colors[x] , 1, show_ids)]
                                            }
                      }
                     ) for x in region_info.names[prefix]])

        settings.set('General', 'rendering', rdn)

        return settings
