"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Christoph Sommer'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['SectionPostProcessing']

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
from cecog.gui.guitraits import (StringTrait,
                                 BooleanTrait,
                                 FloatTrait,
                                 IntTrait,
                                 )

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_EVENT_SELECTION = 'EventSelection'



#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionEventSelection(_Section):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION

    OPTIONS = [
      ('event_selection',
       [
        ('test_key',
            BooleanTrait(False, label='Test Bool')),
        ]
       )
    ]
