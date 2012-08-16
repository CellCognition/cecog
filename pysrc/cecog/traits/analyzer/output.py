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
                                 SelectionTrait2,
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
        ('export_file_names',
            BooleanTrait(False, label='Export raw image file names')),
        ('export_tracking_as_dot',
            BooleanTrait(False, label='Export tracking as GraphViz .dot')),
        ('export_track_data',
            BooleanTrait(False, label='Export tracks for head nodes')),
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
     ('hdf5',
       [('hdf5_create_file',
            BooleanTrait(False, label='Create HDF5')),
        ('hdf5_reuse',
            BooleanTrait(False, label='Reuse HDF5')),
        ('hdf5_include_raw_images',
            BooleanTrait(False, label='Include raw images')),
        ('hdf5_include_label_images',
            BooleanTrait(False, label='Include segmentation images')),
        ('hdf5_include_crack',
            BooleanTrait(False, label='Include crack contours')),
        ('hdf5_include_features',
            BooleanTrait(False, label='Include features')),
        ('hdf5_include_classification',
            BooleanTrait(False, label='Include classification')),
        ('hdf5_include_tracking',
            BooleanTrait(False, label='Include tracking')),
        ('hdf5_include_events',
            BooleanTrait(False, label='Include events')),
        ('hdf5_compression',
            BooleanTrait(True, label='Enable gzip compression (recommended!)')),
        ('hdf5_merge_positions',
            BooleanTrait(True, label='Merge positions into one file')),
        ]),
      ]