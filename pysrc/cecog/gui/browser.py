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

__all__ = ['Browser']

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.datetimeutils import StopWatch

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import numpy_to_qimage
from cecog.gui.imageviewer import ImageViewer
from cecog.gui.analyzer import _ProcessorMixin
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class Browser(QMainWindow):

    ZOOM_STEP = 1.05

    def __init__(self, settings, imagecontainer):
        super(Browser, self).__init__()

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._zoom_value = 1.0

#        action_about = self.create_action('&About', slot=self._on_about)
#        action_quit = self.create_action('&Quit', slot=self._on_quit)
#        action_pref = self.create_action('&Preferences',
#                                         slot=self._on_preferences)
#
#        action_new = self.create_action('&New...', shortcut=QKeySequence.New,
#                                          icon='filenew')
#        action_open = self.create_action('&Open...',
#                                         shortcut=QKeySequence.Open,
#                                         slot=self._on_file_open)
#        file_menu = self.menuBar().addMenu('&File')
#        self.add_actions(file_menu, (action_about,  action_pref,
#                                     None, action_open,
#                                     None, action_quit))

        act_next_t = self.create_action('Next Time-point',
                                        shortcut=QKeySequence.SelectNextChar,
                                        slot=self._on_shortcut_right)
        act_prev_t = self.create_action('Previous Time-point',
                                        shortcut=QKeySequence.SelectPreviousChar,
                                        slot=self._on_shortcut_left)
        act_resize = self.create_action('Automatically Resize',
                                         shortcut=QKeySequence('SHIFT+CTRL+R'),
                                         slot=self._on_shortcut_autoresize,
                                         signal='triggered(bool)',
                                         checkable=True,
                                         checked=True)
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
        act_transform = self.create_action('Fast Display',
                                            shortcut=QKeySequence('CTRL+D'),
                                            slot=self._on_shortcut_transform,
                                            signal='triggered(bool)',
                                            checkable=True,
                                            checked=False)
        view_menu = self.menuBar().addMenu('&View')
        self.add_actions(view_menu, (act_resize, None,
                                     act_zoom100, act_zoomfit,
                                     act_zoomin, act_zoomout,
                                     None,
                                     act_prev_t, act_next_t, None,
                                     act_fullscreen, #None,
                                     #act_transform
                                     ))

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

        layout = QGridLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        self._image_viewer = ImageViewer(frame, auto_resize=True)
        self._image_viewer.image_mouse_pressed.connect(self._on_new_point)
        #self._image_viewer.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
        #                                             QSizePolicy.Expanding))
        layout.addWidget(self._image_viewer, 0, 0, 1, 2)

        self._t_slider = QSlider(Qt.Horizontal, frame)
        self._t_slider.setMinimum(self._meta_data.times[0])
        self._t_slider.setMaximum(self._meta_data.times[-1])
        self._t_slider.setTickPosition(QSlider.TicksBelow)
        self._t_slider.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self._t_slider, 1, 1)

        self._detect_objects = True

        self._position = None
        self._time = self._t_slider.minimum()

        self._t_label = QLabel('t=%d' % self._time, frame)
        self._t_label.setMinimumWidth(35)
        layout.addWidget(self._t_label, 1, 0)

        layout = QGridLayout(frame_side)
        box = QCheckBox('Detect objects', frame_side)
        box.setCheckState(Qt.Checked if self._detect_objects else Qt.Unchecked)
#        box.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        layout.addWidget(box, 0, 0)
        box.clicked.connect(self._on_detect_box)

        # ensure a valid position (not None!)
        table.setCurrentCell(0, 0)

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

    def set_image(self, image):
        s = StopWatch()
        print(image)
        if image.width % 4 != 0:
            image = ccore.subImage(image, ccore.Diff2D(0,0),
                                   ccore.Diff2D(image.width-(image.width % 4),
                                                image.height))
        qimage = numpy_to_qimage(image.toArray(copy=True))
        self._image_viewer.from_qimage(qimage)
        print('SET IMAGE: %s' % s)

    def _on_new_point(self, point):
        print(point)

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

    def _on_shortcut_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _on_shortcut_autoresize(self, state):
        self._image_viewer.set_auto_resize(state)

    def _on_shortcut_zoom100(self):
        #self._zoom_value = 1.0
        self._image_viewer.scale_reset()

    def _on_shortcut_zoomfit(self):
        self._zoom_value = self._image_viewer.scale_to_fit()

    def _on_shortcut_zoomin(self):
        self._image_viewer.scale_relative(self.ZOOM_STEP, ensure_fit=False)

    def _on_shortcut_zoomout(self):
        self._image_viewer.scale_relative(1/self.ZOOM_STEP, ensure_fit=True)

    def _on_shortcut_transform(self, checked):
        if checked:
            self._image_viewer.set_scale_transform(Qt.FastTransformation)
        else:
            self._image_viewer.set_scale_transform(Qt.SmoothTransformation)
        self._process_image()


    def _process_image(self):
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
                                                                             'contours': {'primary': ('#FF0000', 1, show_ids)}
                                                                             }}})

        analyzer = AnalyzerCore(settings,
                                imagecontainer=self._imagecontainer)
        analyzer.processPositions(myhack=self)
        print('PROCESS IMAGE: %s' % s)

