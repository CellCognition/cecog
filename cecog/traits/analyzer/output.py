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

from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import BooleanTrait, IntTrait

SECTION_NAME_OUTPUT = 'Output'

class SectionOutput(SectionCore):

    SECTION_NAME = SECTION_NAME_OUTPUT

    OPTIONS = [
     ('output',
       [('text_output',
         BooleanTrait(False, label='Text Output',
                      widget_info=BooleanTrait.RADIOBUTTON)),
        ('rendering_labels_discwrite',
         BooleanTrait(False, label='Label images')),
        ('rendering_contours_discwrite',
         BooleanTrait(False, label='Contour images')),
        ('rendering_contours_showids',
         BooleanTrait(False, label='Show object IDs')),
        ('rendering_class_discwrite',
         BooleanTrait(False, label='Classification images')),
        ('rendering_class_showids',
         BooleanTrait(False, label='Show object IDs')),
        ('rendering_channel_gallery',
         BooleanTrait(False, label='Merged channel gallery')),
        ('export_object_counts',
         BooleanTrait(False, label='Export object counts')),
        ('export_object_counts_ylim_max',
         IntTrait(-1, -1, 1000 , label='Max. count in plot')),
        ('export_object_details',
         BooleanTrait(False, label='Export detailed object data')),
        ('export_file_names',
         BooleanTrait(False, label='Export raw image file names')),
        ('export_tracking_as_dot',
         BooleanTrait(False, label='Export tracking as GraphViz .dot')),
        ('export_track_data',
         BooleanTrait(False, label='Export tracks for head nodes')),
        ('export_events',
         BooleanTrait(False, label='Export event data')),
        ('events_export_all_features',
         BooleanTrait(False, label='Export all features per event')),
        ('events_export_gallery_images',
         BooleanTrait(False, label='Export gallery images')),
        ('events_gallery_image_size',
         IntTrait(50, 1, 1000, label='Gallery image size (pixel)')),
        ]),
     ('hdf5',
      [('hdf5_create_file',
        BooleanTrait(True, label='Create CellH5',
                     widget_info=BooleanTrait.RADIOBUTTON)),
       ('hdf5_reuse',
        BooleanTrait(False, label='Reuse CellH5')),
       ('minimal_effort',
        BooleanTrait(False, label='Only necessary steps')),
       ('hdf5_include_raw_images',
        BooleanTrait(False, label='Include 8-bit image data')),
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
