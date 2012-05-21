"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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
                                 )

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_POST_PROCESSING = 'PostProcessing'



#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionPostProcessing(_Section):

    SECTION_NAME = SECTION_NAME_POST_PROCESSING

    OPTIONS = [
      ('post_processing',
       [
        ('ibb_analysis',
            BooleanTrait(True, label='IBB analysis')),

        ('mappingfile_path',
            StringTrait('', 1000, label='Mapping filename',
                                   widget_info=StringTrait.STRING_PATH)),
        
        ('ibb_export_single_events',
            BooleanTrait(True, label='Export single event plots',)),
        
        ('ibb_groupby_position',
            BooleanTrait(True, label='Position',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('ibb_groupby_oligoid',
            BooleanTrait(False, label='Oligo ID',
                         widget_info=BooleanTrait.RADIOBUTTON)),
        ('ibb_groupby_genesymbol',
            BooleanTrait(False, label='Gene symbol',
                         widget_info=BooleanTrait.RADIOBUTTON))
        ]
       )
    ]
