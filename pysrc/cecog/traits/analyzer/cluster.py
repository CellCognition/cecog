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

__all__ = ['SectionCluster']

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
from cecog.gui.guitraits import IntTrait

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_CLUSTER = 'Cluster'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionCluster(_Section):

    SECTION_NAME = SECTION_NAME_CLUSTER

    OPTIONS = [
      ('cluster',
       [('position_granularity',
            IntTrait(1, 1, 1000, label='Batch size (non-timelapse)')),
        ])
      ]