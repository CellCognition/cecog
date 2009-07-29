"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['MetaDataFrame',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import (StyledSideFrame,
                            StyledLabel,
                            )

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class MetaDataFrame(StyledSideFrame):

    def __init__(self, parent):
        super(MetaDataFrame, self).__init__(parent)

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.addWidget(StyledLabel('Positions:', self), 0, 0)
        self.layout.addWidget(StyledLabel('Time:', self), 1, 0)
        self.layout.addWidget(StyledLabel('Channels:', self), 2, 0)
        self.layout.addWidget(StyledLabel('ZSlices:', self), 3, 0)
        self.layout.addWidget(StyledLabel('Height:', self), 4, 0)
        self.layout.addWidget(StyledLabel('Width:', self), 5, 0)

        self.positions_label = StyledLabel(self)
        self.times_label = StyledLabel(self)
        self.channels_label = StyledLabel(self)
        self.zslices_label = StyledLabel(self)
        self.height_label = StyledLabel(self)
        self.width_label = StyledLabel(self)

        self.layout.addWidget(self.positions_label, 0, 1)
        self.layout.addWidget(self.times_label, 1, 1)
        self.layout.addWidget(self.channels_label, 2, 1)
        self.layout.addWidget(self.zslices_label, 3, 1)
        self.layout.addWidget(self.height_label, 4, 1)
        self.layout.addWidget(self.width_label, 5, 1)

        self.setLayout(self.layout)

    def update_metadata(self, meta_data):
        self.positions_label.setText(str(meta_data.dim_p))
        self.times_label.setText(str(meta_data.dim_t))
        self.channels_label.setText(str(meta_data.dim_c))
        self.zslices_label.setText(str(meta_data.dim_z))
        self.height_label.setText(str(meta_data.dim_y))
        self.width_label.setText(str(meta_data.dim_x))


#-------------------------------------------------------------------------------
# main:
#

