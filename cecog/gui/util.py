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

__all__ = ['message','information', 'question',
           'warning', 'critical', 'exception']

import sys
import traceback
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from cecog.colors import rgb2hex

def message(icon, text, parent, info=None, detail=None, buttons=None,
            title=None, default=None, escape=None, modal=True):
    if title is None:
        title = text
    msg_box = QMessageBox(icon, title, text, QMessageBox.NoButton,
                          parent)
    if modal:
        msg_box.setWindowModality(Qt.WindowModal)
    if not info is None:
        msg_box.setInformativeText(info)
    if not detail is None:
        msg_box.setDetailedText(detail)
    if not buttons is None:
        msg_box.setStandardButtons(buttons)
    if not default is None:
        msg_box.setDefaultButton(default)
    if not escape is None:
        msg_box.setEscapeButton(escape)
    return msg_box.exec_()

def information(parent, text, info=None, detail=None, modal=True):
    return message(QMessageBox.Information,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def question(parent, text, info=None, detail=None, modal=True,
             show_cancel=False, default=None, escape=None, icon=QMessageBox.Question):
    buttons = QMessageBox.Yes|QMessageBox.No
    if default is None:
        default = QMessageBox.No
    if escape is None:
        escape = default
    if show_cancel:
        buttons |= QMessageBox.Cancel
    result = message(icon,
                     text, parent, info=info, detail=detail, modal=modal,
                     buttons=buttons, default=default, escape=escape)
    if show_cancel:
        return result
    else:
        return result == QMessageBox.Yes

def warning(parent, text, info=None, detail=None, modal=True):
    return message(QMessageBox.Warning,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def critical(parent, text=None, info=None, detail=None, detail_tb=False,
             tb_limit=None, modal=True):
    if detail_tb and detail is None:
        detail = traceback.format_exc(tb_limit)
    return message(QMessageBox.Critical,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def exception(parent, text, tb_limit=None, modal=True):
    type, value = sys.exc_info()[:2]
    return message(QMessageBox.Critical,
                   text, parent,
                   detail=traceback.format_exc(tb_limit), modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def qcolor_to_hex(qcolor):
    return rgb2hex((qcolor.red(), qcolor.green(), qcolor.blue()), mpl=False)

def get_qcolor_hicontrast(qcolor, threshold=0.5):
    lightness = qcolor.lightnessF()
    blue = qcolor.blueF()
    # decrease the lightness by the color blueness
    value = lightness - 0.2 * blue
    return QColor('white' if value <= threshold else 'black')
