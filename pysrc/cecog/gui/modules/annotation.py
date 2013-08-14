"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
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

import os
import re
import numpy
import time
import shutil
import math
import datetime

import h5py

from xml.dom import minidom

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.datetimeutils import StopWatch
from pdk.ordereddict import OrderedDict
from pdk.fileutils import safe_mkdirs
import cellh5

from cecog.gui.util import (exception,
                            information,
                            question,
                            warning,
                            numpy_to_qimage,
                            get_qcolor_hicontrast,
                            qcolor_to_hex,
                            )
from cecog.gui.imageviewer import ImageViewer, QGraphicsPixmapHoverItem
from cecog.gui.analyzer import _ProcessorMixin
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore
from cecog.util.util import hexToRgb
from cecog.io.imagecontainer import Coordinate
from cecog.learning.learning import BaseLearner
from cecog.gui.widgets.groupbox import QxtGroupBox
from cecog.gui.widgets.colorbutton import ColorButton
from cecog.gui.modules.module import Module

from cecog.gui.util import numpy_to_qimage
from cecog.gui.modules.display import blend_images_max

from profilehooks import timecall, profile

class Annotations(object):

    def __init__(self):
        self._annotations = {}
        self._counts = {}

    def add(self, coordinate, class_name, item):
        plate = coordinate.plate
        position = coordinate.position
        time = coordinate.time
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

    def remove(self, coordinate, item):
        plate = coordinate.plate
        position = coordinate.position
        time = coordinate.time
        items = self._annotations[plate][position][time]
        for class_name in items.keys():
            if item in items[class_name]:
                items[class_name].remove(item)
                self._counts[class_name] -= 1
                if len(items[class_name]) == 0:
                    del self._annotations[plate][position][time][class_name]
                break

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

    def iter_items(self, coordinate):
        try:
            items = self._annotations[coordinate.plate] \
                                     [coordinate.position] \
                                     [coordinate.time]
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

    def get_class_name(self, coordinate, item):
        items = self._annotations[coordinate.plate] \
                                 [coordinate.position] \
                                 [coordinate.time]
        for class_name in items:
            if item in items[class_name]:
                return class_name
        return None

    def get_annotations_per_class(self, class_name):
        per_class = []
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    ann2 = ann[plateid][position][time]
                    if class_name in ann2:
                        per_class.append((plateid, position, time,
                                          len(ann2[class_name])))
        per_class.sort(key = lambda x: x[2])
        per_class.sort(key = lambda x: x[1])
        per_class.sort(key = lambda x: x[0])
        return per_class

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

    def import_from_xml(self, path, labels_to_names, imagecontainer):
        pattern = re.compile('((.*?_{3})?PL(?P<plate>.*?)_{3})?P(?P<position>.+?)_{1,3}T(?P<time>\d+).*?')
        ann = self._annotations
        ann.clear()
        has_invalid = False
        plates = imagecontainer.plates
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            prefix, suffix = os.path.splitext(filename)
            match = pattern.match(prefix)
            if (os.path.isfile(file_path) and suffix.lower() == '.xml' and
                not match is None):

                plateid = match.group('plate')
                if not plateid is None:
                    assert plateid in plates, \
                           "Plate '%s' not found in data set." % plateid
                elif len(plates) == 1:
                    plateid = plates[0]
                else:
                    raise ValueError("Plate information not specified in "
                                     "annotation file '%s', but multiple "
                                     "plates found in dataset." % filename)

                imagecontainer.set_plate(plateid)
                meta_data = imagecontainer.get_meta_data()
                time_points = meta_data.times
                position = match.group('position')
                time = int(match.group('time'))

                # check whether time is in this data set
                # otherwise this XML file is skipped
                if time in time_points and position in meta_data.positions:
                    idx_base = time_points.index(time)

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
                            # Z is used as the time information in an ImageJ stack here
                            # it's an relative index (1 based). this first frame used
                            # is stored in the XML filename
                            t = int(marker.getElementsByTagName('MarkerZ')[0].childNodes[0].data)

                            idx = idx_base + t - 1
                            if idx < len(time_points):
                                time_ref = time_points[idx]
                                if not time_ref in ann[plateid][position]:
                                    ann[plateid][position][time_ref] = {}
                                ann2 = ann[plateid][position][time_ref]
                                if not class_name in ann2:
                                    ann2[class_name] = set()
                                ann2[class_name].add((x, y))
                            else:
                                has_invalid = True
                else:
                    has_invalid = True
        # rebuild the count info according to the annotation
        self.rebuild_class_counts()
        return has_invalid

    def export_to_xml(self, path, names_to_labels, imagecontainer):
        impl = minidom.getDOMImplementation()
        ann = self._annotations
        for plateid in ann:

            # load plate specific meta data
            imagecontainer.set_plate(plateid)
            meta_data = imagecontainer.get_meta_data()
            time_points = meta_data.times
            # the reference time on which this file is based on
            min_time = time_points[0]

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

                idx_base = time_points.index(min_time)

                for cn in bycn:
                    element2 = doc.createElement('Marker_Type')
                    element.appendChild(element2)
                    element3 = doc.createElement('Type')
                    class_label = names_to_labels[cn]
                    text = doc.createTextNode(str(class_label))
                    element3.appendChild(text)
                    element2.appendChild(element3)
                    for time in bycn[cn]:
                        idx = time_points.index(time) + 1 - idx_base

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
                            text = doc.createTextNode(str(idx))
                            element4.appendChild(text)
                            element3.appendChild(element4)

                            element2.appendChild(element3)

                filename = 'PL%s___P%s___T%05d.xml' % \
                           (plateid, position, min_time)
                f = file(os.path.join(path, filename), 'w')
                doc.writexml(f, indent='  ', addindent='  ', encoding='utf8',
                             newl='\n')
                f.close()


