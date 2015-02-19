"""
progresswidget.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ('ProcessControl', )


from PyQt5 import QtGui


class ProcessControl(QtGui.QFrame):

    def __init__(self, *args, **kw):
        super(ProcessControl, self).__init__(*args, **kw)

        self._buttons = dict()

        layout = QtGui.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QtGui.QLabel('', self)

        self._progressbar = QtGui.QProgressBar(self)
        self._progressbar.setTextVisible(False)

        self._show_image = QtGui.QCheckBox('Show images', self)
        self._show_image.setChecked(True)

        button = QtGui.QToolButton(self)
        button.setIcon(QtGui.QIcon(':question_mark'))
        button.clicked.connect(
            lambda: self.parent()._on_show_help('controlpanel'))

        layout.addWidget(self._label)
        layout.addWidget(self._progressbar)
        layout.addWidget(self._show_image)
        layout.addWidget(button)

    def __del__(self):
        for key in self._buttons.keys():
            del self._buttons[key]

    def clearText(self):
        self._label.clear()

    def showImages(self):
        return self._show_image.isChecked()

    def setProgress(self, value):
        self._progressbar.setValue(value)
        maximum = self._progressbar.maximum()
        try:
            self._label.setText('%3.1f%%' %(value*100.0/maximum))
        except ZeroDivisionError:
            pass

    def setRange(self, min, max):
        self._progressbar.setRange(min, max)

    def showImageCheckBox(self):
        self._show_image.show()

    def hideImageCheckBox(self):
        self._show_image.hide()

    def addControlButton(self, name, slot):
        count = self.layout().count() - 1
        button = QtGui.QPushButton('', self)
        button.clicked.connect(slot)
        self.layout().insertWidget(count, button)
        self._buttons[name] = button

    def buttonByName(self, name):
        # XXX find a way to make this function obsolete
        return self._buttons[name]

    def setButtonsEnabled(self, state):
        for button in self._buttons.values():
            button.setEnabled(state)

    def toggleButtons(self, exception):

        for name, button in self._buttons.iteritems():
            if name == exception:
                continue
            else:
                button.setEnabled(not button.isEnabled())
