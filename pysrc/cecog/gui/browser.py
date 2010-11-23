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

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#


class MyItem(QGraphicsPolygonItem):

    SCALE = 1.1

    def __init__(self, polygon):
        super(MyItem, self).__init__(polygon)
        self._oldwidth = self.pen().width()
        #self.setAcceptHoverEvents(True)
#        self._effect = QGraphicsColorizeEffect()
#        self._effect.setColor(QColor('red'))
#        self._effect.setStrength(100.0)
#        self._effect.setEnabled(False)
#        self.setGraphicsEffect(self._effect)

    def hoverEnterEvent(self, ev):
        #self.setTransformOriginPoint(0, 0)
        #self.setScale(self.SCALE)
        #self._effect.setEnabled(True)
        pen = self.pen()
        self._oldwidth = self.pen().width()
        pen.setWidth(3)
        self.setPen(pen)
        super(MyItem, self).hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev):
        #self.setScale(1.0)
        #self._effect.setEnabled(False)
        pen = self.pen()
        pen.setWidth(self._oldwidth)
        self.setPen(pen)
        super(MyItem, self).hoverLeaveEvent(ev)


class Annotations(object):

    def __init__(self):
        self._annotations = {}
        self._counts = {}

    def add(self, plate, position, time, channel, class_name, item):
        ann = self._annotations
        if not plate in ann:
            ann[plate] = {}
        if not position in ann[plate]:
            ann[plate][position] = {}
        if not time in ann[plate][position]:
            ann[plate][position][time] = {}
        if not channel in ann[plate][position][time]:
            ann[plate][position][time][channel] = {}
        if not class_name in ann[plate][position][time][channel]:
            ann[plate][position][time][channel][class_name] = set()
        ann[plate][position][time][channel][class_name].add(item)

        if not class_name in self._counts:
            self._counts[class_name] = 0
        self._counts[class_name] += 1

    def remove(self, plate, position, time, channel, item):
        items = self._annotations[plate][position][time][channel]
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
                        for channel in ann[plateid][position][time]:
                            ann2 = ann[plateid][position][time][channel]
                            if name_old in ann2:
                                ann2[name_new] = ann2[name_old]
                                del ann2[name_old]

    def remove_class(self, class_name):
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    for channel in ann[plateid][position][time]:
                        ann2 = ann[plateid][position][time][channel]
                        if class_name in ann2:
                            del ann2[class_name]
        if class_name in self._counts:
            del self._counts[class_name]

    def iter_items(self, plate, position, time, channel):
        try:
            items = self._annotations[plate][position][time][channel]
            for class_name in items:
                for item in items[class_name]:
                    yield (class_name, item)
        except KeyError:
            pass

    def get_class_counts(self):
        return self._counts

    def get_count_for_class(self, class_name):
        return self.get_class_counts().get(class_name, 0)

    def rebuild_class_counts(self):
        self._counts.clear()
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:
                for time in ann[plateid][position]:
                    for channel in ann[plateid][position][time]:
                        for cn in ann[plateid][position][time][channel]:
                            if cn not in self._counts:
                                self._counts[cn] = 0
                            items = ann[plateid][position][time][channel][cn]
                            self._counts[cn] += len(items)

    def import_from_xml(self, path, channel, labels_to_names):
        pattern = re.compile('(.*__)?P(?P<position>.+?)__T(?P<time>\d+).*?')
        ann = self._annotations
        ann.clear()
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            prefix, suffix = os.path.splitext(filename)
            match = pattern.match(prefix)
            if (os.path.isfile(file_path) and suffix.lower() == '.xml' and
                not match is None):

                plateid = None
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
                        if not channel in ann2:
                            ann2[channel] = {}
                        if not class_name in ann2[channel]:
                            ann2[channel][class_name] = set()
                        ann2[channel][class_name].add((x, y))
        self.rebuild_class_counts()

    def export_to_xml(self, path, min_time, channel, names_to_labels):
        impl = minidom.getDOMImplementation()
        ann = self._annotations
        for plateid in ann:
            for position in ann[plateid]:

                ann2 = ann[plateid][position]
                bycn = OrderedDict()
                for time in ann2:
                    for cn in ann2[time][channel]:
                        if not cn in bycn:
                            bycn[cn] = OrderedDict()
                        bycn[cn][time] = ann2[time][channel][cn]

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

                filename = 'P%s__T%05d__C%s.xml' % (position, min_time, channel)
                f = file(os.path.join(path, filename), 'w')
                doc.writexml(f, indent='  ', addindent='  ', encoding='utf8',
                             newl='\n')
                f.close()


