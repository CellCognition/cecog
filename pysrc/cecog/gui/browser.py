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
import math
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.datetimeutils import StopWatch

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
from cecog.gui.modules.module import ModuleManager
from cecog.gui.analyzer import _ProcessorMixin
from cecog.analyzer.channel import (PrimaryChannel,
                                    SecondaryChannel,
                                    TertiaryChannel,
                                    )
from cecog.analyzer import REGION_NAMES_SECONDARY
from cecog.analyzer.core import AnalyzerCore
from cecog import ccore
from cecog.util.util import (hexToRgb,
                             convert_package_path,
                             singleton,
                             )
from cecog.learning.learning import BaseLearner
from cecog.gui.widgets.groupbox import QxtGroupBox

from cecog.gui.modules.navigation import NavigationModule
from cecog.gui.modules.display import DisplayModule
from cecog.gui.modules.annotation import AnnotationModule
#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#



#@singleton
class Browser(QMainWindow):

    ZOOM_STEP = 1.05

    show_objects_toggled = pyqtSignal('bool')
    show_contours_toggled = pyqtSignal('bool')
    coordinates_changed = pyqtSignal(str, str, int)

    def __init__(self, settings, imagecontainer):
        QMainWindow.__init__(self)

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._stopwatch = StopWatch()

        self._settings = settings
        self._imagecontainer = imagecontainer
        self.meta_data = self._imagecontainer.meta_data
        self._show_objects = False
        self._object_region = None

        self.grabGesture(Qt.SwipeGesture)

        self.setStyleSheet(
"""
  QStatusBar { border-top: 1px solid gray; }
""")


        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal, frame)
        #splitter.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
        #                                   QSizePolicy.Expanding))
        layout.addWidget(splitter)

        frame = QFrame(self)
        frame_side = QStackedWidget(splitter)
        #splitter.setChildrenCollapsible(False)
        splitter.addWidget(frame)
        splitter.addWidget(frame_side)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([None, 80])

        self._plateid = ''
        self._channel = ''

        layout = QGridLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_viewer = ImageViewer(frame, auto_resize=True)
        layout.addWidget(self.image_viewer, 0, 0)

        #self.image_viewer.image_mouse_dblclk.connect(self._on_dbl_clk)
        self.image_viewer.zoom_info_updated.connect(self.on_zoom_info_updated)

        self._t_slider = QSlider(Qt.Horizontal, frame)
        self._t_slider.setMinimum(self.meta_data.times[0])
        self._t_slider.setMaximum(self.meta_data.times[-1])
        self._t_slider.setTickPosition(QSlider.TicksBelow)
        self._t_slider.valueChanged.connect(self.on_time_changed,
                                            Qt.DirectConnection)
        layout.addWidget(self._t_slider, 1, 0)

        self._position = None
        self._time = self._t_slider.minimum()

        # menus

        act_next_t = self.create_action('Next Time-point',
                                        shortcut=QKeySequence('Right'),
                                        slot=self.on_shortcut_right)
        act_prev_t = self.create_action('Previous Time-point',
                                        shortcut=QKeySequence('Left'),
                                        slot=self.on_shortcut_left)
        act_resize = self.create_action('Automatically Resize',
                                         shortcut=QKeySequence('SHIFT+CTRL+R'),
                                         slot=self.on_shortcut_autoresize,
                                         signal='triggered(bool)',
                                         checkable=True,
                                         checked=True)
        self._act_resize = act_resize
        act_zoomfit = self.create_action('Zoom to Fit',
                                         shortcut=QKeySequence('CTRL+0'),
                                         slot=self.on_shortcut_zoomfit)
        act_zoom100 = self.create_action('Actual Size',
                                         shortcut=QKeySequence('CTRL+1'),
                                         slot=self.on_shortcut_zoom100)
        act_zoomin = self.create_action('Zoom In',
                                        shortcut=QKeySequence('CTRL++'),
                                        slot=self.on_shortcut_zoomin)
        act_zoomout = self.create_action('Zoom Out',
                                         shortcut=QKeySequence('CTRL+-'),
                                         slot=self.on_shortcut_zoomout)
        act_fullscreen = self.create_action('Full Screen',
                                            shortcut=QKeySequence('CTRL+F'),
                                            slot=self.on_shortcut_fullscreen,
                                            signal='triggered(bool)',
                                            checkable=True,
                                            checked=False)
        self._act_fullscreen = act_fullscreen

        act_show_contours = self.create_action('Show Object Contours',
                                               shortcut=QKeySequence('ALT+C'),
                                               slot=self.on_shortcut_show_contours,
                                               signal='triggered(bool)',
                                               checkable=True,
                                               checked=self.image_viewer.show_contours)
        self._act_show_contours = act_show_contours

        act_anti = self.create_action('Antialiasing',
                                      shortcut=QKeySequence('CTRL+ALT+A'),
                                      slot=self.on_shortcut_antialiasing,
                                      signal='triggered(bool)',
                                      checkable=True,
                                      checked=True)
        act_smooth = self.create_action('Smooth Transform',
                                        shortcut=QKeySequence('CTRL+ALT+S'),
                                        slot=self.on_shortcut_smoothtransform,
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
                                     act_show_contours, None,
                                     act_anti, act_smooth,
                                     ))

        self._statusbar = QStatusBar(self)
        self.setStatusBar(self._statusbar)


        # tool bar

        toolbar = self.addToolBar('Toolbar')
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        region_names = ['Primary - primary']
        self._settings.set_section('ObjectDetection')
        for prefix in ['secondary', 'tertiary']:
            if self._settings.get('Processing', '%s_processchannel' % prefix):
                for name in REGION_NAMES_SECONDARY:
                    if self._settings.get2('%s_regions_%s' % (prefix, name)):
                        region_names.append('%s - %s' % (prefix.capitalize(), name))

        # FIXME: something went wrong with setting up the current region
        self._object_region = region_names[0].split(' - ')


        # create a new ModuleManager with a QToolbar and QStackedFrame
        self._module_manager = ModuleManager(toolbar, frame_side)

        NavigationModule(self._module_manager, self, self.meta_data)

        DisplayModule(self._module_manager, self, self.meta_data, region_names)

        AnnotationModule(self._module_manager, self, self._settings,
                         self._imagecontainer)

        self._module_manager.activate_tab(NavigationModule.NAME)


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
        widget = self._module_manager.get_widget(AnnotationModule.NAME)
        widget.set_coords()

    def set_image(self, image_dict):
        widget = self._module_manager.get_widget(DisplayModule.NAME)
        widget.set_image_dict(image_dict)
        self.update_statusbar()

    def update_statusbar(self):
        timestamp = self.meta_data.get_timestamp_relative(self._position,
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

    def set_coordinates(self, plateid, position, time):
        self._plateid = plateid
        self._position = position
        self._time = time
        self._t_slider.blockSignals(True)
        self._t_slider.setValue(time)
        self._t_slider.blockSignals(False)
        self._process_image()
        self.coordinates_changed.emit(plateid, position, time)

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

        settings.set2('objectdetection', self._show_objects)
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

    # slots

    def on_zoom_info_updated(self, info):
        self.update_statusbar()

    def on_time_changed(self, time):
        self._time = time
        self._process_image()
        self.coordinates_changed.emit(self._plateid, self._position, time)

    def on_position_changed(self, position):
        position = str(position)
        assert position in self.meta_data.positions, "Position not valid"
        self._position = position
        self._process_image()

    def on_object_region_changed(self, channel, region):
        self._object_region = channel, region
        self._process_image()

    def on_shortcut_left(self):
        self._t_slider.setValue(self._t_slider.value()-1)

    def on_shortcut_right(self):
        self._t_slider.setValue(self._t_slider.value()+1)

    def on_shortcut_up(self):
        pass

    def on_shortcut_down(self):
        pass

    def on_shortcut_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
        self.raise_()

    def on_shortcut_show_contours(self, checked):
        self._act_show_contours.blockSignals(True)
        self._act_show_contours.setChecked(checked)
        self._act_show_contours.blockSignals(False)
        self.image_viewer.set_show_contours(checked)
        self.show_contours_toggled.emit(checked)

    def on_shortcut_antialiasing(self, checked):
        self.image_viewer.setRenderHint(QPainter.Antialiasing, checked)
        self.image_viewer.update()

    def on_shortcut_smoothtransform(self, checked):
        self.image_viewer.setRenderHint(QPainter.SmoothPixmapTransform,
                                         checked)
        self.image_viewer.update()

    def on_shortcut_autoresize(self, state):
        self.image_viewer.set_auto_resize(state)
        if state:
            self.image_viewer.scale_to_fit()

    def on_shortcut_zoom100(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_reset()

    def on_shortcut_zoomfit(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_to_fit()

    def on_shortcut_zoomin(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(self.ZOOM_STEP, ensure_fit=False)

    def on_shortcut_zoomout(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(1/self.ZOOM_STEP, ensure_fit=True)

    def on_shortcut_transform(self, checked):
        if checked:
            self.image_viewer.set_scale_transform(Qt.FastTransformation)
        else:
            self.image_viewer.set_scale_transform(Qt.SmoothTransformation)
        self._process_image()

    def on_shortcut_class_selected(self, class_label):
        items = self._find_items_in_class_table(str(class_label),
                                                self.COLUMN_CLASS_LABEL)
        if len(items) == 1:
            self._class_table.setCurrentItem(items[0])

    def on_show_objects(self, state):
        self._show_objects = state
        self.image_viewer.remove_objects()
        self._process_image()
        self.show_objects_toggled.emit(state)

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
        return True

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            return self.gestureEvent(ev)
        return QWidget.event(self, ev)
