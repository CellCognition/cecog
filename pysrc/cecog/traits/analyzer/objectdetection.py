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
from cecog.traits.guitraits import (StringTrait,
                                    IntTrait,
                                    BooleanTrait,
                                    SelectionTrait,
                                    MultiSelectionTrait,
                                    )
from cecog.analyzer import (ZSLICE_PROJECTION_METHODS,
                            REGION_NAMES_PRIMARY,
                            )


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
        ('primary_channelid',
            StringTrait('rfp', 100, label='Primary channel ID')),
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
        ('primary_medianradius',
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
            BooleanTrait(True)),
        ('primary_regions',
            MultiSelectionTrait([REGION_NAMES_PRIMARY[0]],
                                 REGION_NAMES_PRIMARY)),
        ('primary_emptyimagemax',
            IntTrait(90, -1, 10000)),

        ('secondary_channelid',
            StringTrait('rfp', 100, label='Secondary channel ID')),
        ('secondary_normalizemin',
            IntTrait(0, -2**16, 2**16, label='Min.')),
        ('secondary_normalizemax',
            IntTrait(255, -2**16, 2**16, label='Max.')),

        ('secondary_channelregistration_x',
            IntTrait(0, -99999, 99999, label='Shift X')),
        ('secondary_channelRegistration_y',
            IntTrait(0, -99999, 99999, label='Shift Y')),

        ('secondary_zslice_selection',
            BooleanTrait(True, label='Z-slice selection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('secondary_zslice_selection_slice',
            IntTrait(1, 0, 1000, label='Slice')),
        ('secondary_zslice_projection',
            BooleanTrait(False, label='Z-slice projection',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('secondary_zslice_projection_method',
            SelectionTrait(ZSLICE_PROJECTION_METHODS[0],
                           ZSLICE_PROJECTION_METHODS, label='Method')),
        ('secondary_zslice_projection_begin',
            IntTrait(1, 0, 1000, label='Begin')),
        ('secondary_zslice_projection_end',
            IntTrait(1, 0, 1000, label='End')),
        ('secondary_zslice_projection_step',
            IntTrait(1, 1, 1000, label='Step')),

        ('secondary_regions_expanded',
            BooleanTrait(False, label='Expanded')),
        ('secondary_regions_expanded_expansionsize',
            IntTrait(0, 0, 4000, label='Expansion size')),

        ('secondary_regions_inside',
            BooleanTrait(True, label='Inside')),
        ('secondary_regions_inside_shrinkingsize',
            IntTrait(0, 0, 4000, label='Shrinking size')),
        ('secondary_regions_outside',
            BooleanTrait(False, label='Outside')),
        ('secondary_regions_outside_expansionsize',
            IntTrait(0, 0, 4000, label='Expansion size')),
        ('secondary_regions_outside_separationsize',
            IntTrait(0, 0, 4000, label='Separation size')),
        ('secondary_regions_rim',
            BooleanTrait(False, label='Rim')),
        ('secondary_regions_rim_expansionsize',
            IntTrait(0, 0, 4000, label='Expansion size')),
        ('secondary_regions_rim_shrinkingsize',
            IntTrait(0, 0, 4000, label='Shrinking size')),
        ]
