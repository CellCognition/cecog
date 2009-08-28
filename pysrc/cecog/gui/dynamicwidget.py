"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['PhenoDialog',
           'PhenoFrame',
           'PhenoStyledSideFrame',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import time
import sys
import os

#------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.phenes import *

from cecog.gui.util import (StyledFrame,
                            StyledSideFrame,
                            )

#------------------------------------------------------------------------------
# constants:
#
IMAGE_QUESTIONMARK = os.path.join(os.path.split(__file__)[0],
                                  'resources', 'QuestionMark.png')

QT_DIALOG = 'QT_DIALOG'
QT_FRAME = 'QT_FRAME'


#------------------------------------------------------------------------------
# helper functions:
#

def visualize_phenotype(parent, phenotype, kind=QT_DIALOG):
    '''
    Helper function visualizing a PhenoType either as QFrame or QDialog.
    '''
    if kind == QT_DIALOG:
        widget = PhenoDialog(parent, phenotype)
    elif kind == QT_FRAME:
        widget = PhenoFrame(parent, phenotype)
    else:
        raise ValueError("Kind '%s' not supported." % kind)
    return widget


#------------------------------------------------------------------------------
# classes:
#

class _PhenoWidget(object):

    def __init__(self, phenotype):
        self.phenotype = phenotype
        self._display_phenes()

    def _display_phenes(self):
        layout = QGridLayout()

        print self.phenotype
        for idx, (name, phene) in \
            enumerate(self.phenotype.get_phenes().iteritems()):
            if phene.label is None:
                label = name
            else:
                label = phene.label
            row = idx

            # label
            widget = QLabel(label, self)
            widget.setAlignment(Qt.AlignRight|
                                Qt.AlignTrailing|
                                Qt.AlignVCenter)
            layout.addWidget(widget, row, 0)

            # the value-widgets
            value = getattr(self.phenotype, name)
            if isinstance(phene, Int) or isinstance(phene, Float):
                if isinstance(phene, Int):
                    widget_cls = QSpinBox
                    signal = 'valueChanged(int)'
                else:
                    widget_cls = QDoubleSpinBox
                    signal = 'valueChanged(double)'
                widget = widget_cls(self)
                if not phene.min_value is None:
                    widget.setMinimum(phene.min_value)
                if not phene.max_value is None:
                    widget.setMaximum(phene.max_value)
                widget.setValue(value)
                shedule = lambda x: lambda y: self._setValue(x, y)
                self.connect(widget,
                             SIGNAL(signal),
                             shedule(name))
            elif isinstance(phene, Boolean):
                widget = QCheckBox(self)
                widget.setTristate(False)
                if value is None:
                    widget.setCheckState(0)
                else:
                    widget.setCheckState(Qt.Checked if value
                                         else Qt.Unchecked)
                shedule = lambda x: lambda y: self._setState(x, y)
                self.connect(widget,
                             SIGNAL('stateChanged(int)'),
                             shedule(name))
            elif isinstance(phene, String):
                widget = QLineEdit(self)
                widget.setText(value)
                widget.setReadOnly(phene.is_immutable)
                #widget.setInputMask('000.000.000.000;_')
                if not phene.max_length is None:
                    widget.setMaxLength(phene.max_length)
                if not phene.mask is None:
                    regexp = QRegExp(phene.mask.pattern)
                    regexp.setPatternSyntax(QRegExp.RegExp2)
                    widget.setValidator(QRegExpValidator(regexp,
                                                         widget))
                shedule = lambda x,y: lambda z: self._setText(x, y, z)
                self.connect(widget,
                             SIGNAL('textEdited(QString)'),
                             shedule(widget, name))
            elif isinstance(phene, List):
                widget = QComboBox(self)
                widget.addItems(value)
            else:
                widget = QLineEdit(str(value), self)
                shedule = lambda x: lambda y: self._setValue(x, y)
                self.connect(widget,
                             SIGNAL('textEdited(QString)'),
                             shedule(name))

            # tooltip
            if not phene.tooltip is None:
                widget.setToolTip(phene.tooltip)
            layout.addWidget(widget, row, 1)

            # more help: doc dialog button
            if not phene.doc is None:
                widget = QToolButton(self)
                widget.setIcon(QIcon(IMAGE_QUESTIONMARK))
                shedule = lambda x: lambda: self._showDoc(x)
                self.connect(widget,
                             SIGNAL('clicked()'),
                             shedule(phene.doc))
                layout.addWidget(widget, row, 2)

        layout.setAlignment(Qt.AlignCenter|
                            Qt.AlignVCenter)
        self.setLayout(layout)
        self.show()

    def _showDoc(self, doc):
        widget = QMessageBox().information(self, 'Help', doc)

    def _setValue(self, name, value):
        setattr(self.phenotype, name, value)
        print getattr(self.phenotype, name)

    def _setState(self, name, state):
        if state == Qt.Checked:
            value = True
        elif state == Qt.Unchecked:
            value = False
        else:
            value = None
        setattr(self.phenotype, name, value)
        print getattr(self.phenotype, name)

    def _setText(self, widget, name, value):
        if widget.hasAcceptableInput():
            setattr(self.phenotype, name, value)
            widget.setPalette(self.palette())
            widget.update()
            print getattr(self.phenotype, name)
        else:
            print "wrong value '%s', keep '%s'" %\
                  (value, getattr(self.phenotype, name))
            pal = widget.palette()
            pal.setColor(QPalette.Base, QColor(255,40,40))
            widget.setPalette(pal)
            widget.update()


class PhenoFrame(QFrame, _PhenoWidget):

    def __init__(self, phenotype, parent):
        QFrame.__init__(self, parent)
        _PhenoWidget.__init__(self, phenotype)


class PhenoDialog(QDialog, _PhenoWidget):

    def __init__(self, phenotype, parent):
        QDialog.__init__(self, parent)
        _PhenoWidget.__init__(self, phenotype)


class PhenoStyledSideFrame(StyledSideFrame, _PhenoWidget):

    def __init__(self, phenotype, parent):
        StyledSideFrame.__init__(self, parent)
        _PhenoWidget.__init__(self, phenotype)

