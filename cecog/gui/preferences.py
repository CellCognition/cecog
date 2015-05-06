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


from collections import defaultdict
from StringIO import StringIO
from os.path import splitext
import numpy as np


from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSettings

from cecog.util.pattern import Singleton
from cecog import version


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
    __slots__ = ("host", "port", "mapping_str")

    def __init__(self):

        # default values
        self.host = 'http://login-debian7.bioinfo.imp.ac.at:9999'
        self.port = 9999

        self.mapping_str = ("#mac, windows, linux\n"
                            "/Volumes/groups/gerlich, M:, /groups/gerlich\n"
                            "/Volumes/clustertmp, N:, /clustertmp\n"
                            "/Volumes/resources, O:, /resources")

    def saveSettings(self):
        settings = QSettings(version.organisation, version.appname)
        settings.beginGroup('preferences')
        settings.setValue('port', self.port)
        settings.setValue('host', self.host)

        settings.setValue('path_mapping', self.mapping_str)
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

    @property
    def url(self):
        return "%s:%s" %(self.host.text(), self.port.value())

    @property
    def mapping(self):
        return txt2dict(self.mapping_str)

class PreferencesDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kw):
        super(PreferencesDialog, self).__init__(*args, **kw)
        uic.loadUi(splitext(__file__)[0]+'.ui', self)
        apc = AppPreferences()

        self.populateTable(apc.mapping_str)
        self.host.setText(apc.host)
        self.port.setValue(apc.port)

        self.addBtn.clicked.connect(self.addMapping)
        self.deleteBtn.clicked.connect(self.deleteMapping)


    def populateTable(self, mappings):

        table = np.recfromcsv(StringIO(mappings), autostrip=True)
        self.mappings.setHeaderLabels(table.dtype.names)


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