class AnnotationModule(Module):

    NAME = 'Annotation'

    COLUMN_CLASS_NAME = 0
    COLUMN_CLASS_LABEL = 1
    COLUMN_CLASS_COLOR = 2
    COLUMN_CLASS_COUNT = 3

    COLUMN_ANN_PLATE = 0
    COLUMN_ANN_POSITION = 1
    COLUMN_ANN_TIME = 2
    COLUMN_ANN_SAMPLES = 3

    def __init__(self, parent, browser, settings, imagecontainer):
        Module.__init__(self, parent, browser)

        self._current_class = None
        self._detect_objects = False
        self._current_scene_items = set()

        self._settings = settings
        self._imagecontainer = imagecontainer

        self._annotations = Annotations()
        self._object_items = {}

        splitter = QSplitter(Qt.Vertical, self)

        grp_box = QGroupBox('Classes', splitter)
        layout = QBoxLayout(QBoxLayout.TopToBottom, grp_box)
        layout.setContentsMargins(5, 10, 5, 5)

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
        class_table.setStyleSheet('font-size: 10px;')
        layout.addWidget(class_table)
        self._class_table = class_table

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        self._import_class_definitions_btn = QPushButton('Import class definitions')
        layout2.addWidget(self._import_class_definitions_btn)
        self._import_class_definitions_btn.clicked.connect(self._on_import_class_definitions)
        layout.addWidget(frame2)

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        self._class_sbox = QSpinBox(frame2)
        self._class_color_btn = ColorButton(None, frame2)
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


        grp_box = QGroupBox('Annotations', splitter)
        layout = QBoxLayout(QBoxLayout.TopToBottom, grp_box)
        layout.setContentsMargins(5, 10, 5, 5)

        ann_table = QTableWidget(grp_box)
        ann_table.setEditTriggers(QTableWidget.NoEditTriggers)
        ann_table.setSelectionMode(QTableWidget.SingleSelection)
        ann_table.setSelectionBehavior(QTableWidget.SelectRows)
        #ann_table.setSortingEnabled(True)
        column_names = ['Position', 'Frame', 'Samples']
        if self._imagecontainer.has_multiple_plates:
            column_names = ['Plate'] + column_names
        ann_table.setColumnCount(len(column_names))
        ann_table.setHorizontalHeaderLabels(column_names)
        ann_table.resizeColumnsToContents()
        ann_table.currentItemChanged.connect(self._on_anntable_changed)
        ann_table.setStyleSheet('font-size: 10px;')
        layout.addWidget(ann_table)
        self._ann_table = ann_table
        splitter.addWidget(grp_box)


        frame = QFrame(grp_box)
        layout_frame = QBoxLayout(QBoxLayout.LeftToRight, frame)
        layout_frame.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton('New', frame)
        btn.clicked.connect(self._on_new_classifier)
        layout_frame.addWidget(btn)
        #layout_frame.addSpacing(5)
        btn = QPushButton('Open', frame)
        btn.clicked.connect(self._on_open_classifier)
        layout_frame.addWidget(btn)
        btn = QPushButton('Save', frame)
        btn.clicked.connect(self._on_save_classifier)
        layout_frame.addWidget(btn)
        #layout_frame.addSpacing(5)
        btn = QPushButton('Save as', frame)
        btn.pressed.connect(self._on_saveas_classifier)
        layout_frame.addWidget(btn)
        layout.addWidget(frame)

        layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(splitter)


        self._learner = self._init_new_classifier()

        self._action_grp = QActionGroup(browser)
        class_fct = lambda id: lambda : self._on_shortcut_class_selected(id)
        for x in range(1,11):
            action = browser.create_action(
                'Select Class Label %d' % x,
                 shortcut=QKeySequence(str(x) if x < 10 else '0'),
                 slot=class_fct(x))
            self._action_grp.addAction(action)
            browser.addAction(action)

        #browser.coordinates_changed.connect(self._on_coordinates_changed)
        browser.show_objects_toggled.connect(self._on_show_objects)
        browser.show_contours_toggled.connect(self._on_show_contours_toggled)

    def _find_items_in_class_table(self, value, column, match=Qt.MatchExactly):
        items = self._class_table.findItems(value, match)
        return [item for item in items if item.column() == column]

    def _on_import_class_definitions(self):
        if self._on_new_classifier():
            path = self._learner.clf_dir
            if path is None:
                path = os.path.expanduser('~')
            result = QFileDialog.getExistingDirectory(
                self, 'Open classifier directory', os.path.abspath(path))

            if result:
                learner = self._load_classifier(result)
                if learner is not None:
                    self._learner = learner
                    self._update_class_definition_table()
                    self._learner.unset_clf_dir()

    def _update_class_definition_table(self):
        class_table = self._class_table
        class_table.clearContents()
        class_table.setRowCount(len(self._learner.class_labels))
        select_item = None
        for idx, class_label in enumerate(self._learner.class_names):
            samples = 0
            class_name = self._learner.class_names[class_label]
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
                QBrush(QColor(self._learner.hexcolors[class_name])))
            class_table.setItem(idx, self.COLUMN_CLASS_COLOR, item)
        class_table.resizeColumnsToContents()
        class_table.resizeRowsToContents()

        self._activate_objects_for_image(False, clear=True)

    def _on_class_apply(self):
        '''
        Apply class changes
        '''
        learner = self._learner

        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()
        class_name = self._current_class

        if not class_name is None:
            class_label = learner.class_labels[class_name]

            class_labels = learner.class_labels.values()
            class_labels.remove(class_label)
            class_names = learner.class_names.values()
            class_names.remove(class_name)

            if len(class_name_new) == 0:
                warning(self, "Invalid class name",
                        info="The class name must not be empty!")
            elif (not class_name_new in class_names and
                  not class_label_new in class_labels):

                del learner.class_names[class_label]
                del learner.class_labels[class_name]
                del learner.hexcolors[class_name]

                item = self._find_items_in_class_table(class_name,
                                                       self.COLUMN_CLASS_NAME)[0]

                learner.class_names[class_label_new] = class_name_new
                learner.class_labels[class_name_new] = class_label_new
                class_color = self._class_color_btn.current_color
                learner.hexcolors[class_name_new] = \
                    qcolor_to_hex(class_color)

                item.setText(class_name_new)
                item2 = self._class_table.item(item.row(),
                                               self.COLUMN_CLASS_LABEL)
                item2.setText(str(class_label_new))
                item2 = self._class_table.item(item.row(),
                                               self.COLUMN_CLASS_COLOR)
                item2.setBackground(QBrush(class_color))

                col = get_qcolor_hicontrast(class_color)
                self._class_table.resizeRowsToContents()
                self._class_table.resizeColumnsToContents()
                self._class_table.scrollToItem(item)
                css = "selection-background-color: %s; selection-color: %s;" %\
                       (qcolor_to_hex(class_color), qcolor_to_hex(col))
                self._class_table.setStyleSheet(css)
                self._ann_table.setStyleSheet(css)

                self._annotations.rename_class(class_name, class_name_new)
                self._current_class = class_name_new
                self._activate_objects_for_image(False)
                self._activate_objects_for_image(True)
            else:
                warning(self, "Class names and labels must be unique!",
                        info="Class name '%s' or label '%s' already used." %\
                             (class_name_new, class_label_new))

    def _on_class_add(self):
        """Add a new class to definition"""

        learner = self._learner
        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()

        class_labels = learner.class_labels.values()
        class_names = learner.class_names.values()

        if len(class_name_new) == 0:
            warning(self, "Invalid class name",
                    info="The class name must not be empty!")
        elif (not class_name_new in class_names and
              not class_label_new in class_labels):
            self._current_class = class_name_new

            learner.class_names[class_label_new] = class_name_new
            learner.class_labels[class_name_new] = class_label_new
            class_color = self._class_color_btn.current_color
            learner.hexcolors[class_name_new] = \
                qcolor_to_hex(class_color)

            row = self._class_table.rowCount()
            self._class_table.insertRow(row)
            self._class_table.setItem(row, self.COLUMN_CLASS_NAME,
                                      QTableWidgetItem(class_name_new))
            self._class_table.setItem(row, self.COLUMN_CLASS_LABEL,
                                      QTableWidgetItem(str(class_label_new)))
            self._class_table.setItem(row, self.COLUMN_CLASS_COUNT,
                                      QTableWidgetItem('0'))
            item = QTableWidgetItem()
            item.setBackground(QBrush(class_color))
            self._class_table.setItem(row, self.COLUMN_CLASS_COLOR, item)
            self._class_table.resizeRowsToContents()
            self._class_table.resizeColumnsToContents()
            self._class_table.setCurrentItem(item)

            ncl = len(learner.class_names)+1
            self._class_text.setText('class%d' %ncl)
            self._class_sbox.setValue(ncl)
        else:
            warning(self, "Class names and labels must be unique!",
                    info="Class name '%s' or label '%s' already used." %\
                         (class_name_new, class_label_new))

    def _on_class_remove(self):
        '''
        Remove a class and all its annotations
        '''
        class_name = self._current_class
        if (not class_name is None and
            question(self, "Do you really want to remove class '%s'?" % \
                     class_name,
                     info="All %d annotations will be lost." % \
                     self._annotations.get_count_for_class(class_name))):

            self._activate_objects_for_image(False)
            learner = self._learner
            class_label = learner.class_labels[class_name]
            del learner.class_labels[class_name]
            del learner.class_names[class_label]
            del learner.hexcolors[class_name]

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
            else:
                self._update_annotation_table()

    def _init_new_classifier(self):
        learner = BaseLearner(None, None, None)
        self._current_class = None
        self._class_sbox.setValue(1)
        self._class_text.setText('class1')
        self._class_color_btn.set_color(QColor('red'))
        class_table = self._class_table
        class_table.clearContents()
        class_table.setRowCount(0)
        ann_table = self._ann_table
        ann_table.clearContents()
        ann_table.setRowCount(0)
        if self._detect_objects:
            self._activate_objects_for_image(False, clear=True)
        self._annotations.remove_all()
        return learner

    def _on_new_classifier(self):
        ok = False
        if question(self, 'New classifier',
                    'Are you sure to setup a new classifer?\nAll annotations '
                    'will be lost.'):
            self._learner = self._init_new_classifier()
            ok = True

        return ok


    def _on_open_classifier(self):
        try:
            path = os.path.abspath(self._learner.clf_dir)
        except:
            path = os.path.expanduser('~/')

        result = QFileDialog.getExistingDirectory( \
            self, 'Open classifier directory', path)
        if result:
            learner = self._load_classifier(result)
            if not learner is None:
                self._learner = learner
                self._update_class_definition_table()

                self._activate_objects_for_image(False, clear=True)
                path2 = learner.annotations_dir
                try:
                    has_invalid = self._annotations.import_from_xml(path2,
                                                                    learner.class_names,
                                                                    self._imagecontainer)
                except:
                    exception(self, "Problems loading annotation data...")
                    self._learner = self._init_new_classifier()
                else:
                    self._activate_objects_for_image(True)
                    self._update_class_table()
                    if self._class_table.rowCount() > 0:
                        self._class_table.setCurrentCell(0, self.COLUMN_CLASS_NAME)
                    else:
                        self._current_class = None

                    information(self, "Classifier successfully loaded",
                                "Class definitions and annotations "
                                "successfully loaded from '%s'." % result)
                finally:
                    coord = self.browser.get_coordinate()
                    self._imagecontainer.set_plate(coord.plate)

    def _on_save_classifier(self):
        learner = self._learner
        path = learner.clf_dir
        self._on_saveas_classifier(path)

    def _on_saveas_classifier(self, path=None):
        learner = self._learner
        if path is None:
            path = os.path.expanduser("~")
            result = QFileDialog.getExistingDirectory(
                self, 'Save to classifier directory', os.path.abspath(path))
        else:
            result = path

        if result:
            if self._save_classifier(result):
                try:
                    path2 = learner.annotations_dir
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
                    self._annotations.export_to_xml(path2,
                                                    learner.class_labels,
                                                    self._imagecontainer)
                except:
                    exception(self, "Problems saving annotation data...")
                else:
                    information(self, "Classifier successfully saved",
                                "Class definitions and annotations "
                                "successfully saved to '%s'." % result)
                finally:
                    coord = self.browser.get_coordinate()
                    self._imagecontainer.set_plate(coord.plate)

    def _activate_objects_for_image(self, state, clear=False):
        '''
        activate or
        '''
        if clear:
            self._object_items.clear()
        coordinate = self.browser.get_coordinate()
        for class_name, tpl in self._annotations.iter_items(coordinate):
            point = QPointF(*tpl)
            item = self.browser.image_viewer.get_object_item(point)
            if not item is None:
                if not item in self._object_items:
                    self._object_items[item] = point
                self._activate_object(item, point, class_name, state=state)

    def _update_class_table(self):
        '''
        update the class count for the class table
        '''
        counts = self._annotations.get_class_counts()
        for class_name in self._learner.class_names.values():
            if class_name in counts:
                items = self._find_items_in_class_table(class_name,
                                                        self.COLUMN_CLASS_NAME)


                item = self._class_table.item(items[0].row(),
                                              self.COLUMN_CLASS_COUNT)
                item.setText(str(counts[class_name]))
        #self._class_table.update()

    def _update_annotation_table(self):
        '''
        update the annotation table. set the annotation coordinates for
        the current class
        '''
        per_class = \
            self._annotations.get_annotations_per_class(self._current_class)
        ann_table = self._ann_table
        ann_table.blockSignals(True)
        ann_table.clearContents()
        ann_table.setRowCount(len(per_class))
        for idx, data in enumerate(per_class):
            plate, position, time, nr_samples = data
            #m = self._imagecontainer.get_meta_data(plate)
            # plateid in m.plateids
            #if position in m.positions and time in m.times:
            flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
            tooltip = 'Jump to coordinate to see the annotation.'
            #else:
            #    flags = Qt.NoItemFlags
            #    tooltip = 'Coordinate not found in this data set.'

            # make plate information dependent whether the data set contains
            # multiple plates
            if self._imagecontainer.has_multiple_plates:
                item = QTableWidgetItem(plate)
                item.setFlags(flags)
                item.setToolTip(tooltip)
                ann_table.setItem(idx, self.COLUMN_ANN_PLATE, item)
                offset = 0
            else:
                offset = 1

            item = QTableWidgetItem(position)
            item.setFlags(flags)
            item.setToolTip(tooltip)
            ann_table.setItem(idx, self.COLUMN_ANN_POSITION - offset, item)
            item = QTableWidgetItem(str(time))
            item.setFlags(flags)
            item.setToolTip(tooltip)
            ann_table.setItem(idx, self.COLUMN_ANN_TIME - offset, item)
            item = QTableWidgetItem(str(nr_samples))
            item.setFlags(flags)
            item.setToolTip(tooltip)
            ann_table.setItem(idx, self.COLUMN_ANN_SAMPLES - offset, item)

        ann_table.resizeColumnsToContents()
        ann_table.resizeRowsToContents()
        #ann_table.setStyleSheet(css)
        coordinate = self.browser.get_coordinate()
        self._find_annotation_row(coordinate)
        ann_table.blockSignals(False)

    def _find_annotation_row(self, coordinate):
        if self._imagecontainer.has_multiple_plates:
            items1 = self._ann_table.findItems(coordinate.plate,
                                               Qt.MatchExactly)
            rows1 = set(x.row() for x in items1)
            offset = 0
        else:
            rows1 = set(range(self._ann_table.rowCount()))
            offset = 1

        items2 = self._ann_table.findItems(coordinate.position, Qt.MatchExactly)
        items3 = self._ann_table.findItems(str(coordinate.time),
                                           Qt.MatchExactly)
        items2 = [x for x in items2 if x.row() in rows1 and
                  x.column() == 1-offset]
        rows2 = set(x.row() for x in items2)
        items3 = [x for x in items3 if x.row() in rows2 and
                  x.column() == 2-offset]
        assert len(items3) in [0,1]
        if len(items3) == 1:
            self._ann_table.setCurrentItem(items3[0])
        else:
            self._ann_table.clearSelection()

    def _on_new_point(self, point, button, modifier):
        item = self.browser.image_viewer.get_object_item(point)
        #print(item,point,item in self._object_items)
        if button == Qt.LeftButton and not item is None:

            coordinate = self.browser.get_coordinate()
            old_class = None
            # remove the item if already present
            if item in self._object_items:
                point2 = self._object_items[item]
                tpl = (int(point2.x()), int(point2.y()))

                old_class = \
                    self._annotations.get_class_name(coordinate, tpl)
                self._annotations.remove(coordinate, tpl)
                del self._object_items[item]
                self._activate_object(item, point, self._current_class, False)

            # mark a new item only if the shift-key is not pressed, a class
            # is currently active and the class name is different
            if (modifier != Qt.ShiftModifier and
                not self._current_class is None and
                old_class != self._current_class):
                tpl = (int(point.x()), int(point.y()))
                self._annotations.add(coordinate,
                                      self._current_class, tpl)
                self._object_items[item] = point
                self._activate_object(item, point, self._current_class, True)

            self._update_class_table()
            self._update_annotation_table()

    def _on_dbl_clk(self, point):
        pass

    def _activate_object(self, item, point, class_name, state=True):
        if state:
            color = \
                QColor(*hexToRgb(self._learner.hexcolors[class_name]))
            #color.setAlphaF(1.0)
            label = self._learner.class_labels[class_name]
