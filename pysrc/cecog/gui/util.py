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
    h, w = data.shape[:2]
    #print data.dtype, data.ndim, data.shape
    if data.dtype == numpy.uint8:
        if data.ndim == 2:
            shape = (h, w / 4 * 4)
            if shape != data.shape:
                h, w = shape
                image = data[:,:w]
            else:
                image = data
            image = numpy.require(image, numpy.uint8, 'C')
            format = QImage.Format_Indexed8
            if colors is None:
                colors = [QColor(i,i,i) for i in range(256)]
        elif data.ndim == 3:
            if data.shape[2] == 3:
                c = data.shape[2]
                shape = (h, w / 4 * 4, c)
                if shape != data.shape:
                    image = numpy.zeros(shape, numpy.uint8)
                else:
                    image = data
                format = QImage.Format_RGB888
            elif data.shape[0] == 3:
                w, h = data.shape[1:3]
                image = data
                format = QImage.Format_RGB32
    qimage = QImage(image, w, h, format)
    qimage.ndarray = image
    if not colors is None:
        qimage.setColorTable(colors)
    return qimage

def message(icon, text, parent, info=None, detail=None, buttons=None,
            title=None, default=None, escape=None, modal=True):
    if title is None:
        title = text
    msg_box = MyMessageBox(icon, title, text, QMessageBox.NoButton,
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
    blue = qcolor.blueF()
    # decrease the lightness by the color blueness
    value = lightness - 0.2 * blue
    return QColor('white' if value <= threshold else 'black')



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


class MyMessageBox(QMessageBox):

    def showEvent(self, event):
        QMessageBox.showEvent(self, event)
        #self.setFixedSize(400, 100)

class ProgressDialog(QProgressDialog):

    targetFinished = pyqtSignal()
    targetSetValue = pyqtSignal(int)

    '''
    inherited QProgressDialog to ...
       ... ignore the ESC key during dialog exec_()
       ... to provide mechanism to show the dialog only
           while a target function is running
    '''

    def setCancelButton(self, cancelButton):
        self.hasCancelButton = cancelButton is not None
        super(ProgressDialog, self).setCancelButton(cancelButton)

    def keyPressEvent(self, event):
        if event.key() != Qt.Key_Escape or getattr(self, 'hasCancelButton', False):
            QProgressDialog.keyPressEvent(self, event)

    def setTarget(self, target, *args, **options):
        self._target = target
        self._args = args
        self._options = options

    def getTargetResult(self):
        return getattr(self, '_target_result', None)

    def _onSetValue(self, value):
        self.setValue(value)

    def exec_(self, finished=None, started=None, passDialog=False):
        dlg_result = None
        self.targetSetValue.connect(self._onSetValue)
        if hasattr(self, '_target'):
            t = QThread()
            if finished is None:
                finished = self.close
            t.finished.connect(finished)
            if started is not None:
                t.started.connect(started)

            def foo():
                # optional passing of this dialog instance to the target function
                if passDialog:
                    t.result = self._target(self, *self._args, **self._options)
                else:
                    t.result = self._target(*self._args, **self._options)
                self.targetFinished.emit()

            t.result = None
            t.run = foo
            t.start()
            dlg_result = super(QProgressDialog, self).exec_()
            t.wait()
            self._target_result = t.result
        else:
            dlg_result = super(QProgressDialog, self).exec_()
        return dlg_result


def waitingProgressDialog(msg, parent=None, target=None, range=(0,0)):
    dlg = ProgressDialog(parent, Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setLabelText(msg)
    dlg.setCancelButton(None)
    dlg.setRange(*range)
    if target is not None:
        dlg.setTarget(target)
    return dlg


if __name__ == '__main__':
    app = QApplication([''])

    import time
    dlg = ProgressDialog('still running...', 'Cancel', 0, 0, None)

    def foo(t):
        print 'running long long target function for %d seconds' % t,
        time.sleep(t)
        print ' ...finished'
        return 42

    # This is optional.
    # If not specified, the standard ProgressDialog is used
    dlg.setTarget(foo, 3)

    res = dlg.exec_()
    print 'result of dialog target function is:', res

    app.exec_()


