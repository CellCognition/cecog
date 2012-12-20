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
from cecog.traits.config import convert_package_path
from cecog.io.imagecontainer import Coordinate
from cecog.learning.learning import BaseLearner
from cecog.gui.widgets.groupbox import QxtGroupBox

from cecog.gui.modules.navigation import NavigationModule
from cecog.gui.modules.display import DisplayModule
from cecog.gui.modules.annotation import AnnotationModule
from cecog.gui.modules.tracking import TrackingModule
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

    show_objects_toggled = pyqtSignal('bool')
    show_contours_toggled = pyqtSignal('bool')
    coordinates_changed = pyqtSignal(Coordinate)

    def __init__(self, settings, imagecontainer):
        super(Browser, self).__init__()

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._settings = settings
        self._imagecontainer = imagecontainer
        self._show_objects = False
        self._object_region = None

        self.coordinate = Coordinate()

        self.grabGesture(Qt.SwipeGesture)

        self.setStyleSheet("QStatusBar { border-top: 1px solid gray; }")


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
        splitter.setSizes([-1, 80])

        self.coordinate.plate = self._imagecontainer.plates[0]
        self._imagecontainer.set_plate(self.coordinate.plate)

        self.coordinate.channel = self._imagecontainer.channels[0]

        meta_data = self._imagecontainer.get_meta_data()
        self.max_time = meta_data.times[-1]
        self.min_time = meta_data.times[0]
        self.max_frame = meta_data.dim_t-1

        layout = QGridLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_viewer = ImageViewer(frame, auto_resize=True)
        layout.addWidget(self.image_viewer, 0, 0)

        #self.image_viewer.image_mouse_dblclk.connect(self._on_dbl_clk)
        self.image_viewer.zoom_info_updated.connect(self.on_zoom_info_updated)

        self._t_slider = QSlider(Qt.Horizontal, frame)
        self._t_slider.setMinimum(self.min_time)
        self._t_slider.setMaximum(self.max_frame)

        self._t_slider.setTickPosition(QSlider.TicksBelow)
        self._t_slider.valueChanged.connect(self.on_time_changed_by_slider,
                                            Qt.DirectConnection)
        if self._imagecontainer.has_timelapse:
            self._t_slider.show()
        else:
            self._t_slider.hide()
        layout.addWidget(self._t_slider, 1, 0)

        self.coordinate.position = meta_data.positions[0]
        self.coordinate.time = self._t_slider.minimum()

        # menus

        act_next_t = self.create_action('Next Time-point',
                                        shortcut=QKeySequence('Right'),
                                        slot=self.on_act_next_t)
        act_prev_t = self.create_action('Previous Time-point',
                                        shortcut=QKeySequence('Left'),
                                        slot=self.on_act_prev_t)
        act_next_pos = self.create_action('Next Position',
                                          shortcut=QKeySequence('Shift+Down'),
                                          slot=self.on_act_next_pos)
        act_prev_pos = self.create_action('Previous Position',
                                          shortcut=QKeySequence('Shift+Up'),
                                          slot=self.on_act_prev_pos)
        act_next_plate = self.create_action('Next Plate',
                                            shortcut=QKeySequence('Shift+Alt+Down'),
                                            slot=self.on_act_next_plate)
        act_prev_plate = self.create_action('Previous Plate',
                                            shortcut=QKeySequence('Shift+Alt+Up'),
                                            slot=self.on_act_prev_plate)
        act_resize = self.create_action('Automatically Resize',
                                         shortcut=QKeySequence('SHIFT+CTRL+R'),
                                         slot=self.on_act_autoresize,
                                         signal='triggered(bool)',
                                         checkable=True,
                                         checked=True)
        self._act_resize = act_resize
        act_zoomfit = self.create_action('Zoom to Fit',
                                         shortcut=QKeySequence('CTRL+0'),
                                         slot=self.on_act_zoomfit)
        act_zoom100 = self.create_action('Actual Size',
                                         shortcut=QKeySequence('CTRL+1'),
                                         slot=self.on_act_zoom100)
        act_zoomin = self.create_action('Zoom In',
                                        shortcut=QKeySequence('CTRL++'),
                                        slot=self.on_act_zoomin)
        act_zoomout = self.create_action('Zoom Out',
                                         shortcut=QKeySequence('CTRL+-'),
                                         slot=self.on_act_zoomout)
        act_refresh = self.create_action('Refresh',
                                         shortcut=QKeySequence('F5'),
                                         slot=self.on_refresh)

        act_fullscreen = self.create_action('Full Screen',
                                            shortcut=QKeySequence('CTRL+F'),
                                            slot=self.on_act_fullscreen,
                                            signal='triggered(bool)',
                                            checkable=True,
                                            checked=False)
        self._act_fullscreen = act_fullscreen

        act_show_contours = self.create_action('Show Object Contours',
                                               shortcut=QKeySequence('ALT+C'),
                                               slot=self.on_act_show_contours,
                                               signal='triggered(bool)',
                                               checkable=True,
                                               checked=self.image_viewer.show_contours)
        self._act_show_contours = act_show_contours

        act_anti = self.create_action('Antialiasing',
                                      shortcut=QKeySequence('CTRL+ALT+A'),
                                      slot=self.on_act_antialiasing,
                                      signal='triggered(bool)',
                                      checkable=True,
                                      checked=True)
        act_smooth = self.create_action('Smooth Transform',
                                        shortcut=QKeySequence('CTRL+ALT+S'),
                                        slot=self.on_act_smoothtransform,
                                        signal='triggered(bool)',
                                        checkable=True,
                                        checked=True)
        view_menu = self.menuBar().addMenu('&View')

        self.add_actions(view_menu, (act_resize, None,
                                     act_zoom100, act_zoomfit,
                                     act_zoomin, act_zoomout,
                                     None,
                                     act_prev_t, act_next_t,
                                     act_prev_pos, act_next_pos,
                                     act_prev_plate, act_next_plate,
                                     None,
                                     act_refresh,
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
                        region_names.append('%s - %s' % (prefix.capitalize(),
                                                         name))

        # FIXME: something went wrong with setting up the current region
        self._object_region = region_names[0].split(' - ')


        # create a new ModuleManager with a QToolbar and QStackedFrame
        self._module_manager = ModuleManager(toolbar, frame_side)

        NavigationModule(self._module_manager, self, self._imagecontainer)

        DisplayModule(self._module_manager, self, self._imagecontainer,
                      region_names)

        TrackingModule(self._module_manager, self, self._settings,
                         self._imagecontainer)

        AnnotationModule(self._module_manager, self, self._settings,
                         self._imagecontainer)

        # set the Navigation module activated
        self._module_manager.activate_tab(NavigationModule.NAME)

        # process and display the first image
        self._process_image()


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
        widget = self._module_manager.get_widget(TrackingModule.NAME)
        widget.set_coords()

    def set_image(self, image_dict):
        widget = self._module_manager.get_widget(DisplayModule.NAME)
        widget.set_image_dict(image_dict)
        self.update_statusbar()

    def update_statusbar(self):
        meta_data = self._imagecontainer.get_meta_data()
        if meta_data.has_timelapse:
            timestamp = meta_data.get_timestamp_relative(self.coordinate)
            time_info = ' | Frame: %d' % self.coordinate.time

            if not numpy.isnan(timestamp):
                time_info += ' (%.1f min)' % (timestamp / 60)
        else:
            time_info = ''
        msg = 'Plate: %s | Position: %s%s ||  Zoom: %.1f%%' % \
              (self.coordinate.plate, self.coordinate.position, time_info,
               self.image_viewer.scale_factor*100)
        self._statusbar.showMessage(msg)

    def get_coordinate(self):
        return self.coordinate.copy()

    def on_coordinate_changed(self, coordinate):
        """
        All coordinate changes are handled via the Navigator. The change event
        from the Navigator is processed here and further propagated via
        a new Browser event (the Modules are not supposed to know each other).
        """

        self.coordinate = coordinate.copy()
        self._t_slider.blockSignals(True)
        self._imagecontainer.set_plate(coordinate.plate)

        # the slider is always working with frames.
        # reason: it is difficult to forbid slider values between allowed values.
        frame = int(round(
                          self.max_frame * (coordinate.time - self.min_time) /
                          float(self.max_time - self.min_time)
                          )
                    )

        self._t_slider.setValue(frame)

        self._t_slider.blockSignals(False)
        self._process_image()
        # propagate the signal further to other modules
        self.coordinates_changed.emit(coordinate)

    def set_coordinate(self, coordinate):
        """
        Changes the Navigator to a fixed coordinate
        """
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_coordinate(coordinate)

    def _process_image(self):
        settings = _ProcessorMixin.get_special_settings(self._settings)
        settings.set_section('General')
        settings.set2('constrain_positions', True)
        settings.set2('positions', self.coordinate.position)
        settings.set2('redofailedonly', False)
        settings.set2('framerange', True)
        settings.set2('framerange_begin', self.coordinate.time)
        settings.set2('framerange_end', self.coordinate.time)

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
        settings.set2('export_object_counts', False)
        settings.set2('export_object_details', False)
        settings.set2('export_track_data', False)
        settings.set2('hdf5_create_file', False)
        settings.set_section('Classification')
        settings.set2('collectsamples', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})
        settings.set('Output', 'events_export_gallery_images', False)

        pr = self._imagecontainer.get_meta_data().pixel_range
        #settings.set('ObjectDetection', 'primary_normalizemax', pr[1])
        #settings.set('ObjectDetection', 'primary_normalizemin', pr[0])
        #settings.set('ObjectDetection', 'secondary_normalizemax', pr[1])
        #settings.set('ObjectDetection', 'secondary_normalizemin', pr[0])

        if len(self._imagecontainer.channels) > 1:
            settings.set('Processing', 'secondary_processChannel', True)
        settings.set('General', 'rendering', {})
        analyzer = AnalyzerCore(self.coordinate.plate, settings,
                                self._imagecontainer)
        analyzer.processPositions(myhack=self)

    def on_refresh(self):
        self._process_image()

    def on_zoom_info_updated(self, info):
        self.update_statusbar()

    def on_time_changed_by_slider(self, frame):
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        meta_data = self._imagecontainer.get_meta_data()
        time = meta_data.times[frame]
        nav.nav_to_time(time)

    def on_object_region_changed(self, channel, region):
        self._object_region = channel, region
        self._process_image()

    def on_act_prev_t(self):
        self._t_slider.setValue(self._t_slider.value()-1)

    def on_act_next_t(self):
        self._t_slider.setValue(self._t_slider.value()+1)

    def on_act_prev_pos(self):
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_prev_position()

    def on_act_next_pos(self):
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_next_position()

    def on_act_prev_plate(self):
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_prev_plate()

    def on_act_next_plate(self):
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_next_plate()

    def on_act_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()
        self.raise_()

    def on_act_show_contours(self, checked):
        self._act_show_contours.blockSignals(True)
        self._act_show_contours.setChecked(checked)
        self._act_show_contours.blockSignals(False)
        self.image_viewer.set_show_contours(checked)
        self.show_contours_toggled.emit(checked)

    def on_act_antialiasing(self, checked):
        self.image_viewer.setRenderHint(QPainter.Antialiasing, checked)
        self.image_viewer.update()

    def on_act_smoothtransform(self, checked):
        self.image_viewer.setRenderHint(QPainter.SmoothPixmapTransform,
                                         checked)
        self.image_viewer.update()

    def on_act_autoresize(self, state):
        self.image_viewer.set_auto_resize(state)
        if state:
            self.image_viewer.scale_to_fit()

    def on_act_zoom100(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_reset()

    def on_act_zoomfit(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_to_fit()

    def on_act_zoomin(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(self.ZOOM_STEP, ensure_fit=False)

    def on_act_zoomout(self):
        self.image_viewer.set_auto_resize(False)
        self._act_resize.setChecked(False)
        self.image_viewer.scale_relative(1/self.ZOOM_STEP, ensure_fit=True)

    def on_act_transform(self, checked):
        if checked:
            self.image_viewer.set_scale_transform(Qt.FastTransformation)
        else:
            self.image_viewer.set_scale_transform(Qt.SmoothTransformation)
        self._process_image()

    def on_act_class_selected(self, class_label):
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
        super(Browser, self).keyPressEvent(self, ev)
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
                    self._on_act_left()
                elif gesture.horizontalDirection() == QSwipeGesture.Right:
                    self._on_act_right()
                elif gesture.horizontalDirection() == QSwipeGesture.Up:
                    self._on_act_up()
                elif gesture.horizontalDirection() == QSwipeGesture.Down:
                    self._on_act_down()
        return True

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            return self.gestureEvent(ev)
        return QWidget.event(self, ev)
