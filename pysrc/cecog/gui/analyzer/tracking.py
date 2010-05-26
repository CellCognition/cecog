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
from cecog.gui.analyzer import (_BaseFrame,
                                _ProcessorMixin,
                                COMPRESSION_FORMATS,
                                AnalzyerThread,
                                )
from cecog.traits.guitraits import (StringTrait,
                                    IntTrait,
                                    BooleanTrait,
                                    SelectionTrait,
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
class TrackingFrame(_BaseFrame, _ProcessorMixin):

    SECTION = 'Tracking'
    PROCESS_TRACKING = 'PROCESS_TRACKING'
    PROCESS_SYNCING = 'PROCESS_SYNCING'

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

        self.register_control_button(self.PROCESS_TRACKING,
                                     AnalzyerThread,
                                     ('Test tracking', 'Stop tracking'))
        self.register_control_button(self.PROCESS_SYNCING,
                                     AnalzyerThread,
                                     ('Apply event selection',
                                      'Stop event selection'))

        self.add_group('Tracking', None,
                       [('tracking_maxObjectDistance',
                         IntTrait(0, 0, 4000, label='Max object x-y distance'),
                         (0,0,1,1)),
                        ('tracking_maxTrackingGap',
                         IntTrait(0, 0, 4000, label='Max time-point gap'),
                         (0,1,1,1)),
                        ('tracking_maxSplitObjects',
                         IntTrait(0, 0, 4000, label='Max split events'),
                         (1,0,1,1)),
                        ], link='tracking')

        self.add_line()

        self.add_group('Event selection', None,
                       [('tracking_labelTransitions',
                         StringTrait('', 200, label='Class transition motif(s)',
                                     mask='(\(\d+,\d+\),)*\(\d+,\d+\)'),
                         (0,0,1,4)),
                        ('tracking_backwardRange',
                         IntTrait(0, -1, 4000, label='Time-points [pre]'),
                         (1,0,1,1)),
                        ('tracking_forwardRange',
                         IntTrait(0, -1, 4000, label='Time-points [post]'),
                         (1,1,1,1)),
                        ('tracking_backwardLabels',
                         StringTrait('', 200, label='Class filter [pre]',
                                     mask='(\d+,)*\d+'),
                         (2,0,1,1)),
                        ('tracking_forwardLabels',
                         StringTrait('', 200, label='Class filter [post]',
                                     mask='(\d+,)*\d+'),
                         (2,1,1,1)),
                        ('tracking_backwardCheck',
                         IntTrait(2, 0, 4000, label='Filter time-points [pre]'),
                         (3,0,1,1)),
                        ('tracking_forwardCheck',
                         IntTrait(2, 0, 4000, label='Filter time-points [post]'),
                         (3,1,1,1)),
                        ], link='tracking_eventselection')

        self.register_trait('tracking_forwardRange_min',
                            BooleanTrait(False, label='Min.'))
        self.register_trait('tracking_backwardRange_min',
                            BooleanTrait(False, label='Min.'))


#        self.add_group('tracking_event_tracjectory',
#                       BooleanTrait(True, label='Events by trajectory',
#                                    widget_info=BooleanTrait.RADIOBUTTON),
#                       [('tracking_backwardCheck',
#                         IntTrait(0, 0, 4000, label='Backward check',
#                                  tooltip='abc...')),
#                        ('tracking_forwardCheck',
#                         IntTrait(0, 0, 4000, label='Forward check',
#                                  tooltip='abc...')),
#                        ], layout='flow')


        self.add_line()

#        self.add_group('tracking_exportTrackFeatures',
#                       BooleanTrait(False, label='Export tracks'),
#                       [('tracking_compressionTrackFeatures',
#                         SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
#                                        label='Compression'))
#                       ], layout='flow')


        self.add_group('tracking_visualization',
                       BooleanTrait(False, label='Visualization'),
                       [('tracking_visualize_track_length',
                         IntTrait(5, -1, 10000,
                                  label='Max. time-points')),
                        ('tracking_centroid_radius',
                         IntTrait(3, -1, 50, label='Centroid radius')),
                       ], layout='flow')

#        self.add_group('tracking_exportFlatFeatures',
#                       BooleanTrait(False, label='Export flat',
#                                    tooltip='abc...'),
#                       [('tracking_compressionFlatFeatures',
#                         SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
#                                        label='Compression',
#                                        tooltip='abc...'))
#                       ])

        self.add_expanding_spacer()

        self.register_trait('tracking_maxInDegree',
                       IntTrait(0, 0, 4000, label='Max in-degree'))
        self.register_trait('tracking_maxOutDegree',
                       IntTrait(0, 0, 4000, label='Max out-degree'))
        self.register_trait('tracking_exportTrackFeatures',
                            BooleanTrait(True, label='Export tracks'))
        self.register_trait('tracking_compressionTrackFeatures',
                             SelectionTrait(COMPRESSION_FORMATS[0], COMPRESSION_FORMATS,
                                            label='Compression'))

        self._init_control()

    def _get_modified_settings(self, name):
        settings = _ProcessorMixin._get_modified_settings(self, name)

        settings.set_section('ObjectDetection')
        prim_id = settings.get2('primary_channelid')
        sec_id = settings.get2('secondary_channelid')
        settings.set_section('Processing')
        settings.set2('tracking', True)
        settings.set2('tracking_synchronize_trajectories', False)
        settings.set_section('Tracking')
        settings.set_section('General')
        settings.set2('rendering_class', {})
        settings.set2('rendering', {})
        #settings.set2('rendering_discwrite', True)
        #settings.set2('rendering_class_discwrite', True)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        sec_region = settings.get2('secondary_classification_regionname')

        show_ids = settings.get('Output', 'rendering_contours_showids')
        show_ids_class = settings.get('Output', 'rendering_class_showids')

        if name == self.PROCESS_TRACKING:
            settings.set2('primary_simplefeatures_texture', False)
            settings.set2('primary_simplefeatures_shape', False)
            settings.set2('secondary_simplefeatures_texture', False)
            settings.set2('secondary_simplefeatures_shape', False)
            settings.set('Processing', 'primary_classification', False)
            settings.set('Processing', 'secondary_classification', False)
            settings.set('Processing', 'secondary_processChannel', False)
            settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                 'contours': {'primary': ('#FF0000', 1, show_ids)}}}})
        else:
            settings.set('Processing', 'tracking_synchronize_trajectories', True)
            settings.set('Processing', 'primary_classification', True)
            settings.set('General', 'rendering_class', {'primary_classification': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                                             'contours': [('primary', 'class_label', 1, False),
                                                                                                          ('primary', '#000000', 1, show_ids_class)]}},
                                                        'secondary_classification_%s' % sec_region: {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                              'contours': [(sec_region, 'class_label', 1, False),
                                                                                                                           (sec_region, '#000000', 1, show_ids_class)]}
                                                                                                              }
                                                        })

        return settings
