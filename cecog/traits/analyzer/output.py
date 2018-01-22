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
        ('hdf5',
         [('hdf5_create_file', BooleanTrait(True, label='Create Hdf file')),
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
      ]),
     ]
