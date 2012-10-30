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
from cecog.traits.analyzer.eventselection import SECTION_NAME_EVENT_SELECTION
from cecog.gui.util import (information,
                            exception,
                            )
from cecog.gui.analyzer import (BaseProcessorFrame,
                                PostProcessingThread,
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

class EventSelectionFrame(BaseProcessorFrame):

    SECTION_NAME = SECTION_NAME_EVENT_SELECTION
    DISPLAY_NAME = 'Event Selection'

    def __init__(self, settings, parent):
        super(EventSelectionFrame, self).__init__(settings, parent)
        
        #### IMPORTANT LINE HERE: DESIGN NEW EVENT SELECTION PROCESSING THREAD BY TEARING APPART THE OLD TRACKING 
        self.register_control_button('event_selection',
                                     PostProcessingThread,
                                     ('Start', 'Stop'))
        
        self.add_group(None, [('test_key',)], label='Test Bool')
        
        self.add_expanding_spacer()

        self._init_control(has_images=False)

