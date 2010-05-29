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

__all__ = ['SectionProcessing']

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
from cecog.traits.guitraits import BooleanTrait

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_PROCESSING = 'Processing'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionProcessing(_Section):

    SECTION_NAME = SECTION_NAME_PROCESSING

    OPTIONS = [
        ('primary_classification',
            BooleanTrait(False, label='Classification')),
        ('tracking',
            BooleanTrait(False, label='Tracking')),
        ('tracking_synchronize_trajectories',
            BooleanTrait(False, label='Event selection')),
        ('primary_errorcorrection',
            BooleanTrait(False, label='Error correction')),
        ('secondary_processchannel',
            BooleanTrait(False, label='Secondary channel')),
        ('secondary_classification',
            BooleanTrait(False, label='Classification')),
        ('secondary_errorcorrection',
            BooleanTrait(False, label='Error correction')),
        ]