#            item2 = QGraphicsEllipseItem(point.x(), point.y(), 3, 3,item)
#            item2.setPen(QPen(color))
#            item2.setBrush(QBrush(color))
#            item2.show()
            item2 = QGraphicsSimpleTextItem(str(label), item)
            rect = item2.boundingRect()
            # center the text item at the annotated point
            item2.setPos(point - QPointF(rect.width()/2, rect.height()/2))
            item2.setPen(QPen(color))
            item2.setBrush(QBrush(color))
            item2.show()
        else:
            color = self.browser.image_viewer.contour_color
            scene = item.scene()
            for item2 in item.childItems():
                scene.removeItem(item2)
        item.set_pen_color(color)
        obj_id = item.data(0)
        return obj_id

    def _on_coordinates_changed(self, coordinate):
        self._find_annotation_row(coordinate)

    def _on_anntable_changed(self, current, previous):
        if not current is None:
            if self._imagecontainer.has_multiple_plates:
                offset = 0
                plate = self._ann_table.item(current.row(),
                                             self.COLUMN_ANN_PLATE).text()
            else:
                offset = 1
                plate = self._imagecontainer.plates[0]
            col = self.COLUMN_ANN_POSITION - offset
            position = self._ann_table.item(current.row(), col).text()
            col = self.COLUMN_ANN_TIME - offset
            time = int(self._ann_table.item(current.row(), col).text())
            coordinate = Coordinate(plate=plate, position=position, time=time)
            try:
                self.browser.set_coordinate(coordinate)
            except:
                exception(self, "Selected coordinate was not found. "
                                "Make sure the data and annotation match and "
                                "that the data was scanned/imported correctly.")

    def _on_class_changed(self, current, previous):
        if not current is None:
            item = self._class_table.item(current.row(),
                                          self.COLUMN_CLASS_NAME)
            class_name = str(item.text())
            self._current_class = class_name
            hex_col = self._learner.hexcolors[class_name]
            col = get_qcolor_hicontrast(QColor(hex_col))
            class_table = self._class_table
            css = "selection-background-color: %s; selection-color: %s;" % \
                  (hex_col, qcolor_to_hex(col))
            class_table.scrollToItem(item)
            self._class_text.setText(class_name)
            class_label = self._learner.class_labels[class_name]
            self._class_sbox.setValue(class_label)
            self._class_color_btn.set_color(QColor(hex_col))
            class_table.setStyleSheet(css)

            self._update_annotation_table()
            self._ann_table.setStyleSheet(css)
        else:
            self._current_class = None

    def _on_show_contours_toggled(self, state):
        if self.isVisible():
            self._activate_objects_for_image(True)

    def _on_show_objects(self, state):
        if not state:
            self._object_items.clear()
        self._detect_objects = state

    def _on_shortcut_class_selected(self, class_label):
        items = self._find_items_in_class_table(str(class_label),
                                                self.COLUMN_CLASS_LABEL)
        if len(items) == 1:
            self._class_table.setCurrentItem(items[0])

    def _load_classifier(self, path):
        learner = None
        try:
            learner = BaseLearner(path, None, None)
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
            learner.clf_dir = path
            learner.saveDefinition()
        except:
            exception(self, 'Error on saving classifier')
            success = False
        return success

    def set_coords(self):
        if self.isVisible():
            self._activate_objects_for_image(True, clear=True)
            self._update_class_table()

    def activate(self):
        super(AnnotationModule, self).activate()
        self._activate_objects_for_image(True, clear=True)
        self._update_class_table()
        self.browser.image_viewer.image_mouse_pressed.connect(self._on_new_point)
        self._action_grp.setEnabled(True)
        self._find_annotation_row(self.browser.get_coordinate())

    def deactivate(self):
        super(AnnotationModule, self).deactivate()
        self._activate_objects_for_image(False, clear=True)
        self.browser.image_viewer.image_mouse_pressed.disconnect(self._on_new_point)
        self.browser.image_viewer.purify_objects()
        self._action_grp.setEnabled(False)
        
        
