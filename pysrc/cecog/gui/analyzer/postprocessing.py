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

__all__ = ['FeaturePostProcessingFrame']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits.analyzer.postprocessing import SECTION_NAME_POST_PROCESSING
from cecog.gui.util import (information,
                            exception,
                            )
from cecog.gui.analyzer import (BaseProcessorFrame,
                                AnalzyerThread,
                                TrainingThread,
                                )
from cecog.analyzer import SECONDARY_REGIONS
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.learning.learning import (CommonClassPredictor,
                                     )
from cecog.util.util import hexToRgb
from cecog.traits.config import convert_package_path

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class PostProcessingFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_POST_PROCESSING
    DISPLAY_NAME = r'Post-processing Plots'

    def __init__(self, settings, parent):
        super(PostProcessingFrame, self).__init__(settings, parent)

        self.add_group(None,
                       [('ibb_groupby_position',),
                        ('ibb_groupby_oligoid',),
                        ('ibb_groupby_genesymbol',),
                        ], layout='flow', link='groupby', label='Group by')
        self.add_expanding_spacer()

        #self._init_control()

