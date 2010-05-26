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
                                ZSLICE_PROJECTION_METHODS,
                                REGION_NAMES_PRIMARY,
                                SECONDARY_REGIONS,
                                SECONDARY_COLORS,
                                AnalzyerThread
                                )
from cecog.traits.guitraits import (StringTrait,
                                    IntTrait,
                                    BooleanTrait,
                                    SelectionTrait,
                                    MultiSelectionTrait,
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

    SECTION = 'ObjectDetection'
    NAME = 'Object Detection'
    TABS = ['PrimaryChannel', 'SecondaryChannel']

    def __init__(self, settings, parent):
        _BaseFrame.__init__(self, settings, parent)
        _ProcessorMixin.__init__(self)

        self.register_control_button('detect',
                                     AnalzyerThread,
                                     ('Detect %s objects', 'Stop %s detection'))

        self.set_tab_name('PrimaryChannel')

        self.add_input('primary_channelId',
                       StringTrait('rfp', 100, label='Primary channel ID'))
#        self.add_input('zSliceOrProjection',
#                       StringTrait('1', 10,
#                                   label='Z-slice or projection',
#                                   tooltip='abc...'))
        self.add_group('16 to 8 bit conversion', None,
                       [('primary_normalizeMin',
                        IntTrait(0, -2**16, 2**16, label='Min.')),
                        ('primary_normalizeMax',
                        IntTrait(255, -2**16, 2**16, label='Max.')),
                        ], layout='flow', link='primary_channel_conversion')
        self.add_line()

        self.add_group('primary_zslice_selection',
                       BooleanTrait(True, label='Z-slice selection',
                                    widget_info=BooleanTrait.RADIOBUTTON),
                       [('primary_zslice_selection_slice',
                        IntTrait(1, 0, 1000, label='Slice')),
                        ], layout='flow')
        self.add_group('primary_zslice_projection',
                       BooleanTrait(False, label='Z-slice projection',
                                    widget_info=BooleanTrait.RADIOBUTTON),
                       [('primary_zslice_projection_method',
                         SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                                        ZSLICE_PROJECTION_METHODS,
                                        label='Method')),
                        ('primary_zslice_projection_begin',
                         IntTrait(1, 0, 1000, label='Begin')),
                        ('primary_zslice_projection_end',
                         IntTrait(1, 0, 1000, label='End')),
                        ('primary_zslice_projection_step',
                         IntTrait(1, 1, 1000, label='Step')),
                        ], layout='flow')

        self.add_line()

        self.add_input('primary_medianRadius',
                       IntTrait(2, 0, 1000, label='Median radius'))

        self.add_group('Local adaptive threshold', None,
                       [('primary_latWindowSize',
                         IntTrait(20, 1, 1000, label='Window size'),
                         (1,0,1,1)),
                        ('primary_latLimit',
                         IntTrait(1, 0, 255, label='Min. contrast'),
                         (1,1,1,1)),
                        ], link='primary_lat')
        self.add_group('primary_lat2',
                       BooleanTrait(False, label='Local adaptive threshold 2'),
                       [('primary_latWindowSize2',
                         IntTrait(20, 1, 1000, label='Window size'),
                         (0,0,1,1)),
                        ('primary_latLimit2',
                         IntTrait(1, 0, 255, label='Min. contrast'),
                         (0,1,1,1)),
                        ])


        self.add_group('primary_shapeWatershed',
                       BooleanTrait(False, label='Split & merge by shape'),
                       [('primary_shapeWatershed_gaussSize',
                         IntTrait(1, 0, 10000, label='Gauss radius'),
                         (0,0,1,1)),
                        ('primary_shapeWatershed_maximaSize',
                         IntTrait(1, 0, 10000, label='Min. seed distance'),
                         (0,1,1,1)),
                        ('primary_shapeWatershed_minMergeSize',
                         IntTrait(1, 0, 10000, label='Object size threshold'),
                         (1,0,1,1)),
                        ])

#        self.add_group('intensityWatershed',
#                       BooleanTrait(False, label='Watershed by intensity',
#                                    tooltip='abc...'),
#                       [('intensityWatershed_gaussSize',
#                         IntTrait(1, 0, 10000, label='Gauss radius',
#                                  tooltip='abc...')),
#                        ('intensityWatershed_maximaSize',
#                         IntTrait(1, 0, 10000, label='Min. seed distance',
#                                  tooltip='abc...')),
#                        ('intensityWatershed_minMergeSize',
#                         IntTrait(1, 0, 10000, label='Object size threshold',
#                                  tooltip='abc...'))],
#                        layout='box')

        self.add_group('primary_postProcessing',
                       BooleanTrait(False, label='Object filter'),
                        [('primary_postProcessing_roisize_min',
                          IntTrait(-1, -1, 10000, label='Min. object size'),
                          (0,0,1,1)),
                          ('primary_postProcessing_roisize_max',
                          IntTrait(-1, -1, 10000, label='Max. object size'),
                          (0,1,1,1)),
                          ('primary_postProcessing_intensity_min',
                          IntTrait(-1, -1, 10000, label='Min. average intensity'),
                          (1,0,1,1)),
                          ('primary_postProcessing_intensity_max',
                          IntTrait(-1, -1, 10000, label='Max. average intensity'),
                          (1,1,1,1)),
                        ])

