"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held, Thomas Walter'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ['Browser']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import os, \
       re, \
       numpy, \
       time, \
       shutil, \
       math
from xml.dom import minidom

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.datetimeutils import StopWatch
from pdk.ordereddict import OrderedDict
from pdk.fileutils import safe_mkdirs

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import (exception,
                            information,
                            question,
                            warning,
                            numpy_to_qimage,
                            get_qcolor_hicontrast,
                            qcolor_to_hex,
                            )
from cecog.gui.imageviewer import ImageViewer
from cecog.gui.analyzer import _ProcessorMixin
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore
from cecog.util.util import (hexToRgb,
                             convert_package_path,
                             singleton,
                             )
from cecog.learning.learning import BaseLearner
from cecog.gui.widgets.groupbox import QxtGroupBox
from cecog.gui.module import Module
#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#


class Annotations(object):

    def __init__(self):
        self._annotations = {}
        self._counts = {}

    def add(self, coordinates, class_name, item):
        plate, position, time = coordinates
        ann = self._annotations
        if not plate in ann:
            ann[plate] = {}
        if not position in ann[plate]:
            ann[plate][position] = {}
        if not time in ann[plate][position]:
            ann[plate][position][time] = {}
        if not class_name in ann[plate][position][time]:
            ann[plate][position][time][class_name] = set()
        ann[plate][position][time][class_name].add(item)

        if not class_name in self._counts:
            self._counts[class_name] = 0
        self._counts[class_name] += 1

    def remove(self, coordinates, item):
        plate, position, time = coordinates
        items = self._annotations[plate][position][time]
        for class_name in items:
            if item in items[class_name]:
                items[class_name].remove(item)
                self._counts[class_name] -= 1

    def remove_all(self):
        self._annotations.clear()
        self._counts.clear()

    def rename_class(self, name_old, name_new):
        if name_old != name_new:
            ann = self._annotations
            for plateid in ann:
                for position in ann[plateid]:
                    for time in ann[plateid][position]:
                        ann2 = ann[plateid][position][time]
                        if name_old in ann2:
                            ann2[name_new] = ann2[name_old]
                            del ann2[name_old]

    def remove_class(self, class_name):
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    ann2 = ann[plateid][position][time]
                    if class_name in ann2:
                        del ann2[class_name]
        if class_name in self._counts:
            del self._counts[class_name]

    def iter_items(self, coordinates):
        plate, position, time = coordinates
        try:
            items = self._annotations[plate][position][time]
            for class_name in items:
                for item in items[class_name]:
                    yield (class_name, item)
        except KeyError:
            pass

    def iter_all(self):
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    ann2 = ann[plateid][position][time]
                    for cn in ann2:
                        items = ann2[cn]
                        yield plateid, position, time, cn, items

    def get_class_counts(self):
        return self._counts

    def get_count_for_class(self, class_name):
        return self.get_class_counts().get(class_name, 0)

    def get_class_name(self, coordinates, item):
        plate, position, time = coordinates
        items = self._annotations[plate][position][time]
        for class_name in items:
            if item in items[class_name]:
                return class_name
        return None

    def rebuild_class_counts(self):
        self._counts.clear()
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    for cn in ann[plateid][position][time]:
                        if cn not in self._counts:
                            self._counts[cn] = 0
                        items = ann[plateid][position][time][cn]
                        self._counts[cn] += len(items)

    def import_from_xml(self, path, labels_to_names):
        pattern = re.compile('(.*__)?P(?P<position>.+?)__T(?P<time>\d+).*?')
        ann = self._annotations
        ann.clear()
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            prefix, suffix = os.path.splitext(filename)
            match = pattern.match(prefix)
            if (os.path.isfile(file_path) and suffix.lower() == '.xml' and
                not match is None):

                plateid = ''
                position = match.group('position')
                time = int(match.group('time'))

                if not plateid in ann:
                    ann[plateid] = {}
                if not position in ann[plateid]:
                    ann[plateid][position] = {}

                doc = minidom.parse(file_path)

                for marker_type in doc.getElementsByTagName('Marker_Type'):
                    class_label = int(marker_type.getElementsByTagName('Type')[0].childNodes[0].data.strip())
                    class_name = labels_to_names[class_label]

                    for marker in marker_type.getElementsByTagName('Marker'):
                        x = int(marker.getElementsByTagName('MarkerX')[0].childNodes[0].data)
                        y = int(marker.getElementsByTagName('MarkerY')[0].childNodes[0].data)
                        t = int(marker.getElementsByTagName('MarkerZ')[0].childNodes[0].data)

                        time_ref = time + t - 1
                        if not time_ref in ann[plateid][position]:
                            ann[plateid][position][time_ref] = {}
                        ann2 = ann[plateid][position][time_ref]
                        if not class_name in ann2:
                            ann2[class_name] = set()
                        ann2[class_name].add((x, y))
        self.rebuild_class_counts()

    def export_to_xml(self, path, min_time, names_to_labels):
        impl = minidom.getDOMImplementation()
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:

                ann2 = ann[plateid][position]
                bycn = OrderedDict()
                for time in ann2:
                    for cn in ann2[time]:
                        if not cn in bycn:
                            bycn[cn] = OrderedDict()
                        bycn[cn][time] = ann2[time][cn]

                doc = impl.createDocument(None, 'CellCounter_Marker_File', None)
                top = doc.documentElement
                element = doc.createElement('Marker_Data')
                top.appendChild(element)

                for cn in bycn:
                    element2 = doc.createElement('Marker_Type')
                    element.appendChild(element2)
                    element3 = doc.createElement('Type')
                    class_label = names_to_labels[cn]
                    text = doc.createTextNode(str(class_label))
                    element3.appendChild(text)
                    element2.appendChild(element3)
                    for time in bycn[cn]:
                        for item in bycn[cn][time]:
                            element3 = doc.createElement('Marker')

                            element4 = doc.createElement('MarkerX')
                            text = doc.createTextNode(str(item[0]))
                            element4.appendChild(text)
                            element3.appendChild(element4)
                            element4 = doc.createElement('MarkerY')
                            text = doc.createTextNode(str(item[1]))
                            element4.appendChild(text)
                            element3.appendChild(element4)
                            element4 = doc.createElement('MarkerZ')
                            text = doc.createTextNode(str(time))
                            element4.appendChild(text)
                            element3.appendChild(element4)

                            element2.appendChild(element3)

                filename = 'P%s__T%05d.xml' % (position, min_time)
                f = file(os.path.join(path, filename), 'w')
                doc.writexml(f, indent='  ', addindent='  ', encoding='utf8',
                             newl='\n')
                f.close()


