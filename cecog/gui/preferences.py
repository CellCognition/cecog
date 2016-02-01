"""
preferences.py

Setup dialog for application preferences.

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ("PreferencesDialog", "AppPreferences")


import sys
import ntpath
import posixpath

from collections import defaultdict
from StringIO import StringIO
from os.path import splitext
import numpy as np

from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSettings

from .loadui import loadUI
from cecog.util.pattern import Singleton
from cecog import version
from cecog import css


def txt2dict(txt):
    """Convert a csv string into a dict.

    example:
    {source_os: {share_src: {target_os: share_target, }},}
    """

    table = np.recfromcsv(StringIO(txt), autostrip=True, delimiter=",")

    cnames = table.dtype.names
    ncols = len(cnames)
    nrows = table.shape[0]

    table_ = dict()

    for ci in xrange(ncols):
        table2 = defaultdict(dict)
        for ri in xrange(nrows):
            for i in set(range(ncols)).difference([ci]):
                table2[table[ri][ci]].update({cnames[i]: table[ri][i]})
        table_[cnames[ci]] = table2
    return table_


class AppPreferences(object):
    """Singleton class to access applicaton preferences."""

    __metaclass__ = Singleton
    __slots__ = ("host", "port", "mapping_str", "target_platform",
                 "batch_size", "cluster_support", "stylesheet",
                 'available_stylesheets')

    def __init__(self):

        # default values
        self.host = 'http://cecog-gerlich.imp.univie.ac.at'
        self.port = 9999

        self.mapping_str = ("#darwin, win32, linux2\n"
                            "/Volumes/groups/gerlich, M:, /groups/gerlich\n"
                            "/Volumes/clustertmp/gerlich, O:, /clustertmp/gerlich\n"
                            "/Volumes/resources, N:, /resources")
        self.target_platform = "linux2"
        self.batch_size = 1
        self.cluster_support = True
        self.stylesheet = 'classic'

        self.restoreSettings()


    def saveSettings(self):
        settings = QSettings(version.organisation, version.appname)
        settings.beginGroup('preferences')
        settings.setValue('port', self.port)
        settings.setValue('host', self.host)

        settings.setValue('path_mapping', self.mapping_str)
        settings.setValue('target_platform', self.target_platform)
        settings.setValue('batch_size', self.batch_size)
        settings.setValue('cluster_support', self.cluster_support)
        settings.setValue('stylesheet', self.stylesheet)
        settings.endGroup()

    def restoreSettings(self):

        settings = QSettings(version.organisation, version.appname)
        settings.beginGroup('preferences')

        if settings.contains('host'):
            self.host = settings.value('host', type=str)

        if settings.contains('port'):
            self.port = settings.value('port', type=int)

        if settings.contains('path_mapping'):
            self.mapping_str = settings.value('path_mapping')

        if settings.contains('target_platform'):
            self.target_platform = settings.value('target_platform')

        if settings.contains('batch_size'):
            self.batch_size = settings.value('batch_size', type=int)

        if settings.contains('cluster_support'):
            self.cluster_support = settings.value('cluster_support', type=bool)

        if settings.contains('stylesheet'):
            self.stylesheet = settings.value('stylesheet', type=str)

        settings.endGroup()

    @property
    def url(self):
        return "%s:%s" %(self.host, self.port)

    @property
    def mapping(self):
        return txt2dict(self.mapping_str)

    def map2platform(self, path, target_platform=None):
        """Map paths of from the source i.e. current platform to the
        target platform. Supported plaforms are linux, win32 and darwin.

        The method does not perform any sanity checks wether the path exists
        on the current or target platform. It simply replaces the substrings of
        the current path, defined in mapping table.

        The new path is normalized using the xx.normcase method (x is replaced
        either by ntpath or posixpath).
        """

        if target_platform is None:
            target_platform = self.target_platform

        if target_platform not in ("linux", "linux2", "darwin", "win32"):
            raise RuntimeError("Target platform not supported!")

        platform = sys.platform
        if platform == target_platform:
            return path

        mapping = AppPreferences().mapping

        path_mapped = None
        for k, v in mapping[platform].iteritems():
            if path.find(k) == 0:
                path_mapped = path.replace(k, v[target_platform])
                break

        if path_mapped is None:
            pass
        elif target_platform.startswith("win"):
            path_mapped = ntpath.normcase(path_mapped)
        # OSX 10.X and linux
        else:
            path_mapped = posixpath.normcase(path_mapped)
            path_mapped = path_mapped.replace(ntpath.sep, posixpath.sep)
        return path_mapped



class PreferencesDialog(QtWidgets.QDialog):

    _osnames = {"darwin": "Mapple",
                "linux2": "Linux",
                "win32": "DOS"}
    _iosnames = dict([(v, k) for k, v in _osnames.iteritems()])

    def __init__(self, *args, **kw):
        super(PreferencesDialog, self).__init__(*args, **kw)
        loadUI(splitext(__file__)[0]+'.ui', self)
        apc = AppPreferences()

        self.populateTable(apc.mapping_str)
        self.host.setText(apc.host)
        self.port.setValue(apc.port)

        self.addBtn.clicked.connect(self.addMapping)
        self.deleteBtn.clicked.connect(self.deleteMapping)

        for i in xrange(self.mappings.columnCount()):
            self.mappings.resizeColumnToContents(i)

        self.target_platform.clear()
        self.target_platform.addItems(self._iosnames.keys())
        self.target_platform.setCurrentIndex(
            self.target_platform.findText(self._osnames[apc.target_platform]))

        self.batch_size.setValue(apc.batch_size)
        self.cluster_support.setChecked(apc.cluster_support)

        self.style_select.addItems(css.StyleSheets.keys())
        self.style_select.setCurrentIndex(
            self.style_select.findText(apc.stylesheet))

        self.style_select.currentIndexChanged[str].connect(
            self.setGlobalStylesheet)

    def setGlobalStylesheet(self, stylesheet):
        stylesheet = css.loadStyle(stylesheet)
        self.parent().updateStyleSheet(stylesheet)

    def populateTable(self, mappings):

        table = np.recfromcsv(StringIO(mappings), autostrip=True)
        self.mappings.setHeaderLabels(
            [self._osnames[n] for n in table.dtype.names])

        for i, line in enumerate(table):
            item = QtWidgets.QTreeWidgetItem(line)
            item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEditable|
                          Qt.ItemIsEnabled)
            self.mappings.addTopLevelItem(item)

    def mappingTable(self):
        return txt2dict(self.mapping2txt())

    def mapping2txt(self):

        names = [self.mappings.headerItem().data(i, Qt.DisplayRole)
                 for i in xrange(self.mappings.columnCount())]
        names = [self._iosnames[n] for n in names]

        txt = "#" + ",".join(names)
        for i in xrange(self.mappings.topLevelItemCount()):
            line = [self.mappings.topLevelItem(i).text(j)
                    for j in xrange(self.mappings.columnCount())]
            txt = "%s\n%s" %(txt, ",".join(line))
        return txt

    def addMapping(self):
        item = QtWidgets.QTreeWidgetItem(["--", "--", "--"])
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEditable|
                      Qt.ItemIsEnabled)
        self.mappings.addTopLevelItem(item)

    def deleteMapping(self):
        for item in self.mappings.selectedItems():
            self.mappings.takeTopLevelItem(
                self.mappings.indexOfTopLevelItem(item))

    def accept(self):

        appcfg = AppPreferences()
        appcfg.host =  self.host.text()
        appcfg.port = self.port.value()
        appcfg.mapping_str = self.mapping2txt()
        appcfg.target_platform = \
            self._iosnames[self.target_platform.currentText()]
        appcfg.batch_size = self.batch_size.value()
        appcfg.cluster_support = self.cluster_support.isChecked()
        appcfg.stylesheet = self.style_select.currentText()
        appcfg.saveSettings()

        super(PreferencesDialog, self).accept()



if __name__ == "__main__":
    import sys
    sys.path.append("../../")
    from PyQt5.QtWidgets import QApplication
    import cecog.cecog_rc



    app = QApplication(sys.argv)
    pd = PreferencesDialog()
    pd.show()
    app.exec_()
