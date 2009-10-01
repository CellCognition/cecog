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
                            StyledButton,
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

        self.meta_data = None

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop|Qt.AlignCenter)
        self.layout.addWidget(StyledLabel('Positions:', self), 0, 0, Qt.AlignRight)
        self.layout.addWidget(StyledLabel('Time:', self), 1, 0, Qt.AlignRight)
        self.layout.addWidget(StyledLabel('Channels:', self), 2, 0, Qt.AlignRight)
        self.layout.addWidget(StyledLabel('ZSlices:', self), 3, 0, Qt.AlignRight)
        self.layout.addWidget(StyledLabel('Height:', self), 4, 0, Qt.AlignRight)
        self.layout.addWidget(StyledLabel('Width:', self), 5, 0, Qt.AlignRight)

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

        self.btn_export1 = StyledButton('Export Absolute Timestamps', self)
        self.btn_export1.setEnabled(False)
        #self.btn_export1.setFlat(True)
        self.btn_export2 = StyledButton('Export Relative Timestamps', self)
        self.btn_export2.setEnabled(False)
        self.connect(self.btn_export1, SIGNAL('clicked()'),
                     self._on_export_absolute)
        self.connect(self.btn_export2, SIGNAL('clicked()'),
                     self._on_export_relative)

        self.layout.addWidget(self.btn_export1, 10, 0, 1, 2,
                              Qt.AlignBottom)
        self.layout.addWidget(self.btn_export2, 11, 0, 1, 2,
                              Qt.AlignBottom)
        self.setLayout(self.layout)

    def _on_export_absolute(self):
        filename = self._get_save_filename('absolute timestamps')
        if not filename is None:
            self._write_timestamps(filename, absolute=True)

    def _on_export_relative(self):
        filename = self._get_save_filename('relative timestamps')
        if not filename is None:
            self._write_timestamps(filename, absolute=False)

    def _get_save_filename(self, name):
        dialog = QFileDialog(self,
                            'Save %s...' % name)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setDefaultSuffix('tsv')
        if dialog.exec_():
            filename = str(dialog.selectedFiles()[0])
        else:
            filename = None
        return filename

    def _write_timestamps(self, filename, absolute=True, sep='\t'):
        f = file(filename, 'w')
        f.write('%s\n' % sep.join(map(str, self.meta_data.positions)))
        for t in self.meta_data.times:
            timestamps = []
            for p in self.meta_data.positions:
                if absolute:
                    ts = self.meta_data.get_timestamp_absolute(p, t)
                else:
                    ts = self.meta_data.get_timestamp_relative(p, t)
                timestamps.append(ts)
            f.write('%s\n' % sep.join(['%.3f' % v for v in timestamps]))
        f.close()

    def update_metadata(self, meta_data):
        self.meta_data = meta_data
        self.positions_label.setText(str(meta_data.dim_p))
        self.times_label.setText(str(meta_data.dim_t))
        self.channels_label.setText(str(meta_data.dim_c))
        self.zslices_label.setText(str(meta_data.dim_z))
        self.height_label.setText(str(meta_data.dim_y))
        self.width_label.setText(str(meta_data.dim_x))
        self.btn_export1.setEnabled(True)
        self.btn_export2.setEnabled(True)


#-------------------------------------------------------------------------------
# main:
#