class Annotation(Module):

    NAME = 'Annotation'

    COLUMN_CLASS_NAME = 0
    COLUMN_CLASS_LABEL = 1
    COLUMN_CLASS_COLOR = 2
    COLUMN_CLASS_COUNT = 3

    def __init__(self, parent, browser, settings, imagecontainer):
        Module.__init__(self, parent, browser)

        self._current_class = None
        self._detect_objects = False
        self._current_scene_items = set()

        self._settings = settings
        self._imagecontainer = imagecontainer

        self._annotations = Annotations()
        self._object_items = {}
        self._plateid = ''
        #self._channel = ''

        splitter = QSplitter(Qt.Horizontal, self)

#        grp_box = QxtGroupBox('Annotation2', frame_side)
#        grp_box.setFlat(True)
#        grp_box.setMinimumHeight(30)
#        layout = QBoxLayout(QBoxLayout.TopToBottom, grp_box)
#        layout.setContentsMargins(2,2,2,2)
#
#        ann_table = QTableWidget(grp_box)
#        ann_table.setEditTriggers(QTableWidget.NoEditTriggers)
#        ann_table.setSelectionMode(QTableWidget.SingleSelection)
#        ann_table.setSelectionBehavior(QTableWidget.SelectRows)
#        ann_table.setSortingEnabled(True)
#        ann_table.setColumnCount(4)
#        ann_table.setHorizontalHeaderLabels(['Plate', 'Position', 'Time',
#                                             'Samples',
#                                             ])
#        ann_table.resizeColumnsToContents()
#        ann_table.currentItemChanged.connect(self._on_class_changed)
#        layout.addWidget(ann_table)
#        self._ann_table = ann_table
#        frame_side.layout().addWidget(grp_box)
#        frame_side.layout().addSpacing(1)

        grp_box = QxtGroupBox('Annotation', splitter)
        grp_box.setFlat(True)

        layout = QBoxLayout(QBoxLayout.TopToBottom, grp_box)
        layout.setContentsMargins(2,2,2,2)

        class_table = QTableWidget(grp_box)
        class_table.setEditTriggers(QTableWidget.NoEditTriggers)
        class_table.setSelectionMode(QTableWidget.SingleSelection)
        class_table.setSelectionBehavior(QTableWidget.SelectRows)
        #class_table.setSortingEnabled(True)
        class_table.setColumnCount(4)
        class_table.setHorizontalHeaderLabels(['Name', 'Label', 'Color',
                                               'Samples',
                                               ])
        class_table.resizeColumnsToContents()
        class_table.currentItemChanged.connect(self._on_class_changed)
        layout.addWidget(class_table)
        self._class_table = class_table

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        self._class_sbox = QSpinBox(frame2)
        self._class_color_btn = QToolButton(frame2)
        self._class_color_btn.clicked.connect(self._on_class_color)
        self._class_color = None
        self._class_sbox.setRange(0, 1000)
        self._class_text = QLineEdit(frame2)
        layout2.addWidget(self._class_color_btn)
        layout2.addWidget(self._class_sbox)
        layout2.addWidget(self._class_text)
        layout.addWidget(frame2)

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        btn = QPushButton('Apply', frame2)
        btn.clicked.connect(self._on_class_apply)
        layout2.addWidget(btn)
        btn = QPushButton('Add', frame2)
        btn.clicked.connect(self._on_class_add)
        layout2.addWidget(btn)
        btn = QPushButton('Remove', frame2)
        btn.clicked.connect(self._on_class_remove)
        layout2.addWidget(btn)
        layout.addWidget(frame2)

        splitter.addWidget(grp_box)
        #layout_side.addWidget(grp_box)
        #layout_side.addSpacing(1)

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.addWidget(splitter)

        box = QCheckBox('Detect objects', self)
        box.setCheckState(Qt.Checked if self._detect_objects else Qt.Unchecked)
        layout.addWidget(box)
        #frame_side.layout().addSpacerItem(QSpacerItem(1,1))

        box.clicked.connect(self._on_detect_box)
        self._learner = self._init_new_classifier()

    def _on_class_color(self):
        '''
        Open the color dialog for a class
        '''
        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.ShowAlphaChannel)
        if not self._class_color is None:
            dlg.setCurrentColor(self._class_color)
        if dlg.exec_():
            col = dlg.currentColor()
            # FIXME: assignment and update should be made upon "apply"
            self._class_color_btn.setStyleSheet('background-color: rgb(%d, %d, %d)'\
                                                % (col.red(), col.green(),
                                                   col.blue()))
            self._class_color = col

    def _find_items_in_class_table(self, value, column, match=Qt.MatchExactly):
        items = self._class_table.findItems(value, match)
        return [item for item in items if item.column() == column]

    def _on_class_apply(self):
        '''
        Apply class changes
        '''
        learner = self._learner

        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()
        class_name = self._current_class

        if not class_name is None:
            class_label = learner.dctClassLabels[class_name]

            class_labels = set(learner.lstClassLabels)
            class_labels.remove(class_label)
            class_names = set(learner.lstClassNames)
            class_names.remove(class_name)

            if len(class_name_new) == 0:
                warning(self, "Invalid class name",
                        info="The class name must not be empty!")
            elif (not class_name_new in class_names and
                  not class_label_new in class_labels):

                del learner.dctClassNames[class_label]
                del learner.dctClassLabels[class_name]
                del learner.dctHexColors[class_name]

                item = self._find_items_in_class_table(class_name,
                                                       self.COLUMN_CLASS_NAME)[0]

                learner.dctClassNames[class_label_new] = class_name_new
                learner.dctClassLabels[class_name_new] = class_label_new
                learner.dctHexColors[class_name_new] = \
                    qcolor_to_hex(self._class_color)

                item.setText(class_name_new)
                item2 = self._class_table.item(item.row(),
                                               self.COLUMN_CLASS_LABEL)
                item2.setText(str(class_label_new))
                item2 = self._class_table.item(item.row(),
                                               self.COLUMN_CLASS_COLOR)
                item2.setBackground(QBrush(self._class_color))

                col = get_qcolor_hicontrast(self._class_color)
                self._class_table.setStyleSheet("selection-background-color: %s;"\
                                                "selection-color: %s;" %\
                                                (qcolor_to_hex(self._class_color),
                                                 qcolor_to_hex(col)))
                self._class_table.resizeRowsToContents()
                self._class_table.resizeColumnsToContents()
                self._class_table.scrollToItem(item)

                self._annotations.rename_class(class_name, class_name_new)
                self._current_class = class_name_new
                self._activate_objects_for_image(False)
                self._activate_objects_for_image(True)
            else:
                warning(self, "Class names and labels must be unique!",
                        info="Class name '%s' or label '%s' already used." %\
                             (class_name_new, class_label_new))

    def _on_class_add(self):
        '''
        Add a new class
        '''
        learner = self._learner
        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()

        class_labels = set(learner.lstClassLabels)
        class_names = set(learner.lstClassNames)
        if len(class_name_new) == 0:
            warning(self, "Invalid class name",
                    info="The class name must not be empty!")
        elif (not class_name_new in class_names and
              not class_label_new in class_labels):
            self._current_class = class_name_new

            learner.dctClassNames[class_label_new] = class_name_new
            learner.dctClassLabels[class_name_new] = class_label_new
            learner.dctHexColors[class_name_new] = \
                qcolor_to_hex(self._class_color)

            row = self._class_table.rowCount()
            self._class_table.insertRow(row)
            self._class_table.setItem(row, self.COLUMN_CLASS_NAME,
                                      QTableWidgetItem(class_name_new))
            self._class_table.setItem(row, self.COLUMN_CLASS_LABEL,
                                      QTableWidgetItem(str(class_label_new)))
            self._class_table.setItem(row, self.COLUMN_CLASS_COUNT,
                                      QTableWidgetItem('0'))
            item = QTableWidgetItem()
            item.setBackground(QBrush(self._class_color))
            self._class_table.setItem(row, self.COLUMN_CLASS_COLOR, item)
            self._class_table.resizeRowsToContents()
            self._class_table.resizeColumnsToContents()
            self._class_table.setCurrentItem(item)
        else:
            warning(self, "Class names and labels must be unique!",
                    info="Class name '%s' or label '%s' already used." %\
                         (class_name_new, class_label_new))

    def _on_class_remove(self):
        '''
        Remove a class and all its annotations
        '''
        class_name = self._current_class
        if question(self, "Do you really want to remove class '%s'?" % \
                    class_name,
                    info="All %d annotations will be lost." % \
                    self._annotations.get_count_for_class(class_name)):

            self._activate_objects_for_image(False)
            learner = self._learner
            class_label = learner.dctClassLabels[class_name]
            del learner.dctClassLabels[class_name]
            del learner.dctClassNames[class_label]
            del learner.dctHexColors[class_name]

            item = self._find_items_in_class_table(class_name,
                                                   self.COLUMN_CLASS_NAME)[0]
            row = item.row()
            self._class_table.removeRow(row)
            self._annotations.remove_class(class_name)
            self._activate_objects_for_image(True, clear=True)

            row_count = self._class_table.rowCount()
            if row_count > 0:
                row = row if row < row_count else row_count-1
                item = self._class_table.item(row, self.COLUMN_CLASS_NAME)
                self._class_table.setCurrentItem(item)

    def _init_new_classifier(self):
        learner = BaseLearner()
        self._current_class = None
        self._class_sbox.setValue(1)
        self._class_text.setText('class1')
        self._class_color = QColor('red')
        self._class_color_btn.setStyleSheet("background-color: %s;" %
                                            qcolor_to_hex(self._class_color))
        class_table = self._class_table
        class_table.clearContents()
        class_table.setRowCount(0)
        if self._detect_objects:
            self._activate_objects_for_image(False, clear=True)
        self._annotations.remove_all()
        return learner

    def _on_new_classifier(self):
        if question(self, 'New classifier',
                    'Are you sure to setup a new classifer? All annotations '
                    'will be lost.'):
            self._learner = self._init_new_classifier()

    def _on_open_classifier(self):

        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        path = self._learner.get_env_path()
        dialog.setDirectory(os.path.abspath(path))
        if dialog.exec_():
            path = str(dialog.selectedFiles()[0])
            learner = self._load_classifier(path)
            if not learner is None:
                self._learner = learner
                class_table = self._class_table
                class_table.clearContents()
                class_table.setRowCount(len(self._learner.dctClassLabels))
                select_item = None
                for idx, class_name in enumerate(self._learner.lstClassNames):
                    samples = 0
                    class_label = self._learner.dctClassLabels[class_name]
                    item = QTableWidgetItem(class_name)
                    class_table.setItem(idx, self.COLUMN_CLASS_NAME, item)
                    if select_item is None:
                        select_item = item
                    class_table.setItem(idx, self.COLUMN_CLASS_LABEL,
                                        QTableWidgetItem(str(class_label)))
                    class_table.setItem(idx, self.COLUMN_CLASS_COUNT,
                                        QTableWidgetItem(str(samples)))
                    item = QTableWidgetItem(' ')
                    item.setBackground(
                        QBrush(QColor(self._learner.dctHexColors[class_name])))
                    class_table.setItem(idx, self.COLUMN_CLASS_COLOR, item)
                class_table.resizeColumnsToContents()
                class_table.resizeRowsToContents()

                path2 = learner.getPath(learner.ANNOTATIONS)
                try:
                    self._annotations.import_from_xml(path2,
                                                      learner.dctClassNames)
                except:
                    exception(self, "Problems loading annotation data...")
                    self._learner = self._init_new_classifier()
                else:
                    if self._detect_objects:
                        self._activate_objects_for_image(False, clear=True)
                        self._activate_objects_for_image(True)
                    self._update_class_table()
                    if class_table.rowCount() > 0:
                        class_table.setCurrentCell(0, self.COLUMN_CLASS_NAME)
                    else:
                        self._current_class = None