#                       [('primary_postProcessing_featureCategories',
#                         MultiSelectionTrait([], FEATURE_CATEGORIES,
#                                             label='Feature categories',
#                                             tooltip='abc...')),
#                        ('primary_postProcessing_conditions',
#                         StringTrait('', 200, label='Conditions',
#                                     tooltip='abc...')),
#                        ])


        self.register_trait('primary_regions',
                            MultiSelectionTrait([REGION_NAMES_PRIMARY[0]],
                                                 REGION_NAMES_PRIMARY))
        self.register_trait('primary_postProcessing_deleteObjects',
                             BooleanTrait(True, 'Delete rejected objects'))
        self.register_trait('primary_zSliceOrProjection',
                       StringTrait('1', 10,
                                   label='Z-slice or projection'))
        self.register_trait('primary_removeBorderObjects',
                            BooleanTrait(True, label='Remove border objects'))

        self.register_trait('primary_intensityWatershed',
                       BooleanTrait(False, label='Watershed by intensity'))
        self.register_trait('primary_intensityWatershed_gaussSize',
                         IntTrait(1, 0, 10000, label='Gauss radius'))
        self.register_trait('primary_intensityWatershed_maximaSize',
                         IntTrait(1, 0, 10000, label='Min. seed distance'))
        self.register_trait('primary_intensityWatershed_minMergeSize',
                         IntTrait(1, 0, 10000, label='Object size threshold'))
        self.register_trait('primary_emptyImageMax',
                         IntTrait(90, 0, 255, label='Empty frame threshold'))

        self.add_expanding_spacer()


        self.set_tab_name('SecondaryChannel')

        self.add_input('secondary_channelId',
                       StringTrait('rfp', 100, label='Secondary channel ID'))
#        self.add_input('zSliceOrProjection',
#                       StringTrait('1', 10,
#                                   label='Z-slice or projection',
#                                   tooltip='abc...'))
        self.add_group('16 to 8 bit conversion', None,
                       [('secondary_normalizeMin',
                        IntTrait(0, -2**16, 2**16, label='Min.')),
                        ('secondary_normalizeMax',
                        IntTrait(255, -2**16, 2**16, label='Max.')),
                        ], layout='flow', link='secondary_channel_conversion')

        self.add_group('Channel registration', None,
                       [('secondary_channelRegistration_x',
                         IntTrait(0, -99999, 99999,
                                  label='Shift X')),
                        ('secondary_channelRegistration_y',
                         IntTrait(0, -99999, 99999,
                                  label='Shift Y')),
                        ], layout='flow', link='secondary_channel_registration')

#        self.add_input('medianRadius',
#                       IntTrait(2, 0, 1000, label='Median radius',
#                                tooltip='abc...'))
        self.add_line()

        self.add_group('secondary_zslice_selection',
                       BooleanTrait(True, label='Z-slice selection',
                                    widget_info=BooleanTrait.RADIOBUTTON),
                       [('secondary_zslice_selection_slice',
                        IntTrait(1, 0, 1000, label='Slice')),
                        ], layout='flow')
        self.add_group('secondary_zslice_projection',
                       BooleanTrait(False, label='Z-slice projection',
                                    widget_info=BooleanTrait.RADIOBUTTON),
                       [('secondary_zslice_projection_method',
                         SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                                        ZSLICE_PROJECTION_METHODS,
                                        label='Method')),
                        ('secondary_zslice_projection_begin',
                         IntTrait(1, 0, 1000, label='Begin')),
                        ('secondary_zslice_projection_end',
                         IntTrait(1, 0, 1000, label='End')),
                        ('secondary_zslice_projection_step',
                         IntTrait(1, 1, 1000, label='Step')),
                        ], layout='flow')

        self.add_line()
        self.add_pixmap(QPixmap(':cecog_secondary_regions'), Qt.AlignRight)

        self.add_group('Region definition', None,
                       [('secondary_regions_expanded',
                         BooleanTrait(False, label='Expanded'),
                         (0,0,1,1)),
                        ('secondary_regions_expanded_expansionsize',
                         IntTrait(0, 0, 4000, label='Expansion size'),
                         (0,1,1,1)),
                        (None, None, (1,0,1,9)),

                        ('secondary_regions_inside',
                         BooleanTrait(True, label='Inside'),
                         (2,0,1,1)),
                        ('secondary_regions_inside_shrinkingsize',
                         IntTrait(0, 0, 4000, label='Shrinking size'),
                         (2,1,1,1)),
                        (None, None, (3,0,1,9)),

                        ('secondary_regions_outside',
                         BooleanTrait(False, label='Outside'),
                         (4,0,1,1)),
                        ('secondary_regions_outside_expansionsize',
                         IntTrait(0, 0, 4000, label='Expansion size'),
                         (4,1,1,1)),
                        ('secondary_regions_outside_separationsize',
                         IntTrait(0, 0, 4000, label='Separation size'),
                         (4,2,1,1)),
                        (None, None, (5,0,1,9)),

                        ('secondary_regions_rim',
                         BooleanTrait(False, label='Rim'),
                         (6,0,1,1)),
                        ('secondary_regions_rim_expansionsize',
                         IntTrait(0, 0, 4000, label='Expansion size'),
                         (6,1,1,1)),
                        ('secondary_regions_rim_shrinkingsize',
                         IntTrait(0, 0, 4000, label='Shrinking size'),
                         (6,2,1,1)),

                        ], link='secondary_region_definition')


        self.register_trait('secondary_zSliceOrProjection',
                       StringTrait('1', 10,
                                   label='Z-slice or projection'))

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

        if self._tab.currentIndex() == 0:
            settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0), 'contours': {'primary': ('#FF0000', 1, show_ids)}}}})
        else:
            settings.set('Processing', 'secondary_processChannel', True)
            settings.get('General', 'rendering').update(dict([('secondary_contours_%s' % x, {sec_id: {'raw': ('#FFFFFF', 1.0),
                                                                                                      'contours': [(x, SECONDARY_COLORS[x] , 1, show_ids)]
                                                                                             }})
                                                              for x in sec_regions]))
        return settings