@singleton
class Browser(QMainWindow):

    ZOOM_STEP = 1.05
    COLUMN_CLASS_NAME = 0
    COLUMN_CLASS_LABEL = 1
    COLUMN_CLASS_COLOR = 2
    COLUMN_CLASS_COUNT = 3

    def __init__(self, settings, imagecontainer):
        QMainWindow.__init__(self)

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._stopwatch = StopWatch()
        self._zoom_value = 1.0
        self._current_class = None
        self._detect_objects = False
        self._current_scene_items = set()

        self.grabGesture(Qt.PinchGesture)
        self.grabGesture(Qt.SwipeGesture)

        act_new = self.create_action('New Classifier...',
                                     shortcut=QKeySequence.New,
                                     slot=self._on_new_classifier)
        act_open = self.create_action('Open Classifier...',
                                      shortcut=QKeySequence.Open,
                                      slot=self._on_open_classifier)
#        act_save = self.create_action('Save Classifier...',
#                                      shortcut=QKeySequence.Save,
#                                      slot=self._on_save_classifier)
        act_saveas = self.create_action('Save Classifier As...',
                                        shortcut=QKeySequence.SaveAs,
                                        slot=self._on_saveas_classifier)
        file_menu = self.menuBar().addMenu('&File')
        self.add_actions(file_menu, (act_new, act_open, None,
                                     #act_save,
                                     act_saveas,
                                     ))

        act_next_t = self.create_action('Next Time-point',
                                        shortcut=QKeySequence('Right'),
                                        slot=self._on_shortcut_right)
        act_prev_t = self.create_action('Previous Time-point',
                                        shortcut=QKeySequence('Left'),
                                        slot=self._on_shortcut_left)
        act_resize = self.create_action('Automatically Resize',
                                         shortcut=QKeySequence('SHIFT+CTRL+R'),
                                         slot=self._on_shortcut_autoresize,
                                         signal='triggered(bool)',
                                         checkable=True,
                                         checked=True)
        self._act_resize = act_resize
        act_zoomfit = self.create_action('Zoom to Fit',
                                         shortcut=QKeySequence('CTRL+0'),
                                         slot=self._on_shortcut_zoomfit)
        act_zoom100 = self.create_action('Actual Size',
                                         shortcut=QKeySequence('CTRL+1'),
                                         slot=self._on_shortcut_zoom100)
        act_zoomin = self.create_action('Zoom In',
                                        shortcut=QKeySequence('CTRL++'),
                                        slot=self._on_shortcut_zoomin)
        act_zoomout = self.create_action('Zoom Out',
                                         shortcut=QKeySequence('CTRL+-'),
                                         slot=self._on_shortcut_zoomout)
        act_fullscreen = self.create_action('Full Screen',
                                            shortcut=QKeySequence('CTRL+F'),
                                            slot=self._on_shortcut_fullscreen,
                                            signal='triggered(bool)',
                                            checkable=True,
                                            checked=False)
        self._act_fullscreen = act_fullscreen
        act_anti = self.create_action('Antialiasing',
                                      shortcut=QKeySequence('CTRL+ALT+A'),
                                      slot=self._on_shortcut_antialiasing,
                                      signal='triggered(bool)',
                                      checkable=True,
                                      checked=True)
        act_smooth = self.create_action('Smooth Transform',
                                        shortcut=QKeySequence('CTRL+ALT+S'),
                                        slot=self._on_shortcut_smoothtransform,
                                        signal='triggered(bool)',
                                        checkable=True,
                                        checked=True)
        view_menu = self.menuBar().addMenu('&View')
        self.add_actions(view_menu, (act_resize, None,
                                     act_zoom100, act_zoomfit,
                                     act_zoomin, act_zoomout,
                                     None,
                                     act_prev_t, act_next_t, None,
                                     act_fullscreen, None,
                                     act_anti, act_smooth,
                                     ))

        class_fct = lambda id: lambda : self._on_shortcut_class_selected(id)
        act_class = \
            [self.create_action(
                'Select Class Label %d' % x,
                 shortcut=QKeySequence(str(x) if x < 10 else '0'),
                 slot=class_fct(x))
             for x in range(1,11)]
        menu = self.menuBar().addMenu('&Annotation')
        self.add_actions(menu, act_class)

        self.setContentsMargins(5, 5, 5, 5)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self._settings = settings
        self._imagecontainer = imagecontainer
        self._meta_data = self._imagecontainer.meta_data

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal, frame)
        #splitter.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
        #                                   QSizePolicy.Expanding))
        layout.addWidget(splitter)

        splitter2 = QSplitter(Qt.Vertical, splitter)
        #splitter2.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
        #                                    QSizePolicy.Expanding))
        #splitter2.setMinimumWidth(20)

        frame = QFrame(splitter)
        frame_side = QFrame(splitter)
        #frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
        #                                QSizePolicy.Expanding))

        splitter.addWidget(splitter2)
        splitter.addWidget(frame)
        splitter.addWidget(frame_side)
        splitter.setMinimumWidth(20)
        splitter.setStretchFactor(1,2)
        #splitter.setSizes([30,300])

        grp1 = QFrame(splitter2)
        grp2 = QFrame(splitter2)
        splitter2.addWidget(grp1)
        splitter2.addWidget(grp2)

        layout = QGridLayout(grp1)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(QLabel('Plates', grp1), 0, 0)

        table = QTableWidget(grp1)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        #table.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,
        #                                QSizePolicy.Expanding|QSizePolicy.Maximum))
        #table.setColumnCount(3)
        #table.setRowCount(len(meta_data.positions))
        #table.setMinimumWidth(20)
        layout.addWidget(table, 1, 0)

        layout = QGridLayout(grp2)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(QLabel('Positions', grp2), 0, 0)

        table = QTableWidget(grp2)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        #table.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,
        #                                QSizePolicy.Expanding|QSizePolicy.Maximum))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Position', 'Well', 'Subwell'])
        table.setRowCount(len(self._meta_data.positions))

        for idx, pos in enumerate(self._meta_data.positions):
            #table.setRowHeight(idx, 15)
            table.setItem(idx, 0, QTableWidgetItem(pos))