#                    iter_all = self._annotations.iter_all(self._channel)
#                    items = [(pi,p,t,cn,len(it)) for pi,p,t,cn,it in iter_all]
#                    ann_table = self._ann_table
#                    ann_table.clearContents()
#                    ann_table.setRowCount(len(items))
#                    #ann_table.setM
#                    for idx, (pi,p,t,cn,cnt) in enumerate(items):
#                        print idx, pi,p,t,cn,cnt
#                        ann_table.setItem(idx, 0, QTableWidgetItem(str(pi)))
#                        ann_table.setItem(idx, 1, QTableWidgetItem(str(p)))
#                        ann_table.setItem(idx, 2, QTableWidgetItem(str(t)))
#                        ann_table.setItem(idx, 3, QTableWidgetItem(str(cnt)))
#                    ann_table.resizeColumnsToContents()
#                    ann_table.resizeRowsToContents()

                    information(self, "Classifier successfully loaded",
                                "Class definitions and annotations "
                                "successfully loaded from '%s'." % path)

    def _on_saveas_classifier(self):
        min_time = self._meta_data.times[0]

        learner = self._learner
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        path = learner.get_env_path()
        dialog.setDirectory(os.path.abspath(path))
        dialog.setConfirmOverwrite(True)
        if dialog.exec_():
            path = str(dialog.selectedFiles()[0])
            if self._save_classifier(path):
                try:
                    path2 = learner.getPath(learner.ANNOTATIONS)
                    filenames = os.listdir(path2)
                    filenames = [os.path.join(path2, f) for f in filenames
                                 if os.path.isfile(os.path.join(path2, f)) and
                                 os.path.splitext(f)[1].lower() == '.xml']
                    fmt = time.strftime('_backup__%Y%m%d_%H%M%S')
                    path_backup = os.path.join(path2, fmt)
                    safe_mkdirs(path_backup)
                    for filename in filenames:
                        shutil.copy2(filename, path_backup)
                        os.remove(filename)
                    self._annotations.export_to_xml(path2, min_time,
                                                    learner.dctClassLabels)
                except:
                    exception(self, "Problems saving annotation data...")
                else:
                    information(self, "Classifier successfully saved",
                                "Class definitions and annotations "
                                "successfully saved to '%s'." % path)

    def _activate_objects_for_image(self, state=True, clear=False):
        if clear:
            self._object_items.clear()
        coordinates = self._browser.get_coordinates()
        for class_name, tpl in self._annotations.iter_items(coordinates):
            point = QPointF(*tpl)
            item = self._browser.image_viewer.get_object_item(point)
            if not item is None:
                if not item in self._object_items:
                    self._object_items[item] = point
                self._activate_object(item, class_name, state=state)

    def _update_class_table(self):
        counts = self._annotations.get_class_counts()
        for class_name in self._learner.lstClassNames:
            if class_name in counts:
                items = self._find_items_in_class_table(class_name,
                                                        self.COLUMN_CLASS_NAME)
                item = self._class_table.item(items[0].row(),
                                              self.COLUMN_CLASS_COUNT)
                item.setText(str(counts[class_name]))
        #self._class_table.update()

    def _on_new_point(self, point, button, modifier):
        item = self._browser.image_viewer.get_object_item(point)
        print(item,point,item in self._object_items)
        if button == Qt.LeftButton and not item is None:

            coordinates = self._browser.get_coordinates()
            old_class = None
            # remove the item if already present
            if item in self._object_items:
                point2 = self._object_items[item]
                tpl = (int(point2.x()), int(point2.y()))

                old_class = \
                    self._annotations.get_class_name(coordinates, tpl)
                self._annotations.remove(coordinates, tpl)
                del self._object_items[item]
                self._activate_object(item, self._current_class, False)

            # mark a new item only if the shift-key is not pressed, a class
            # is currently active and the class name is different
            if (modifier != Qt.ShiftModifier and
                not self._current_class is None and
                old_class != self._current_class):
                tpl = (int(point.x()), int(point.y()))
                self._annotations.add(coordinates,
                                      self._current_class, tpl)
                self._object_items[item] = point
                self._activate_object(item, self._current_class, True)
            self._update_class_table()


    def _on_dbl_clk(self, point):
        items = self.image_viewer.items(point)
        print(items)

    def _activate_object(self, item, class_name, state=True):
        pen = item.pen()
        color = \
            QColor(*hexToRgb(self._learner.dctHexColors[class_name]))
        pen.setColor(color if state else Qt.white)
        item.setPen(pen)

        if state:
            rect = item.boundingRect()
            label = self._learner.dctClassLabels[class_name]
            item2 = QGraphicsSimpleTextItem(str(label), item)
            item2.setPos(rect.x()+rect.width()/2., rect.y()+rect.height()/2)
            item2.setPen(QPen(color))
            item2.setBrush(QBrush(color))
            item2.show()
        else:
            scene = item.scene()
            for item2 in item.childItems():
                scene.removeItem(item2)
        obj_id = item.data(0).toInt()[0]
        return obj_id

    def _on_class_changed(self, current, previous):
        print self._class_table.rowCount(), current
        if not current is None:
            item = self._class_table.item(current.row(),
                                          self.COLUMN_CLASS_NAME)
            self._current_class = str(item.text())
            print self._current_class, current.row()
            hex_col = self._learner.dctHexColors[self._current_class]
            col = get_qcolor_hicontrast(QColor(hex_col))
            self._class_table.setStyleSheet("selection-background-color: %s;"\
                                            "selection-color: %s;" %\
                                            (hex_col, qcolor_to_hex(col)))
            self._class_table.scrollToItem(item)
            self._class_text.setText(self._current_class)
            class_label = self._learner.dctClassLabels[self._current_class]
            self._class_sbox.setValue(class_label)
            self._class_color_btn.setStyleSheet("background-color: %s;" % hex_col)
            self._class_color = QColor(hex_col)
        else:
            self._current_class = None

    def _on_detect_box(self, state):
        if not state:
            self._browser.image_viewer.remove_objects()
            self._object_items.clear()
        self._detect_objects = state
        self._browser._process_image()

    def _on_shortcut_class_selected(self, class_label):
        items = self._find_items_in_class_table(str(class_label),
                                                self.COLUMN_CLASS_LABEL)
        if len(items) == 1:
            self._class_table.setCurrentItem(items[0])

    def _load_classifier(self, path):
        learner = None
        try:
            learner = BaseLearner(strEnvPath=path)
        except:
            exception(self, 'Error on loading classifier')
        else:
            result = learner.check()
            #if result['has_arff']:
            #    self._learner.importFromArff()

            if result['has_definition']:
                learner.loadDefinition()
        return learner

    def _save_classifier(self, path):
        learner = self._learner
        success = True
        try:
            learner.set_env_path(path)
            learner.initEnv()
            learner.saveDefinition()
        except:
            exception(self, 'Error on saving classifier')
            success = False
        return success

    def set_coords(self):
        self._activate_objects_for_image(clear=True)
        self._update_class_table()

    def showEvent(self, event):
        QFrame.showEvent(self, event)
        self._browser.image_viewer.image_mouse_pressed.connect(self._on_new_point)

    def hideEvent(self, event):
        QFrame.hideEvent(self, event)
        self._browser.image_viewer.image_mouse_pressed.disconnect(self._on_new_point)


