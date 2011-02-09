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

__all__ = ['SectionObjectdetection']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.config import _Section
from cecog.gui.guitraits import (IntTrait,
                                 FloatTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 SelectionTrait2,
                                 MultiSelectionTrait,
                                 )
from cecog.analyzer import (ZSLICE_PROJECTION_METHODS,
                            REGION_NAMES_PRIMARY,
                            )
from cecog.util.util import unlist

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_OBJECTDETECTION = 'ObjectDetection'


#-------------------------------------------------------------------------------
# functions:
#

#-------------------------------------------------------------------------------
# classes:
#
class SectionObjectdetection(_Section):

    SECTION_NAME = SECTION_NAME_OBJECTDETECTION

    OPTIONS = [
      ('primary_image',
       [('primary_channelid',
            SelectionTrait2(None, [], label='Primary channel ID')),
        ('primary_normalizemin',
            IntTrait(0, -2**16, 2**16, label='Min.')),
        ('primary_normalizemax',
            IntTrait(255, -2**16, 2**16, label='Max.')),
        ('primary_zslice_selection',
            BooleanTrait(True, label='Z-slice selection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('primary_zslice_selection_slice',
            IntTrait(1, 0, 1000, label='Slice')),
        ('primary_zslice_projection',
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('primary_zslice_projection_method',
            SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                           ZSLICE_PROJECTION_METHODS, label='Method')),
        ('primary_zslice_projection_begin',
            IntTrait(1, 0, 1000, label='Begin')),
        ('primary_zslice_projection_end',
            IntTrait(1, 0, 1000, label='End')),
        ('primary_zslice_projection_step',
            IntTrait(1, 1, 1000, label='Step')),
       ]),

      ('primary_segmentation',
       [('primary_medianradius',
            IntTrait(2, 0, 1000, label='Median radius')),
        ('primary_latwindowsize',
            IntTrait(20, 1, 1000, label='Window size')),
        ('primary_latlimit',
            IntTrait(1, 0, 255, label='Min. contrast')),
        ('primary_lat2',
            BooleanTrait(False, label='Local adaptive threshold 2')),
        ('primary_latwindowsize2',
            IntTrait(20, 1, 1000, label='Window size')),
        ('primary_latlimit2',
            IntTrait(1, 0, 255, label='Min. contrast')),
        ('primary_shapewatershed',
            BooleanTrait(False, label='Split & merge by shape')),
        ('primary_shapewatershed_gausssize',
            IntTrait(1, 0, 10000, label='Gauss radius')),
        ('primary_shapewatershed_maximasize',
            IntTrait(1, 0, 10000, label='Min. seed distance')),
        ('primary_shapewatershed_minmergesize',
            IntTrait(1, 0, 10000, label='Object size threshold')),
        ('primary_intensitywatershed',
            BooleanTrait(False, label='Split & merge by intensity')),
        ('primary_intensitywatershed_gausssize',
            IntTrait(1, 0, 10000, label='Gauss radius')),
        ('primary_intensitywatershed_maximasize',
            IntTrait(1, 0, 10000, label='Min. seed distance')),
        ('primary_intensitywatershed_minmergesize',
            IntTrait(1, 0, 10000, label='Object size threshold')),
        ('primary_postprocessing',
            BooleanTrait(False, label='Object filter')),
        ('primary_postprocessing_roisize_min',
            IntTrait(-1, -1, 10000, label='Min. object size')),
        ('primary_postprocessing_roisize_max',
            IntTrait(-1, -1, 10000, label='Max. object size')),
        ('primary_postprocessing_intensity_min',
            IntTrait(-1, -1, 10000, label='Min. average intensity')),
        ('primary_postprocessing_intensity_max',
            IntTrait(-1, -1, 10000, label='Max. average intensity')),
        ('primary_removeborderobjects',
            BooleanTrait(True, label='Remove border objects')),
        ('primary_regions',
            MultiSelectionTrait([REGION_NAMES_PRIMARY[0]],
                                 REGION_NAMES_PRIMARY)),
        ('primary_holefilling',
            BooleanTrait(True, label='Fill holes')),
       ]),

      ] +\
      unlist(
      [[('%s_image' % prefix,
       [('%s_channelid' % prefix,
            SelectionTrait2(None, [], label='%s channel ID' % name)),
        ('%s_normalizemin' % prefix,
            IntTrait(0, -2**16, 2**16, label='Min.')),
        ('%s_normalizemax' % prefix,
            IntTrait(255, -2**16, 2**16, label='Max.')),

        ('%s_zslice_selection' % prefix,
            BooleanTrait(True, label='Z-slice selection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('%s_zslice_selection_slice' % prefix,
            IntTrait(1, 0, 1000, label='Slice')),
        ('%s_zslice_projection' % prefix,
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('%s_zslice_projection_method' % prefix,
            SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                           ZSLICE_PROJECTION_METHODS, label='Method')),
        ('%s_zslice_projection_begin' % prefix,
            IntTrait(1, 0, 1000, label='Begin')),
        ('%s_zslice_projection_end' % prefix,
            IntTrait(1, 0, 1000, label='End')),
        ('%s_zslice_projection_step' % prefix,
            IntTrait(1, 1, 1000, label='Step')),
       ]),

      ('%s_registration' % prefix,
       [('%s_channelregistration_x' % prefix,
            IntTrait(0, -99999, 99999, label='Shift X')),
        ('%s_channelRegistration_y' % prefix,
            IntTrait(0, -99999, 99999, label='Shift Y')),
       ]),

      ('%s_segmentation' % prefix,
       [('%s_presegmentation' % prefix,
            BooleanTrait(False, label='Pre-Segmentation')),
        ('%s_presegmentation_medianradius' % prefix,
            IntTrait(1, 0, 1000, label='Median radius')),
        ('%s_presegmentation_alpha' % prefix,
            FloatTrait(1.0, 0, 4000, label='Otsu factor', digits=2)),


        ('%s_regions_expanded' % prefix,
            BooleanTrait(False, label='Expanded')),
        ('%s_regions_expanded_expansionsize' % prefix,
            IntTrait(0, 0, 4000, label='Expansion size')),

        ('%s_regions_inside' % prefix,
            BooleanTrait(True, label='Inside')),
        ('%s_regions_inside_shrinkingsize' % prefix,
            IntTrait(0, 0, 4000, label='Shrinking size')),

        ('%s_regions_outside' % prefix,
            BooleanTrait(False, label='Outside')),
        ('%s_regions_outside_expansionsize' % prefix,
            IntTrait(0, 0, 4000, label='Expansion size')),
        ('%s_regions_outside_separationsize' % prefix,
            IntTrait(0, 0, 4000, label='Separation size')),

        ('%s_regions_rim' % prefix,
            BooleanTrait(False, label='Rim')),
        ('%s_regions_rim_expansionsize' % prefix,
            IntTrait(0, 0, 4000, label='Expansion size')),
        ('%s_regions_rim_shrinkingsize' % prefix,
            IntTrait(0, 0, 4000, label='Shrinking size')),

        ('%s_regions_propagate' % prefix,
            BooleanTrait(False, label='Propagate')),
        ('%s_regions_propagate_lambda' % prefix,
            FloatTrait(0.05, 0, 4000, label='Lambda', digits=2)),
        ('%s_regions_propagate_deltawidth' % prefix,
            IntTrait(1, 0, 4000, label='Delta width')),
       ])]
      for name, prefix in [('Secondary', 'secondary'),
                           ('Tertiary', 'tertiary')
                           ]]
      )