#            self._table_info.setItem(r, 1, QTableWidgetItem(str(samples)))
#            item = QTableWidgetItem(' ')
#            item.setBackground(QBrush(QColor(*hexToRgb(self._learner.dctHexColors[name]))))
#            self._table_info.setItem(r, 2, item)
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.currentItemChanged.connect(self._on_position_changed)
        #table.setMinimumWidth(20)
        layout.addWidget(table, 1, 0)

        self._annotations = Annotations()
        self._object_items = {}
        self._plateid = None
        self._channel = None

        layout = QGridLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        self._image_viewer = ImageViewer(frame, auto_resize=True)
        self._image_viewer.setTransformationAnchor(ImageViewer.AnchorViewCenter)
        self._image_viewer.setResizeAnchor(ImageViewer.AnchorViewCenter)
        self._image_viewer.setRenderHints(QPainter.Antialiasing |
                                          QPainter.SmoothPixmapTransform)
        self._image_viewer.setViewportUpdateMode(ImageViewer.SmartViewportUpdate)
        self._image_viewer.setBackgroundBrush(QBrush(QColor('#666666')))
        layout.addWidget(self._image_viewer, 0, 0, 1, 2)
        self._image_viewer.image_mouse_pressed.connect(self._on_new_point)
        self._image_viewer.image_mouse_dblclk.connect(self._on_dbl_clk)
        self._image_viewer.zoom_info_updated.connect(self._on_zoom_info_updated)

        self._t_slider = QSlider(Qt.Horizontal, frame)
        self._t_slider.setMinimum(self._meta_data.times[0])
        self._t_slider.setMaximum(self._meta_data.times[-1])
        self._t_slider.setTickPosition(QSlider.TicksBelow)
        self._t_slider.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self._t_slider, 1, 1)

        self._position = None
        self._time = self._t_slider.minimum()

        self._t_label = QLabel('t=%d' % self._time, frame)
        self._t_label.setMinimumWidth(45)
        layout.addWidget(self._t_label, 1, 0)

        layout = QGridLayout(frame_side)
        layout.setContentsMargins(5, 5, 5, 5)

        class_table = QTableWidget(frame_side)
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
        layout.addWidget(class_table, 0, 0, 1, 3)
        self._class_table = class_table

        frame2 = QFrame(frame_side)
        layout2 = QBoxLayout(QBoxLayout.LeftToRight, frame2)
        self._class_sbox = QSpinBox(frame2)
        self._class_color_btn = QToolButton(frame2)
        self._class_color_btn.clicked.connect(self._on_class_color)
        self._class_color = None
        self._class_sbox.setRange(0, 1000)
        self._class_text = QLineEdit(frame2)
        layout2.addWidget(self._class_color_btn)
        layout2.addWidget(self._class_sbox)
        layout2.addWidget(self._class_text)
        layout.addWidget(frame2, 1, 0, 1, 3)
        btn = QPushButton('Apply', frame_side)
        btn.clicked.connect(self._on_class_apply)
        layout.addWidget(btn, 2, 0)
        btn = QPushButton('Add', frame_side)
        btn.clicked.connect(self._on_class_add)
        layout.addWidget(btn, 2, 1)
        btn = QPushButton('Remove', frame_side)
        btn.clicked.connect(self._on_class_remove)
        layout.addWidget(btn, 2, 2)

        self._learner = self._init_new_classifier()

        box = QCheckBox('Detect objects', frame_side)
        box.setCheckState(Qt.Checked if self._detect_objects else Qt.Unchecked)
        layout.addWidget(box, 10, 0)
        box.clicked.connect(self._on_detect_box)

        # ensure a valid position (not None!)
        table.setCurrentCell(0, 0)
        #self._class_table.setCurrentCell(0, 0)


    def _on_class_color(self):
        dlg = QColorDialog(self)
        if not self._class_color is None:
            dlg.setCurrentColor(self._class_color)
        if dlg.exec_():
            col = dlg.currentColor()
            self._class_color_btn.setStyleSheet('background-color: rgb(%d, %d, %d)'\
                                                % (col.red(), col.green(),
                                                   col.blue()))
            self._class_color = col

    def _on_zoom_info_updated(self, info):
        print info

    def _find_items_in_class_table(self, value, column, match=Qt.MatchExactly):
        items = self._class_table.findItems(value, match)
        return [item for item in items if item.column() == column]


    def _on_class_apply(self):
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
        channel =  None

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
                    self._annotations.import_from_xml(path2, channel,
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
                    information(self, "Classifier successfully loaded",
                                "Class definitions and annotations "
                                "successfully loaded from '%s'." % path)

    def _on_saveas_classifier(self):
        channel =  None
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
                    self._annotations.export_to_xml(path2, min_time, channel,
                                                    learner.dctClassLabels)
                except:
                    exception(self, "Problems saving annotation data...")
                else:
                    information(self, "Classifier successfully saved",
                                "Class definitions and annotations "
                                "successfully saved to '%s'." % path)

#    def _on_saveas_classifier(self):
#        pass

    def create_action(self, text, slot=None, shortcut=None, icon=None,
                      tooltip=None, checkable=None, signal='triggered()',
                      checked=False):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(':/%s.png' % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip is not None:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable is not None:
            action.setCheckable(True)
        action.setChecked(checked)
        return action

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def _activate_objects_for_image(self, state=True, clear=False):
        if clear:
            self._object_items.clear()
        for class_name, tpl in self._annotations.iter_items(self._plateid,
                                                            self._position,
                                                            self._time,
                                                            self._channel):
            point = QPointF(*tpl)
            item = self._get_object_item(point)
            if not item in self._object_items:
                self._object_items[item] = point
            self._activate_object(item, class_name, state=state)

    def set_coords(self, coords):
        scene = self._image_viewer.scene()
        for item in self._current_scene_items:
            scene.removeItem(item)
        self._current_scene_items.clear()
        for obj_id, crack in coords.iteritems():
            poly = QPolygonF([QPointF(*pos) for pos in crack])
            item = MyItem(poly)
            item.setPen(QPen(Qt.white))
            item.setAcceptHoverEvents(True)
            item.setData(0, obj_id)
            scene.addItem(item)
            self._current_scene_items.add(item)
        self._object_items.clear()
        self._activate_objects_for_image()
        self._update_class_table()

    def set_image(self, image):
        s = StopWatch()
        print(image)
        if image.width % 4 != 0:
            image = ccore.subImage(image, ccore.Diff2D(0,0),
                                   ccore.Diff2D(image.width-(image.width % 4),
                                                image.height))
        qimage = numpy_to_qimage(image.toArray(copy=True))
        self._image_viewer.from_qimage(qimage)

        print('SET IMAGE: %s (total: %s)' % (s, self._stopwatch))

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
        item = self._get_object_item(point)
        print(item,point,item in self._object_items)
        if button == Qt.LeftButton and not item is None:

            # remove the item if already present
            if item in self._object_items:
                point2 = self._object_items[item]
                tpl = (int(point2.x()), int(point2.y()))
                self._annotations.remove(self._plateid, self._position,
                                         self._time, self._channel,
                                         tpl)
                del self._object_items[item]
                self._activate_object(item, self._current_class, False)

            # mark a new item if the shift-key is not pressed
            if modifier != Qt.ShiftModifier and not self._current_class is None:
                tpl = (int(point.x()), int(point.y()))
                self._annotations.add(self._plateid, self._position,
                                      self._time, self._channel,
                                      self._current_class, tpl)
                self._object_items[item] = point
                self._activate_object(item, self._current_class, True)
            self._update_class_table()


    def _on_dbl_clk(self, point):
        items = self._image_viewer.items(point)
        print(items)

    def _get_object_item(self, point):
        scene = self._image_viewer.scene()
        item = scene.itemAt(point)
        if isinstance(item, MyItem):
            found_item = item
        elif isinstance(item.parentItem(), MyItem):
            found_item = item.parentItem()
        else:
            found_item = None
        return found_item

    def _activate_object(self, item, class_name, state=True):
        pen = item.pen()
        color = \
            QColor(*hexToRgb(self._learner.dctHexColors[class_name]))
        pen.setColor(color if state else Qt.white)
        item.setPen(pen)

        scene = self._image_viewer.scene()
        if state:
            rect = item.boundingRect()
            label = self._learner.dctClassLabels[class_name]
            item2 = QGraphicsSimpleTextItem(str(label), item)
            item2.setPos(rect.x()+rect.width()/2., rect.y()+rect.height()/2)
            item2.setPen(QPen(color))
            item2.setBrush(QBrush(color))
            item2.show()
        else:
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
        self._detect_objects = state
        self._process_image()

    def _on_time_changed(self, time):
        self._time = time
        self._t_label.setText('t=%d' % self._time)
        self._process_image()

    def _on_position_changed(self, current, previous):
        row_idx = current.row()
        self._position = self._meta_data.positions[row_idx]
        self._process_image()

    def _on_shortcut_left(self):
        self._t_slider.setValue(self._t_slider.value()-1)

    def _on_shortcut_right(self):
        self._t_slider.setValue(self._t_slider.value()+1)

    def _on_shortcut_up(self):
        pass

    def _on_shortcut_down(self):
        pass

    def _on_shortcut_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
        self.raise_()

    def _on_shortcut_antialiasing(self, checked):
        self._image_viewer.setRenderHint(QPainter.Antialiasing, checked)
        self._image_viewer.update()

    def _on_shortcut_smoothtransform(self, checked):
        self._image_viewer.setRenderHint(QPainter.SmoothPixmapTransform,
                                         checked)
        self._image_viewer.update()

    def _on_shortcut_autoresize(self, state):
        self._image_viewer.set_auto_resize(state)
        if state:
            self._zoom_value = self._image_viewer.scale_to_fit()

    def _on_shortcut_zoom100(self):
        self._image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self._image_viewer.scale_reset()

    def _on_shortcut_zoomfit(self):
        self._image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self._zoom_value = self._image_viewer.scale_to_fit()

    def _on_shortcut_zoomin(self):
        self._image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self._image_viewer.scale_relative(self.ZOOM_STEP, ensure_fit=False)

    def _on_shortcut_zoomout(self):
        self._image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self._image_viewer.scale_relative(1/self.ZOOM_STEP, ensure_fit=True)

    def _on_shortcut_transform(self, checked):
        if checked:
            self._image_viewer.set_scale_transform(Qt.FastTransformation)
        else:
            self._image_viewer.set_scale_transform(Qt.SmoothTransformation)
        self._process_image()

    def _on_shortcut_class_selected(self, class_label):
        items = self._find_items_in_class_table(str(class_label),
                                                self.COLUMN_CLASS_LABEL)
        if len(items) == 1:
            self._class_table.setCurrentItem(items[0])


    def _process_image(self):
        self._stopwatch.reset()
        s = StopWatch()
        settings = _ProcessorMixin.get_special_settings(self._settings)
        settings.set_section('General')
        settings.set2('constrain_positions', True)
        settings.set2('positions', str(self._position))
        settings.set2('framerange', True)
        settings.set2('framerange_begin', self._time)
        settings.set2('framerange_end', self._time)

        settings.set_section('ObjectDetection')
        prim_id = PrimaryChannel.NAME
        #sec_id = SecondaryChannel.NAME
        #sec_regions = settings.get2('secondary_regions')
        settings.set_section('Processing')
        settings.set2('primary_classification', False)
        settings.set2('secondary_classification', False)
        settings.set2('primary_featureextraction', False)
        settings.set2('secondary_featureextraction', False)
        settings.set2('objectdetection', self._detect_objects)
        settings.set2('tracking', False)
        settings.set_section('Output')
        settings.set2('rendering_contours_discwrite', False)
        settings.set2('rendering_class_discwrite', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        settings.set('Processing', 'secondary_processChannel', False)
        show_ids = False
        settings.set('General', 'rendering', {'primary_contours': {prim_id: {'raw': ('#FFFFFF', 1.0),
                                                                             #'contours': {'primary': ('#FF0000', 1, show_ids)}
                                                                             }}})

        analyzer = AnalyzerCore(settings,
                                imagecontainer=self._imagecontainer)
        analyzer.processPositions(myhack=self)
        print('PROCESS IMAGE: %s' % s)

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


    def keyPressEvent(self, ev):
        QMainWindow.keyPressEvent(self, ev)
        # allow to return from fullscreen via the Escape key
        if self.isFullScreen() and ev.key() == Qt.Key_Escape:
            self.showNormal()
            self._act_fullscreen.setChecked(False)
            self.raise_()

    def gestureEvent(self, ev):
        # determine whether a swipe gesture was detected
        if not ev.gesture(Qt.SwipeGesture) is None:
            gesture = ev.gesture(Qt.SwipeGesture)
            if gesture.state() == Qt.GestureFinished:
                if gesture.horizontalDirection() == QSwipeGesture.Left:
                    self._on_shortcut_left()
                elif gesture.horizontalDirection() == QSwipeGesture.Right:
                    self._on_shortcut_right()
                elif gesture.horizontalDirection() == QSwipeGesture.Up:
                    self._on_shortcut_up()
                elif gesture.horizontalDirection() == QSwipeGesture.Down:
                    self._on_shortcut_down()
        # or a pinch gesture was detected
        elif not ev.gesture(Qt.PinchGesture) is None:
            gesture = ev.gesture(Qt.PinchGesture)
            if gesture.state() == Qt.GestureStarted:
                self._image_viewer.setTransformationAnchor(
                    ImageViewer.AnchorUnderMouse)
            f = gesture.scaleFactor()
            if f != 1.0:
                self._image_viewer.scale_relative(math.sqrt(f), ensure_fit=True,
                                                  small_only=True)
                self._image_viewer.set_auto_resize(False)
                self._act_resize.setChecked(False)

            if gesture.state() in [Qt.GestureCanceled, Qt.GestureFinished]:
                self._image_viewer.setTransformationAnchor(
                    ImageViewer.AnchorViewCenter)
        return True

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            return self.gestureEvent(ev)
        return QWidget.event(self, ev)
