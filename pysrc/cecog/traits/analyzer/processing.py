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

__all__ = ['SectionProcessing']


from cecog.traits.analyzer.section_core import SectionCore
from cecog.gui.guitraits import BooleanTrait


SECTION_NAME_PROCESSING = 'Processing'


class SectionProcessing(SectionCore):

    SECTION_NAME = SECTION_NAME_PROCESSING

    OPTIONS = \
        [('processing',
           [('objectdetection',
             BooleanTrait(True, label='Object detection')),
            ('primary_featureextraction',
             BooleanTrait(True, label='Feature Extraction')),
            ('primary_classification',
             BooleanTrait(False, label='Classification')),
            ('tracking',
             BooleanTrait(False, label='Tracking')),
            ('eventselection',
             BooleanTrait(False, label='Event selection')),
            ('primary_errorcorrection',
             BooleanTrait(False, label='Error correction')),

            ('secondary_featureextraction',
             BooleanTrait(False, label='Feature Extraction')),
            ('secondary_classification',
             BooleanTrait(False, label='Classification')),
            ('secondary_errorcorrection',
             BooleanTrait(False, label='Error correction')),

            ('tertiary_featureextraction',
             BooleanTrait(False, label='Feature Extraction')),
            ('tertiary_classification',
             BooleanTrait(False, label='Classification')),
            ('tertiary_errorcorrection',
             BooleanTrait(False, label='Error correction')),

            ('merged_featureextraction',
             BooleanTrait(False, label='Feature Extraction')),
            ('merged_classification',
             BooleanTrait(False, label='Classification')),
            ('merged_errorcorrection',
             BooleanTrait(False, label='Error correction')),
            ]
          )
         ]
