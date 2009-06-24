import sys, time

from PyQt4 import QtCore, QtGui

from pdk.phenes import *
from cecog.gui.dynamicwidget import (visualize_phenotype,
                                     QT_DIALOG,
                                     QT_FRAME)

#------------------------------------------------------------------------------
# main:
#

if __name__ == "__main__":

    class Test(PhenoType):

        b = Float(1.0, label='mooo123', tooltip='This is very cool!',
                  doc='some text',
                  rank=10)

        a = Int(min_value=0,
                doc='some other text',
                is_mandatory=True)

        c = List(['abc', '123'])

        d = Boolean(True)

#        g = Boolean(allow_na=True,
#                    tooltip='No value is given here, this should invoke '\
#                            'the tri-state checkbox.')

        e = String('abcd123', max_length=10)

        f = String('abcd123', mask='^abcd\d+',
                   label='Fancy RegExp Validator',
                   doc='Input is constrained by regular expression '\
                       '"^abcd\d+".\nOnly "abcd" followed by any number of '\
                       'digits is accepted.')

    class MainWindow(QtGui.QMainWindow):
        def __init__(self, phenotype):
            QtGui.QMainWindow.__init__(self)

            self.setGeometry(0, 0, 600, 400)
            self.setWindowTitle('Dynamic dialog generation with pdk.phenes')

            frame = QtGui.QFrame(self)
            self.setCentralWidget(frame)

            self.phenotype = phenotype

            self.frame_widget = None
            self.dialog_widget = None

            self.layout = QtGui.QVBoxLayout()
            self.layout.setAlignment(QtCore.Qt.AlignTop)
            widget = QtGui.QPushButton('Dialog Demo', self)
            self.connect(widget, QtCore.SIGNAL('clicked()'), self._onShowDialog)
            self.layout.addWidget(widget)
            widget = QtGui.QPushButton('Frame Demo', self)
            self.connect(widget, QtCore.SIGNAL('clicked()'), self._onShowFrame)
            self.layout.addWidget(widget)
            frame.setLayout(self.layout)
            frame.show()

            self.center()
            self.show()
            self.raise_()

        def _onShowFrame(self):
            time.sleep(.1)
            if not self.dialog_widget is None:
                self.dialog_widget.close()
                self.dialog_widget = None
            if self.frame_widget is None:
                self.frame_widget = visualize_phenotype(self,
                                                        self.phenotype,
                                                        QT_FRAME)
                self.layout.addWidget(self.frame_widget)
            self.update()

        def _onShowDialog(self):
            time.sleep(.1)
            if not self.frame_widget is None:
                self.layout.removeWidget(self.frame_widget)
                self.frame_widget.destroy()
                self.frame_widget = None
            if self.dialog_widget is None:
                self.dialog_widget = visualize_phenotype(self,
                                                         self.phenotype,
                                                         QT_DIALOG)
                self.connect(self.dialog_widget,
                             QtCore.SIGNAL('finished(int)'),
                             self._onDestroyed)
            self.update()

        def _onDestroyed(self, x):
            time.sleep(.1)
            print "moo"
            self.dialog_widget.close()
            self.dialog_widget = None

        def center(self):
            screen = QtGui.QDesktopWidget().screenGeometry()
            size =  self.geometry()
            self.move((screen.width()-size.width())/2,
            (screen.height()-size.height())/2)

    app = QtGui.QApplication(sys.argv)

    phenotype = Test(a = 4)
    main = MainWindow(phenotype)
    main.raise_()

    sys.exit(app.exec_())