class AnnotationsContainer(object):
    def __init__(self, w, p, track_id):
        self.track_id = track_id
        self.well = w
        self.pos = p
        self.graphics_items = []
        self._annotations = {}
        
    def add_graphics_item(self, graphics_item):
        self.graphics_items.append(graphics_item)
        
    def clear_graphics_items(self):
        self.graphics_items = []
        
    def add(self, ann_index, ann_label):
        old_class = -1
        if ann_index in self._annotations:
            old_class = self._annotations[ann_index] 
            del self._annotations[ann_index] 
        if not old_class == ann_label:
            self._annotations[ann_index] = ann_label
    
            
    def show(self, class_def):
        begin_idx = 0
        for k, g in enumerate(self.graphics_items):
            if k in self._annotations:
                pen = QPen(class_def.get_color(self._annotations[k]))
                pen.setWidth(3)
                g.setPen(pen)
                g.setBrush(class_def.get_color(self._annotations[k]))
                for g_ in self.graphics_items[begin_idx:k]:
                    g_.setBrush(class_def.get_color(self._annotations[k]))
                begin_idx = k+1
                
    def encode(self):
        return ",".join(["%d,%d"%(t[0],t[1]) for t in tuple(sorted(self._annotations.items()))])
    
    def decode(self, code_string):
        code = code_string.split(',')
        self._annotations = {}
        for a,b in zip(code[::2], code[1::2]):
            self._annotations[int(a)] = int(b)
        
        
        
    def __len__(self):
        return len(self._annotations)
                    
        
