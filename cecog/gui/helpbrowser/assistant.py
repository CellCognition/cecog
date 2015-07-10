"""
assistant.py

The Qt-Project recommends to use the Qt-Assistant for online documentation.
This is a lightweight reimplemntation of the assistant in python to embbed
a help browser into a application bundle (i.e using py2exe or py2app).
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2015'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("AtAssistant", )


from os.path import join, dirname, isfile, basename

from PyQt5 import uic
from PyQt5 import QtGui
from PyQt5 import QtHelp
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextDocument

from cecog import version
from cecog.gui.util import loadUI


class AtLineEdit(QtWidgets.QLineEdit):
    """QLineEdit with clear button, which appears when user enters text."""

    def __init__(self, *args, **kw):
        super(AtLineEdit, self).__init__(*args, **kw)

        self._button = QtWidgets.QToolButton(self)
        self._button.setIcon(QtGui.QIcon(":/oxygen/clear.png"))
        self._button.setStyleSheet('border: 0px; padding: 0px;')
        self._button.setCursor(QtCore.Qt.ArrowCursor)

        width = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        size = self._button.sizeHint()

        self.setStyleSheet('QLineEdit {padding-right: %dpx; }'
                           %(size.width() + width + 1))
        self.setMinimumSize(max(self.minimumSizeHint().width(),
                                size.width() + width*2 + 2),
                            max(self.minimumSizeHint().height(),
                                size.height() + width*2 + 2))

        self.textChanged.connect(self.changed)
        self._button.clicked.connect(self.clear)
        self._button.hide()

    def resizeEvent(self, event):
        size = self._button.sizeHint()
        width = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        self._button.move(self.rect().right() - width - size.width(),
                         (self.rect().bottom() - size.height() + 1)/2)
        super(AtLineEdit, self).resizeEvent(event)

    def changed(self, text):
        """Shows image if text is not empty."""
        if text:
            self._button.show()
        else:
            self._button.hide()


class AtHelpBrowser(QtWidgets.QTextBrowser):

    QTHELP = 'qthelp'
    HTTP = 'http'

    def __init__(self, *args, **kw):
        super(AtHelpBrowser, self).__init__(*args, **kw)
        self.helpengine = None

    def setSource(self, url):

        if url.scheme() == self.HTTP:
            QtGui.QDesktopServices.openUrl(url)
        else:
            super(AtHelpBrowser, self).setSource(url)

    def setHelpEngine(self, helpengine):
        self.helpengine = helpengine

    def loadResource(self, type_, url):

        if url.scheme() == self.QTHELP:
            return self.helpengine.fileData(url);
        else:
            return super(AtHelpBrowser, self).loadResource(type_, url);

    def close(self):
        # prevents a segfault on c++ side
        self.helpengine = None


class AtAssistant(QtWidgets.QMainWindow):

    Manual = "manual.qhc"

    def __init__(self, qhcfile, *args, **kw):
        self._kwmap = dict()

        if not isfile(qhcfile):
            raise IOError("%s file not found" %(qhcfile))

        super(AtAssistant, self).__init__(*args, **kw)
        loadUI(join(dirname(__file__), "assistant.ui"), self)
        self.toolBar.setObjectName('Navigation Toolbar')

        self.hengine = QtHelp.QHelpEngine(qhcfile)
        self.hengine.setupData()
        self.hengine.registerDocumentation(qhcfile.replace('.qhc', '.qch'))

        self.hengine.searchEngine().reindexDocumentation()
        self.hbrowser = AtHelpBrowser()
        self.hbrowser.setHelpEngine(self.hengine)
        self.setupToolBar()
        self.setCentralWidget(self.hbrowser)
        self.hengine.contentWidget().linkActivated.connect(
           self.hbrowser.setSource)

        self.queries  = self.hengine.searchEngine().queryWidget()
        self.results = self.hengine.searchEngine().resultWidget()
        self.index = self.hengine.indexWidget()
        self.contents = self.hengine.contentWidget()

        self.tabifyDockWidget(self.contentDock, self.indexDock)
        self.tabifyDockWidget(self.contentDock, self.searchDock)
        self.searchDock.hide()

        # search dock (hidden)
        search = QtWidgets.QFrame(self)
        vbox = QtWidgets.QVBoxLayout(search)
        vbox.setContentsMargins(3, 3, 3, 3)
        vbox.addWidget(self.queries)
        vbox.addWidget(self.results)
        self.results.requestShowLink.connect(self.hbrowser.setSource)
        self.index.linkActivated.connect(self.hbrowser.setSource)
        self.queries.search.connect(self.search)

        # index dock
        index = QtWidgets.QFrame(self)
        filterEdit = AtLineEdit(self)
        vbox = QtWidgets.QVBoxLayout(index)
        vbox.setContentsMargins(3, 3, 3, 3)
        vbox.addWidget(QtWidgets.QLabel("Look for:"))
        vbox.addWidget(filterEdit)
        vbox.addWidget(self.index)
        filterEdit.textChanged.connect(self.filter)

        self.searchDock.setWidget(search)
        self.contentDock.setWidget(self.contents)
        self.indexDock.setWidget(index)

        self._restoreSettings()
        self.indexDock.show()
        self.contentDock.show()
        self._genKeywordMap()

    def setupToolBar(self):

        btn = QtWidgets.QToolButton(self.toolBar)
        btn.setIcon(QtGui.QIcon(":backward.png"))
        btn.setToolTip("backward")
        self.toolBar.addWidget(btn)
        btn.clicked.connect(self.hbrowser.backward)

        btn = QtWidgets.QToolButton(self.toolBar)
        btn.setIcon(QtGui.QIcon(":forward.png"))
        btn.setToolTip("forward")
        self.toolBar.addWidget(btn)
        btn.clicked.connect(self.hbrowser.forward)

        btn = QtWidgets.QToolButton(self.toolBar)
        btn.setIcon(QtGui.QIcon(":reload.png"))
        btn.setToolTip("reload")
        self.toolBar.addWidget(btn)
        btn.clicked.connect(self.hbrowser.reload)

        btn = QtWidgets.QToolButton(self.toolBar)
        btn.setIcon(QtGui.QIcon(":home.png"))
        btn.setToolTip("home")
        self.toolBar.addWidget(btn)
        btn.clicked.connect(self.hbrowser.home)

    def waitForIndex(self):
        for i in xrange(50):
            self.thread().msleep(100)
            if not self.hengine.indexModel().isCreatingIndex():
                break

    def show(self, keyword=None):
        super(AtAssistant, self).show()
        if keyword is not None:
            self.openKeyword(keyword)

    def _genKeywordMap(self):
        """Map html anchors to human readable keywords for index search"""

        model = self.hengine.indexModel()

        for i in xrange(model.rowCount()):
            keyword = model.data(model.index(i), 0)
            link = model.linksForKeyword(keyword).values()[0]
            self._kwmap[self._keywordFromUrl(link)] = keyword

    def _keywordFromUrl(self, url):
        print url
        url = url.toString()
        if '#' in url:
            return url.split('#')[1]
        else:
            return basename(url)

    def openKeyword(self, keyword):
        self.waitForIndex()

        if not self._kwmap:
            self._genKeywordMap()

        if self._kwmap.has_key(keyword):
            keyword = self._kwmap[keyword]

        links = self.hengine.indexModel().linksForKeyword(keyword)
        if links:
            self.hbrowser.setSource(links.values()[0])
        else:
            QtWidgets.QMessageBox.warning(
                self, 'Warning', 'No help for keyword "%s"' %keyword)

    def closeEvent(self, event):
        self._saveSettings()

    def search(self):
        queries = self.queries.query()
        self.hengine.searchEngine().search(queries)

    def filter(self, txt):
        self.hengine.indexModel().filter(txt)

    def _saveSettings(self):
        settings = QtCore.QSettings(version.organisation, version.appname)
        settings.beginGroup('HelpBrowser')
        settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())
        settings.endGroup()

    def _restoreSettings(self):
        settings = QtCore.QSettings(version.organisation, version.appname)
        settings.beginGroup('HelpBrowser')

        if settings.contains('geometry'):
            geometry = settings.value('geometry')
            self.restoreGeometry(geometry)

        if settings.contains('state'):
            state = settings.value('state')
            self.restoreState(state)

        settings.endGroup()

    def close(self):
        self.hbrowser.close()
        # don't use del to prevent AttributeError
        self.hengine = None
