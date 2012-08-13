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

__all__ = ['SectionClassification']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog import CHANNEL_PREFIX
from cecog.traits.settings import _Section
from cecog.gui.guitraits import (StringTrait,
                                 BooleanTrait,
                                 SelectionTrait2,
                                 )
from cecog.util.util import unlist

#-------------------------------------------------------------------------------
# constants:
#
SECTION_NAME_CLASSIFICATION = 'Classification'

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class SectionClassification(_Section):

    SECTION_NAME = SECTION_NAME_CLASSIFICATION

    OPTIONS = \
    unlist(
    [[('%s_classification' % x,
     [('%s_classification_envpath' % x, StringTrait('', 1000, label='Classifier folder',
                                                    widget_info=StringTrait.STRING_PATH)),
      ('%s_classification_regionname' % x, SelectionTrait2(None, [], label='Region name')),
      ('%s_classification_annotationfileext' % x, StringTrait('.xml', 50, label='Annotation ext.')),
      ])]
      for x in CHANNEL_PREFIX]
      ) + \
      [
      ('collectsamples',
       [('collectsamples', BooleanTrait(False)),
        ('collectsamples_prefix', StringTrait('',100)),
        ])
      ]
