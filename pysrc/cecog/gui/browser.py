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

from cecog.gui.navigation import Navigation
from cecog.gui.channel import Channel
from cecog.gui.annotation import Annotation
#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#



@singleton
class Browser(QMainWindow):

    ZOOM_STEP = 1.05

    def __init__(self, settings, imagecontainer):
        QMainWindow.__init__(self)

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._stopwatch = StopWatch()

        self._settings = settings
        self._imagecontainer = imagecontainer
        self._meta_data = self._imagecontainer.meta_data


        self.grabGesture(Qt.PinchGesture)
        self.grabGesture(Qt.SwipeGesture)

        # setup the main menu

#        act_new = self.create_action('New Classifier...',
#                                     shortcut=QKeySequence.New,
#                                     slot=self._on_new_classifier)
#        act_open = self.create_action('Open Classifier...',
#                                      shortcut=QKeySequence.Open,
#                                      slot=self._on_open_classifier)
##        act_save = self.create_action('Save Classifier...',
##                                      shortcut=QKeySequence.Save,
##                                      slot=self._on_save_classifier)
#        act_saveas = self.create_action('Save Classifier As...',
#                                        shortcut=QKeySequence.SaveAs,
#                                        slot=self._on_saveas_classifier)
#        file_menu = self.menuBar().addMenu('&File')
#        self.add_actions(file_menu, (act_new, act_open, None,
#                                     #act_save,
#                                     act_saveas,
#                                     ))
#
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

