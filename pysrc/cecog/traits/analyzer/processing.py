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
from cecog.util.util import unlist
from cecog import CH_OTHER, CH_VIRTUAL

SECTION_NAME_PROCESSING = 'Processing'


class SectionProcessing(SectionCore):

    SECTION_NAME = SECTION_NAME_PROCESSING

    OPTIONS = [
      ('processing',
       [
        ('objectdetection',
            BooleanTrait(True, label='Object detection')),
        ('primary_featureextraction',
            BooleanTrait(True, label='Feature Extraction')),
        ('primary_classification',
            BooleanTrait(False, label='Classification')),
        ('tracking',
            BooleanTrait(False, label='Tracking')),
        ('tracking_synchronize_trajectories',
            BooleanTrait(False, label='Event selection')),
        ('primary_errorcorrection',
            BooleanTrait(False, label='Error correction')),
        ] +\
        unlist(
        [[('%s_processchannel' % x,
            BooleanTrait(False, label='%s channel' % x.capitalize())),
          #('secondary_objectdetection',
          #    BooleanTrait(True, label='Object detection')),
          ('%s_featureextraction' % x,
            BooleanTrait(False, label='Feature Extraction')),
          ('%s_classification' % x,
            BooleanTrait(False, label='Classification')),
          ('%s_errorcorrection' % x,
            BooleanTrait(False, label='Error correction')),
          ] for x in (CH_OTHER+CH_VIRTUAL)]
        )
      )]