class ClassDefinitions(object):
    def __init__(self):
        self.classes = {}
        
    def add(self, class_label, class_name, class_color):
        self.classes[class_label] = (class_name, class_color)
        
    def remove(self, class_label):
        del self.classes[class_label]
        
    def get_color(self, class_label):
        return self.classes[class_label][1]
    
    def get_name(self, class_label):
        return self.classes[class_label][0]
    
    def get_names(self):
        return [self.get_name(x) for x in self.classes]
    
    def get_definition_table(self):
        n = len(self.classes)
        table = numpy.ndarray((n,), dtype=[('class_label', 'uint8'), ('class_name', '|S64'), ('class_color', '|S8'),])
        for k, c in enumerate(sorted(self.classes)):
            table[k] = (c, self.get_name(c),qcolor_to_hex(self.get_color(c)))
        return table
            
        
        
class CellH5AnnotationModule(Module):
    NAME = 'CellH5 Track Annotation'
    COLUMN_CLASS_NAME = 0
    COLUMN_CLASS_LABEL = 1
    COLUMN_CLASS_COLOR = 2
    COLUMN_CLASS_COUNT = 3
    def __init__(self, parent, browser, settings, imagecontainer):
        Module.__init__(self, parent, browser)
        self._imagecontainer = imagecontainer
        
        self._settings = settings
        self.hdf_file = os.path.join(self._settings.get('General', 'pathout'), 'hdf5', 'all_positions.ch5')
        
        if not os.path.exists(self.hdf_file):
            warning(self, "Invalid hdf5 files",
                        info="%s does not exist!" % self.hdf_file)
        
        
        self.ch5file = cellh5.CH5File(self.hdf_file)
        
        self.class_def = ClassDefinitions()
        
        
        self.cmap = [qRgb(i,i,i) for i in range(256)]
        self.layout = QVBoxLayout(self)
        
        self._init_pos_table()
        self._init_event_table()
        self._init_class_table()
        self._init_options_box()
    
        self.annotations = {}
        
        for i, (w, p, pos) in enumerate(self.ch5file.iter_positions()):
            # Navigation Table
            self.pos_table.insertRow(i)
            w_item = QTableWidgetItem(str(w))
            p_item = QTableWidgetItem(str(p))
            self.pos_table.setItem(i, 0, w_item)
            self.pos_table.setItem(i, 1, p_item)
            if i == 0:
                self.update_track_table(pos)
                self.cur_pos = pos
                self.cur_w = w
                self.cur_p = p
                
            # Annotations
            self.annotations[w, p] = {}
            
            
            
        self.pos_table.resizeColumnsToContents()
        self.pos_table.resizeRowsToContents()
        
        self.browser.image_viewers['gallery'].image_mouse_pressed.connect(self._on_new_point)
        
    @timecall
    def update_track_table(self, pos):
        self.event_table.setRowCount(0)
        events = pos.get_event_items()
        
        events_from = self._sb_events_from.value()
        events_to = self._sb_events_until.value()
    
        selected_track = []
        cnt = 0
        
        start_ids = map(lambda x: x[1][0], events)
        time_idxs = pos.get_time_indecies(start_ids) 
        
        self.tracks = []
        
        for (e_id, e), time_idx in zip(events, time_idxs):
            if events_from <= time_idx <= events_to:
                if self._cb_track.checkState():
                    print 'do tracking'
                    track = e[:-1] + pos.track_first(e[-1])
                else:
                    print 'no tracking'
                    track = e
                
                
                selected_track.append(e)
                self.event_table.insertRow(cnt)
                self.event_table.setItem(cnt, 0, QTableWidgetItem(str(e_id)))
                self.event_table.setItem(cnt, 1, QTableWidgetItem(str(len(track))))
                self.event_table.setItem(cnt, 2, QTableWidgetItem(str(time_idx)))    
                cnt+=1
                self.tracks.append(track)
                
        self.event_table.resizeColumnsToContents()
        self.event_table.resizeRowsToContents()                  
        
    def load_annotations(self, filename):
        plate_id = self._imagecontainer.plates[0]
        object_name = 'event_annotation'
        
        definitions_template = '/definition/feature/%s'
        sample_template = 'sample/0/plate/%s/experiment/%s/position/%s/feature/'
        
        with h5py.File(filename, 'r') as ann_hdf5_handle:     
            # save definition
            class_def = ClassDefinitions()
            def_group = ann_hdf5_handle[definitions_template % object_name]
            table = def_group['class_definition']
            for class_label, class_name, class_color in table:
                class_def.add(class_label, class_name, QColor(str(class_color)))
                   
            # loop over all annotations 
            for w, p in self.annotations:
                ann_prefix = sample_template % (plate_id, w, str(p))
                annotation_group = ann_hdf5_handle[ann_prefix]
                ann_dset = annotation_group[object_name]
                for k, (track_id, anno_string) in enumerate(sorted(ann_dset)):
                    anno = AnnotationsContainer(w, p, track_id)
                    anno.decode(anno_string)
                    self.annotations[(w, p)][track_id] = anno
                    
        self.class_def = class_def
        self._update_class_definition_table()
    
    def save_annotations(self, filename):
        annotations = self.annotations
        plate_id = self._imagecontainer.plates[0]
        object_name = 'event_annotation'
        
        definitions_template = '/definition/feature/%s'
        sample_template = 'sample/0/plate/%s/experiment/%s/position/%s/feature/'
        
        with h5py.File(filename, 'a') as ann_hdf5_handle:
            # Backup of old annotations
            now_string = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            if 'sample' in ann_hdf5_handle:
                ann_hdf5_handle[now_string + '/sample'] = ann_hdf5_handle['sample']
                del ann_hdf5_handle['sample']
            if 'definition' in ann_hdf5_handle:
                ann_hdf5_handle[now_string + '/definition'] = ann_hdf5_handle['definition']
                del ann_hdf5_handle['definition']
                
            # save definition
            def_group = ann_hdf5_handle.create_group(definitions_template % object_name)
            table = self.class_def.get_definition_table()
            def_group.create_dataset('class_definition', shape=table.shape, dtype=table.dtype, data=table)
            
            
                
            # loop over all annotations 
            for (w, p), annotation_dict in annotations.items():
                ann_prefix = sample_template % (plate_id, w, str(p))
                annotation_group = ann_hdf5_handle.create_group(ann_prefix)
                ann_dset = annotation_group.create_dataset(object_name, (len(annotation_dict),), [('event_id', 'int32'), ('annotation', h5py.new_vlen(str))])
                for k, track_id in enumerate(sorted(annotation_dict)):
                    a = annotation_dict[track_id]
                    assert track_id == a.track_id
                    ann_dset[k] = (track_id, a.encode())
                
     
    def _on_load_annotations(self):
        filename = os.path.join(self._settings.get('General', 'pathout'), 'hdf5', 'annotations_all_positions.ch5')
        if os.path.exists(filename):
            self.load_annotations(filename)
            information(self, 'Track annotations successfully loaded', filename)
        else:
            warning(self, 'No annotations found...', filename)
        
    def _on_save_annotations(self):
        filename = os.path.join(self._settings.get('General', 'pathout'), 'hdf5', 'annotations_all_positions.ch5')
        self.save_annotations(filename)
        information(self, 'Annotations successfully saved!', filename)
        
    @timecall
    def _init_pos_table(self):
        self.pos_table = QTableWidget(self)
        self.pos_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pos_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pos_table.setColumnCount(2)
        self.pos_table.setHorizontalHeaderLabels(['Well', 'Site'])
        self.pos_table.resizeColumnsToContents()
        self.pos_table.currentItemChanged.connect(self._on_pos_changed)
        self.pos_table.setStyleSheet('font-size: 10px;')
        self.layout.addWidget(self.pos_table)
        
    @timecall
    def _init_event_table(self):
        self.event_table = QTableWidget(self)
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.event_table.setSelectionMode(QTableWidget.SingleSelection)
        self.event_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.event_table.setColumnCount(3)
        self.event_table.setHorizontalHeaderLabels(['Event Id', 'Event Length', 'Start Frame',])
        self.event_table.resizeColumnsToContents()
        self.event_table.currentItemChanged.connect(self._on_track_changed)
        self.event_table.setStyleSheet('font-size: 10px;')
        self.layout.addWidget(self.event_table)
        
    @timecall
    def _init_class_table(self):
        grp_box = QGroupBox('Classes', self)
        layout = QBoxLayout(QBoxLayout.TopToBottom, grp_box)

        self.class_table = QTableWidget(grp_box)
        self.class_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.class_table.setSelectionMode(QTableWidget.SingleSelection)
        self.class_table.setSelectionBehavior(QTableWidget.SelectRows)
        #self.class_table.setSortingEnabled(True)
        self.class_table.setColumnCount(4)
        self.class_table.setHorizontalHeaderLabels(['Name', 'Label', 'Color',
                                               'Samples',
                                               ])
        self.class_table.resizeColumnsToContents()
        self.class_table.currentItemChanged.connect(self._on_class_changed)
        self.class_table.setStyleSheet('font-size: 10px;')
        layout.addWidget(self.class_table)

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        self._import_class_definitions_btn = QPushButton('Import class definitions')
        layout2.addWidget(self._import_class_definitions_btn)
        self._import_class_definitions_btn.clicked.connect(self._on_import_class_definitions)
        layout.addWidget(frame2)

        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        self._class_sbox = QSpinBox(frame2)
        self._class_color_btn = ColorButton(None, frame2)
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
        
        frame2 = QFrame(grp_box)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        layout2.setContentsMargins(0,0,0,0)
        btn = QPushButton('Save', frame2)
        btn.clicked.connect(self._on_save_annotations)
        layout2.addWidget(btn)
        btn = QPushButton('Load', frame2)
        btn.clicked.connect(self._on_load_annotations)
        layout2.addWidget(btn)
        layout.addWidget(frame2)
        
        
        
        
        
        self._class_sbox.setValue(1)
        self._class_text.setText('class 1')
        self._class_color_btn.set_color(QColor('red'))

        self.layout.addWidget(grp_box)
        
    @timecall
    def _init_options_box(self):
        grp_box = QGroupBox('Options', self)
        grp_layout = QVBoxLayout(grp_box)
        grp_layout.setContentsMargins(0, 0, 0, 0)
        
        
        # object type
        frame = QWidget(self)
        layout = QHBoxLayout(frame)
        layout.addWidget(QLabel('Regions'))
        self._cbb_object = QComboBox()
        for o in self.ch5file.object_definition.keys():
            if self.ch5file.has_object_features(o):
                self._cbb_object.addItem(str(o))
        layout.addWidget(self._cbb_object)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        # fate tracking
        frame = QWidget(grp_box)
        layout = QHBoxLayout(frame)
        self._cb_track = QCheckBox('Event Fate', self)
        self._cb_track.setCheckState(False)
        layout.addWidget(self._cb_track)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        # event selection
        frame = QFrame(grp_box)
        layout = QHBoxLayout(frame)
        layout.addWidget(QLabel('Event Onset From'))
        self._sb_events_from = QSpinBox(self)
        self._sb_events_from.setMaximum(9999)
        self._sb_events_from.setValue(0)
        layout.addWidget(self._sb_events_from)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        frame = QFrame(grp_box)
        layout = QHBoxLayout(frame)
        layout.addWidget(QLabel('Event Onset Until'))
        self._sb_events_until = QSpinBox(self)
        self._sb_events_until.setMaximum(9999)
        self._sb_events_until.setValue(9999)
        layout.addWidget(self._sb_events_until)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        # Gallery Size
        frame = QFrame(grp_box)
        layout = QHBoxLayout(frame)
        layout.addWidget(QLabel('Gallery Size'))
        self._sb_gallery_size = QSpinBox(self)
        self._sb_gallery_size.setValue(52)
        self._sb_gallery_size.setMinimum(52)
        self._sb_gallery_size.setSingleStep(4)
        layout.addWidget(self._sb_gallery_size)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        # show seg
        frame = QFrame(grp_box)
        layout = QHBoxLayout(frame)
        self._cb_segmentation = QCheckBox('Show Segmentation', self)
        self._cb_segmentation.setCheckState(False)
        layout.addWidget(self._cb_segmentation)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        # show classificaton
        frame = QFrame(grp_box)
        layout = QHBoxLayout(frame)
        self._cb_classification = QCheckBox('Show Segmentation', self)
        self._cb_classification.setCheckState(False)
        layout.addWidget(self._cb_classification)
        frame.setLayout(layout)
        grp_layout.addWidget(frame)
        
        self.layout.addWidget(grp_box)
        
        self.btn = QPushButton('Update')
        self.btn.clicked.connect(self.update_options)
        self.layout.addWidget(self.btn)
    
    def update_options(self):
        self.update_track_table(self.cur_pos)
    
    def _on_class_changed(self, current, previous):
        if not current is None:
            item = self.class_table.item(current.row(),
                                          self.COLUMN_CLASS_LABEL)
            class_label = int(item.text())
            self._current_class = class_label

            class_color = self.class_def.get_color(class_label)
            class_name = self.class_def.get_name(class_label)
            css = "selection-background-color: %s; selection-color: %s;" % \
                  (qcolor_to_hex(class_color), qcolor_to_hex(get_qcolor_hicontrast(class_color)))
            self.class_table.setStyleSheet(css)
            
            self.class_table.scrollToItem(item)
            self._class_color_btn.set_color(class_color)
            
            self._class_text.setText(class_name)
            self._class_sbox.setValue(class_label)
            self._class_color_btn.set_color(class_color)
            
        else:
            self._current_class = None
    
    def _on_import_class_definitions(self):
        ok = False
        if question(self, 'New classifier',
                    'Are you sure to setup a new classifer?\nAll annotations '
                    'will be lost.'):
            ok = True

        if not ok:
            return

        path = os.path.expanduser('~')
        result = QFileDialog.getExistingDirectory(
            self, 'Open classifier directory', os.path.abspath(path))

        if result:
            self.class_def = self._import_class_def(result)
            self._update_class_definition_table()
            
    def _import_class_def(self, path):
        try:
            learner = BaseLearner(path, None, None)
        except:
            exception(self, 'Error on loading classifier')
        else:
            result = learner.check()
            if result['has_definition']:
                learner.loadDefinition()
                class_def = ClassDefinitions()
                for class_label in sorted(learner.class_labels.values()):
                    class_name = learner.class_names[class_label]
                    class_color = QColor(learner.hexcolors[class_name])
                    class_def.add(class_label, class_name, class_color)                    
                return class_def
                
    def _update_class_definition_table(self):
        class_table = self.class_table
        class_table.clearContents()
        class_table.setRowCount(len(self.class_def.classes))
        select_item = None
        for idx, class_label in enumerate(sorted(self.class_def.classes)):
            samples = 0
            class_name = self.class_def.get_name(class_label)
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
                QBrush(QColor(self.class_def.get_color(class_label))))
            class_table.setItem(idx, self.COLUMN_CLASS_COLOR, item)
        class_table.resizeColumnsToContents()
        class_table.resizeRowsToContents()
                
    def _on_class_add(self):
        class_def = self.class_def
        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()


        if len(class_name_new) == 0:
            warning(self, "Invalid class name",
                    info="The class name must not be empty!")
        elif (not class_label_new in class_def.classes) and (not class_name_new in class_def.get_names()):
            self._current_class = class_label_new

            class_color = self._class_color_btn.current_color

            row = self.class_table.rowCount()
            self.class_table.insertRow(row)
            self.class_table.setItem(row, self.COLUMN_CLASS_NAME,
                                      QTableWidgetItem(class_name_new))
            self.class_table.setItem(row, self.COLUMN_CLASS_LABEL,
                                      QTableWidgetItem(str(class_label_new)))
            self.class_table.setItem(row, self.COLUMN_CLASS_COUNT,
                                      QTableWidgetItem('0'))
            item = QTableWidgetItem()
            item.setBackground(QBrush(class_color))
            self.class_table.setItem(row, self.COLUMN_CLASS_COLOR, item)
            self.class_table.resizeRowsToContents()
            self.class_table.resizeColumnsToContents()

            self._class_text.setText('class %d' % (self.class_table.rowCount()+1))
            self._class_sbox.setValue(self.class_table.rowCount()+1)
            self.class_def.add(class_label_new, class_name_new, class_color)
            self._class_color_btn.set_color(QColor(numpy.random.randint(255),numpy.random.randint(255),numpy.random.randint(255)))
            self.class_table.setCurrentItem(item)
            
        else:
            warning(self, "Class names and labels must be unique!",
                    info="Class name '%s' or label '%s' already used." %\
                         (class_name_new, class_label_new))
    
    def _on_class_remove(self):
        pass
    
    def _find_items_in_class_table(self, value, column, match=Qt.MatchExactly):
        items = self.class_table.findItems(value, match)
        return [item for item in items if item.column() == column]
    
    def _on_class_apply(self):
        class_name_new = str(self._class_text.text())
        class_label_new = self._class_sbox.value()
        class_color_new = self._class_color_btn.current_color
        class_label = self._current_class
        
        del self.class_def.classes[class_label]

        if not class_label is None:
            if len(class_name_new) == 0:
                warning(self, "Invalid class name",
                        info="The class name must not be empty!")
                
            elif (not class_name_new in self.class_def.get_names() and
                  not class_label_new in self.class_def.classes):

                item = self._find_items_in_class_table(class_name_new,
                                                       self.COLUMN_CLASS_NAME)[0]

                self.class_def.add(class_label_new, class_name_new, class_color_new)

                item.setText(class_name_new)
                item2 = self.class_table.item(item.row(),
                                               self.COLUMN_CLASS_LABEL)
                item2.setText(str(class_label_new))
                item2 = self.class_table.item(item.row(),
                                               self.COLUMN_CLASS_COLOR)
                item2.setBackground(QBrush(class_color_new))

                col = get_qcolor_hicontrast(class_color_new)
                self.class_table.resizeRowsToContents()
                self.class_table.resizeColumnsToContents()
                self.class_table.scrollToItem(item)
                css = "selection-background-color: %s; selection-color: %s;" %\
                       (qcolor_to_hex(class_color_new), qcolor_to_hex(col))
                self.class_table.setStyleSheet(css)

            else:
                warning(self, "Class names and labels must be unique!",
                        info="Class name '%s' or label '%s' already used." %\
                             (class_name_new, class_label_new))
    
    def activate(self):
        print 'CellH5Annotator.activate()'
        self.browser.set_display_module(self)
        self.browser.set_image_viewer('gallery')
        
        
    def deactivate(self):
        print 'CellH5Annotator.deactivate()'
        self.browser.set_display_module(self.browser._module_manager.get_widget('Display'))
        self.browser.set_image_viewer('image')
            
    def _on_pos_changed(self, current, previous):
        print '_on_pos_changed'
        w = str(self.pos_table.item(current.row(), 0).text())         
        p = str(self.pos_table.item(current.row(), 1).text())   
        print 'CellH5Annotator._on_pos_changed()', w, p
        pos = self.ch5file.get_position(w, str(p))    
        self.cur_pos = pos
        self.cur_w = w
        self.cur_p = p
        self.update_track_table(pos)
             
    def _on_track_changed(self, current, previous):
        print '_on_track_changed'
        track_idx = current.row()         
        track_id = int(self.event_table.item(current.row(), 0).text())     
        self.cur_track_id = track_id
        self.cur_track_idx = track_idx     
        self.show_tracks(track_idx, track_id)
        
    def _on_new_point(self, point, button, modifier):
        print point, button, modifier
        self.insert_annotation(point)
        self.update_annotations()
         
    def insert_annotation(self, point):
        for k, g in enumerate(self.cur_annotation.graphics_items):
            if g.contains(point):
                print 'added item', k, 'with', point
                self.cur_annotation.add(k, self._current_class)
                break
        self.reset_annotation_items()
        self.update_annotations()
                
         
    def update_annotations(self):
        self.cur_annotation.show(self.class_def)
        
    def reset_annotation_items(self):
        for g in self.cur_annotation.graphics_items:
            g.setBrush(Qt.white)
            g.setZValue(5)
            g.setPen(QPen())
        
        
    @timecall
    def show_tracks(self, idx, track_id):
        print 'show_tracks for track_id',  track_id
        self.browser.image_viewer.clear()
        pos = self.cur_pos
        w = pos.well
        p = pos.pos
        
        if track_id not in self.annotations[(w, p)]:
            annotations = AnnotationsContainer(w, p, track_id)
            self.annotations[(w, p)][track_id] = annotations
        else:
            annotations = self.annotations[(w, p)][track_id]
            annotations.clear_graphics_items()
            
        self.cur_annotation = annotations
            
        #self.clear_annotation_items()
        

        cellh5.GALLERY_SIZE = self._sb_gallery_size.value()
        step = cellh5.GALLERY_SIZE
        
        x_max = 1000
        x, y = 0, 0
        
        
        track = self.tracks[idx]
        
        object_ = str(self._cbb_object.currentText())
        
        for i, gallery_numpy in enumerate(pos.get_gallery_image_generator(track, object_)):
            gallery_item = QGraphicsPixmapHoverItem(QPixmap(numpy_to_qimage(gallery_numpy, self.cmap )))
            gallery_item.setPos(x, y)
            self.browser.image_viewer._scene.addItem(gallery_item)
            
            annotation_item = QGraphicsRectItem(x, y, 10, 10)
            annotation_item.setBrush(Qt.white)
            annotation_item.setZValue(5)
            self.browser.image_viewer._scene.addItem(annotation_item)
            annotations.add_graphics_item(annotation_item)
            
            
            if self._cb_segmentation.checkState():
                contour_item = QGraphicsPolygonItem(QPolygonF(map(lambda x: QPointF(x[0],x[1]), self.cur_pos.get_crack_contour(track[i],object_)[0])))
                contour_item.setPos(x,y)
                color = Qt.red
                if self._cb_classification.checkState():
                    color = QColor(self.cur_pos.get_class_color(track[i]))
                contour_item.setPen(QPen(color))
                contour_item.setZValue(4)
                
                self.browser.image_viewer._scene.addItem(contour_item)

            x += step
            if x > x_max:
                x = 0
                y += step
            print gallery_numpy.shape
            
        self.update_annotations()
        
            
        
    
    def set_image_dict(self, image_dict):
        print 'CellH5Annotator.set_image_dict()'  
    
    def do(self):
        self.show_tracks('0', '0038')
        