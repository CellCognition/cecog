"""
progressdialog.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import traceback
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt



class ProgressThread(QtCore.QThread):

    error = QtCore.pyqtSignal("PyQt_PyObject")
    result = QtCore.pyqtSignal("PyQt_PyObject")

    def start(self, target, qobjects):
        self._target = target
        self._qobjects = qobjects
        if qobjects is not None:
            for qobject in qobjects:
                qobject.moveToThread(self)
        return super(ProgressThread, self).start()

    def run(self):
        try:
            result = self._target()
            self.result.emit(result)
        except Exception as e:
            stackstr = traceback.print_exc()
            self.error.emit(e)
            raise
        finally:
            # perhaps processEvents()???
            self.msleep(150)
            if self._qobjects is not None:
                for qobject in self._qobjects:
                    qobject.moveToThread(
                        QtWidgets.QApplication.instance().thread())
        self.result.emit(result)


class ProgressObject(QtCore.QObject):
    """Helper class to emit signals to the progress dialog from
    the function to be execute in the thread."""

    setValue = QtCore.pyqtSignal(int)
    setRange = QtCore.pyqtSignal(int, int)
    setLabelText = QtCore.pyqtSignal("PyQt_PyObject")


class ProgressDialog(QtWidgets.QProgressDialog):
    """Subclass of QProgressDialog to:
         -) ignore the ESC key during dialog exec_()
         -) to provide mechanism to show the dialog only
            while a target function is running
    """

    def __init__(self, *args, **kw):
        super(ProgressDialog, self).__init__(*args, **kw)
        self.setWindowModality(Qt.WindowModal)
        self.setCancelButton(None)
        self.setAutoClose(False)
        self._error = None

        self.thread = ProgressThread(self)
        self.thread.finished.connect(self.close)
        self.thread.finished.connect(self.hide)
        self.thread.result.connect(self.setTargetResult)
        self.thread.error.connect(self.onError)

        # avoid progressbar with just one step
        if self.maximum() == 1:
            self.setMaximum(0)

    def setCancelButton(self, cancelButton):
        self.hasCancelButton = cancelButton is not None
        super(ProgressDialog, self).setCancelButton(cancelButton)

    def keyPressEvent(self, event):
        if event.key() != Qt.Key_Escape or \
                getattr(self, 'hasCancelButton', False):
            super(ProgressDialog, self).keyPressEvent(event)

    def getTargetResult(self):
        return getattr(self, '_target_result', None)

    def setTargetResult(self, result):
        self._target_result = result

    def setRange(self, *args, **kw):
        super(ProgressDialog, self).setRange(*args, **kw)

    def onError(self, exc):
        self._error = exc

    def close(self):
        if self.thread.isRunning():
            self.thread.wait()
        super(ProgressDialog, self).close()

    def exec_(self, target, qobjects=None):
        self.thread.start(target, qobjects)
        ret = super(ProgressDialog, self).exec_()

        if isinstance(self._error, Exception):
            raise self._error

        return ret


if __name__ == '__main__':
    app = QtWidgets.QApplication([''])

    import time
    dlg = ProgressDialog('labeltext', "buttontext", 0, 0, None)

    def foo(t):
        print 'running long long target function for %d seconds' % t,
        time.sleep(t)
        print ' ...finished'
        return 42

    # This is optional.
    # If not specified, the standard ProgressDialog is used
    res = dlg.exec_(lambda: foo(3))
    print 'result of dialog target function is:', dlg.getTargetResult()