#        class_fct = lambda id: lambda : self._on_shortcut_class_selected(id)
#        act_class = \
#            [self.create_action(
#                'Select Class Label %d' % x,
#                 shortcut=QKeySequence(str(x) if x < 10 else '0'),
#                 slot=class_fct(x))
#             for x in range(1,11)]
#        menu = self.menuBar().addMenu('&Annotation')
#        self.add_actions(menu, act_class)

        self._statusbar = QStatusBar(self)
        self.setStatusBar(self._statusbar)


        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0,0,0,0)

        splitter = QSplitter(Qt.Horizontal, frame)
        #splitter.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
        #                                   QSizePolicy.Expanding))
        layout.addWidget(splitter)

        frame = QFrame(self)
        self._frame_side = QStackedWidget(splitter)
        #splitter.setChildrenCollapsible(False)
        splitter.addWidget(frame)
        splitter.addWidget(self._frame_side)
        splitter.setStretchFactor(0,1)
        splitter.setStretchFactor(1,0)
        splitter.setSizes([None,80])

        #self._frame_side.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
        #                                           QSizePolicy.Expanding))


        self._plateid = ''
        self._channel = ''

        layout = QGridLayout(frame)
        layout.setContentsMargins(0,0,0,0)
        self.image_viewer = ImageViewer(frame, auto_resize=True)
        self.image_viewer.setTransformationAnchor(ImageViewer.AnchorViewCenter)
        self.image_viewer.setResizeAnchor(ImageViewer.AnchorViewCenter)
        self.image_viewer.setRenderHints(QPainter.Antialiasing |
                                          QPainter.SmoothPixmapTransform)
        self.image_viewer.setViewportUpdateMode(ImageViewer.SmartViewportUpdate)
        self.image_viewer.setBackgroundBrush(QBrush(QColor('#666666')))
        layout.addWidget(self.image_viewer, 0, 0)

        #self.image_viewer.image_mouse_dblclk.connect(self._on_dbl_clk)
        self.image_viewer.zoom_info_updated.connect(self._on_zoom_info_updated)

        self._t_slider = QSlider(Qt.Horizontal, frame)
        self._t_slider.setMinimum(self._meta_data.times[0])
        self._t_slider.setMaximum(self._meta_data.times[-1])
        self._t_slider.setTickPosition(QSlider.TicksBelow)
        self._t_slider.valueChanged.connect(self._on_time_changed,
                                            Qt.DirectConnection)
        layout.addWidget(self._t_slider, 1, 0)

        self._position = None
        self._time = self._t_slider.minimum()


        # tool bar

        self._toolbar = self.addToolBar('Toolbar')
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self._toolbar_grp = QButtonGroup(self._toolbar)
        self._toolbar_grp.setExclusive(True)

        self._tabs = {}
        self._register_tab(Navigation(self._frame_side, self,
                                      self._meta_data))
        self._register_tab(Channel(self._frame_side, self,
                                   self._meta_data))
        self._register_tab(Annotation(self._frame_side, self,
                                      self._settings, self._imagecontainer))

        self._activate_tab(Navigation.NAME)

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


        # ensure a valid position (not None!)
        #table.setCurrentCell(0, 0)
        #self._class_table.setCurrentCell(0, 0)

    def _register_tab(self, widget):
        idx = len(self._tabs)
        name = widget.NAME
        btn = QPushButton(name, self._toolbar)
        btn.toggled.connect(lambda x: self._on_tab_changed(name))
        btn.setFlat(True)
        btn.setCheckable(True)
        self._toolbar.addWidget(btn)
        self._toolbar_grp.addButton(btn, idx)
        self._frame_side.addWidget(widget)
        self._tabs[name] = (widget, idx)

    def _activate_tab(self, name):
        widget, idx = self._tabs[name]
        btn = self._toolbar_grp.button(idx)
        btn.setChecked(True)
        widget.activate()

    def _on_tab_changed(self, name):
        self._frame_side.setCurrentWidget(self.get_tab_widget(name))

    def get_tab_widget(self, name):
        return self._tabs[name][0]

    def _on_zoom_info_updated(self, info):
        self.update_statusbar()

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
            self.connect(action, SIGNAL(signal), slot, Qt.DirectConnection)
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

    def set_coords(self, coords):
        self.image_viewer.remove_objects()
        self.image_viewer.set_objects_by_crackcoords(coords)
        widget = self.get_tab_widget(Annotation.NAME)
        widget.set_coords()

    def set_image(self, image_dict):
        widget = self.get_tab_widget(Channel.NAME)
        widget.set_image_dict(image_dict)
        self.update_statusbar()

    def _on_time_changed(self, time):
        self._time = time
        self._process_image()

    def on_position_changed(self, position):
        position = str(position)
        assert position in self._meta_data.positions, "Position not valid"
        self._position = position
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
        self.image_viewer.setRenderHint(QPainter.Antialiasing, checked)
        self.image_viewer.update()

    def _on_shortcut_smoothtransform(self, checked):
        self.image_viewer.setRenderHint(QPainter.SmoothPixmapTransform,
                                         checked)
        self.image_viewer.update()

    def _on_shortcut_autoresize(self, state):
        self.image_viewer.set_auto_resize(state)
        if state:
            self.image_viewer.scale_to_fit()

    def _on_shortcut_zoom100(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_reset()

    def _on_shortcut_zoomfit(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_to_fit()

    def _on_shortcut_zoomin(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(self.ZOOM_STEP, ensure_fit=False)

    def _on_shortcut_zoomout(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(1/self.ZOOM_STEP, ensure_fit=True)

    def _on_shortcut_transform(self, checked):
        if checked:
            self.image_viewer.set_scale_transform(Qt.FastTransformation)
        else:
            self.image_viewer.set_scale_transform(Qt.SmoothTransformation)
        self._process_image()

    def _on_shortcut_class_selected(self, class_label):
        items = self._find_items_in_class_table(str(class_label),
                                                self.COLUMN_CLASS_LABEL)
        if len(items) == 1:
            self._class_table.setCurrentItem(items[0])

    def update_statusbar(self):
        timestamp = self._meta_data.get_timestamp_relative(self._position,
                                                           self._time)
        time_info = str(self._time)
        if not numpy.isnan(timestamp):
            time_info += ' (%.1f min)' % (timestamp / 60)
        msg = 'Plate %s | Position %s | Frame %s  ||  Zoom %.1f%%' % \
              (self._plateid, self._position, time_info,
               self.image_viewer.scale_factor*100)
        self._statusbar.showMessage(msg)

    def get_coordinates(self):
        return self._plateid, self._position, self._time

    def _process_image(self):
        self._stopwatch.reset()
        s = StopWatch()
        settings = _ProcessorMixin.get_special_settings(self._settings)
        settings.set_section('General')
        settings.set2('constrain_positions', True)
        settings.set2('positions', self._position)
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

        # FIXME: just interim solution
        widget = self._tabs[Annotation.NAME][0]
        settings.set2('objectdetection', widget._detect_objects)
        settings.set2('tracking', False)
        settings.set_section('Output')
        settings.set2('rendering_contours_discwrite', False)
        settings.set2('rendering_class_discwrite', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        settings.set('Processing', 'secondary_processChannel', True)
        settings.set('General', 'rendering', {})

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

    # Qt method overwrites

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
                self.image_viewer.setTransformationAnchor(
                    ImageViewer.AnchorUnderMouse)
            f = gesture.scaleFactor()
            if f != 1.0:
                self.image_viewer.scale_relative(math.sqrt(f), ensure_fit=True,
                                                  small_only=True)
                self.image_viewer.set_auto_resize(False)
                self._act_resize.setChecked(False)

            if gesture.state() in [Qt.GestureCanceled, Qt.GestureFinished]:
                self.image_viewer.setTransformationAnchor(
                    ImageViewer.AnchorViewCenter)
        return True

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            return self.gestureEvent(ev)
        return QWidget.event(self, ev)
