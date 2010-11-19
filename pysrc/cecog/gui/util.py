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

__all__ = ['QRC_TOKEN',
           'ImageRatioDisplay',
           'numpy_to_qimage',
           'message',
           'information',
           'question',
           'warning',
           'critical',
           'exception',
           'status',
           'load_qrc_text',
           'show_html',
           'on_anchor_clicked',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       traceback

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.platform import on_mac

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.util.color import rgb_to_hex

#-------------------------------------------------------------------------------
# constants:
#
QRC_TOKEN = 'qrc:/'


#-------------------------------------------------------------------------------
# functions:
#
def numpy_to_qimage(data, colors=None):
    w, h = data.shape[:2]
    #print data.shape, data.ndim
    if data.dtype == numpy.uint8:
        if data.ndim == 2:
            shape = (numpy.ceil(w / 4.) * 4, h)
            if shape != data.shape:
                image = numpy.zeros(shape, numpy.uint8, 'C')
                image[:w,:] = data
            else:
                image = data
            format = QImage.Format_Indexed8
            #colors = [QColor(i,i,i) for i in range(256)]
        elif data.ndim == 3:
            c = data.shape[2]
            shape = (int(numpy.ceil(w / 4.) * 4), h, c)
            if c == 3:
                if shape != data.shape:
                    image = numpy.zeros(shape, numpy.uint8)
                else:
                    image = data
                format = QImage.Format_RGB888
            elif data.shape[2] == 4:
                format = QImage.Format_RGB32

    qimage = QImage(image, w, h, format)
    qimage.ndarray = image
    if not colors is None:
        for idx, col in enumerate(colors):
            qimage.setColor(idx, col.rgb())
    return qimage

def message(icon, text, parent, info=None, detail=None, buttons=None,
            title=None, default=None, escape=None, modal=False):
    if title is None:
        title = text
    msg_box = QMessageBox(icon, title, text, QMessageBox.NoButton,
                          parent, Qt.Dialog)
    if on_mac() and modal:
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

def information(parent, text, info=None, detail=None, modal=False):
    return message(QMessageBox.Information,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def question(parent, text, info=None, detail=None, modal=False,
             show_cancel=False, default=None, escape=None):
    buttons = QMessageBox.Yes|QMessageBox.No
    if default is None:
        default = QMessageBox.No
    if escape is None:
        escape = default
    if show_cancel:
        buttons |= QMessageBox.Cancel
    result = message(QMessageBox.Question,
                     text, parent, info=info, detail=detail, modal=modal,
                     buttons=buttons, default=default, escape=escape)
    if show_cancel:
        return result
    else:
        return result == QMessageBox.Yes

def warning(parent, text, info=None, detail=None, modal=False):
    return message(QMessageBox.Warning,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def critical(parent, text=None, info=None, detail=None, detail_tb=False,
             tb_limit=None, modal=False):
    if detail_tb and detail is None:
        detail = traceback.format_exc(tb_limit)
    return message(QMessageBox.Critical,
                   text, parent, info=info, detail=detail, modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)

def exception(parent, text, tb_limit=None, modal=False):
    type, value = sys.exc_info()[:2]
    return message(QMessageBox.Critical,
                   text, parent,
                   info='%s : %s ' % (str(type.__name__), str(value)),
                   detail=traceback.format_exc(tb_limit), modal=modal,
                   buttons=QMessageBox.Ok, default=QMessageBox.Ok)


def status(msg, timeout=0):
    qApp._statusbar.showMessage(msg, timeout)


def load_qrc_text(name):
    file_name = ':%s' % name
    f = QFile(file_name)
    text = None
    if f.open(QIODevice.ReadOnly | QIODevice.Text):
        s = QTextStream(f)
        text = str(s.readAll())
        f.close()
    return text


def show_html(name, link='_top', title=None,
              header='_header', footer='_footer'):
    if not hasattr(qApp, 'cecog_help_dialog'):
        dialog = QFrame()
        if title is None:
            title = name
        dialog.setWindowTitle('CecogAnalyzer Help')
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        w_text = QTextBrowser(dialog)
        w_text.setOpenLinks(False)
        w_text.setOpenExternalLinks(False)
        w_text.connect(w_text, SIGNAL('anchorClicked ( const QUrl & )'),
                       on_anchor_clicked)
        layout.addWidget(w_text)
        dialog.setMinimumSize(QSize(900,600))
        qApp.cecog_help_dialog = dialog
        qApp.cecog_help_wtext = w_text
    else:
        dialog = qApp.cecog_help_dialog
        w_text = qApp.cecog_help_wtext

    w_text.clear()
    html_text = load_qrc_text('help/%s.html' % name.lower())
    if not html_text is None:
        css_text = load_qrc_text('help/help.css')

        if not header is None:
            header_text = load_qrc_text('help/%s.html' % header)
            if not header_text is None:
                html_text = html_text.replace('<!-- HEADER -->', header_text)

        if not footer is None:
            footer_text = load_qrc_text('help/%s.html' % footer)
            if not footer_text is None:
                html_text = html_text.replace('<!-- FOOTER -->', footer_text)

        doc = QTextDocument()
        if not css_text is None:
            doc.setDefaultStyleSheet(css_text)
        doc.setHtml(html_text)
        w_text.setDocument(doc)
        #FIXME: will cause a segfault when ref is lost
        w_text._doc = doc
        if not link is None:
            w_text.scrollToAnchor(link)
    else:
        w_text.setHtml("We are sorry, but help for '%s' was not found." % name)
    dialog.show()
    dialog.raise_()


def on_anchor_clicked(link):
    slink = str(link.toString())
    if slink.find(QRC_TOKEN) == 0:
        items = slink.split('#')
        show_html(items[0].replace(QRC_TOKEN, ''))
        if len(items) > 1:
            qApp.cecog_help_wtext.scrollToAnchor(items[1])
    elif slink.find('#') == 0:
        qApp.cecog_help_wtext.scrollToAnchor(slink[1:])
    else:
        QDesktopServices.openUrl(link)

def qcolor_to_hex(qcolor):
    return rgb_to_hex(qcolor.red(), qcolor.green(), qcolor.blue())

def get_qcolor_hicontrast(qcolor, threshold=0.5):
    lightness = qcolor.lightnessF()
    return QColor('white' if lightness <= threshold else 'black')



#-------------------------------------------------------------------------------
# classes:
#
class ImageRatioDisplay(QLabel):

    def __init__(self, parent, ratio):
        QLabel.__init__(self, parent,
                        Qt.CustomizeWindowHint|Qt.WindowCloseButtonHint|
                        Qt.WindowMinimizeButtonHint|Qt.SubWindow)
        self._ratio = ratio

    def set_ratio(self, ratio):
        self._ratio = ratio

    def heightForWidth(self, w):
        return int(w*self._ratio)
