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

__all__ = ['SectionOutput']

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
from cecog.gui.guitraits import (BooleanTrait,
                                 IntTrait,
                                 )

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_OUTPUT = 'Output'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionOutput(_Section):

    SECTION_NAME = SECTION_NAME_OUTPUT

    OPTIONS = [
     ('output',
       [('rendering_labels_discwrite',
            BooleanTrait(False, label='Label images')),
        ('rendering_contours_discwrite',
            BooleanTrait(False, label='Contour images')),
        ('rendering_contours_showids',
            BooleanTrait(False, label='Show object IDs')),
        ('rendering_class_discwrite',
            BooleanTrait(False, label='Classification images')),
        ('rendering_class_showids',
            BooleanTrait(False, label='Show object IDs')),
        ('export_object_counts',
            BooleanTrait(False, label='Export object counts')),
        ('export_object_details',
            BooleanTrait(False, label='Export detailed object data')),
        ('export_track_data',
            BooleanTrait(False, label='Export track data')),
        ('events_export_all_features',
            BooleanTrait(False, label='Export all features per event')),
        ('events_export_gallery_images',
            BooleanTrait(False, label='Export gallery images')),
        ('events_gallery_image_size',
            IntTrait(50, 1, 1000, label='Gallery image size (pixel)')),
        ]),
     ('ImageContainer',
       [('imagecontainer_create_file',
            BooleanTrait(True, label='Create ImageContainer')),
        ('imagecontainer_reuse_file',
            BooleanTrait(True, label='Reuse ImageContainer')),
        ]),
     ('netcdf4',
       [('netcdf_create_file',
            BooleanTrait(False, label='Create NetCDF4')),
        ('netcdf_reuse_file',
            BooleanTrait(False, label='Reuse NetCDF4 (experimental!)')),
        ]),
      ]