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

from collections import OrderedDict
import h5py
import numpy

try:
    from PyQt5 import sip
except ImportError:
    import sip

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from PyQt5 import QtWidgets

from cecog import version
from cecog.gui.analyzer import BaseProcessorFrame

from cecog.gui.imageviewer import ImageViewer, GalleryViewer
from cecog.gui.modules.module import ModuleManager

#from cecog.analyzer.plate import AnnotationBrowser
from cecog.io.imagecontainer import Coordinate
from cecog.gui.modules.navigation import NavigationModule
from cecog.gui.modules.display import DisplayModule
from cecog.gui.modules.annotation import AnnotationModule
from cecog.gui.modules.eventviewer import CellH5EventModule
from cecog.io.imagecontainer import ImageContainer
from cecog.gui.config import GuiConfigSettings
from cecog.plugin.metamanager import MetaPluginManager


class TSlider(QSlider):

    newValue = pyqtSignal()

    def mouseReleaseEvent(self, event):
        self.newValue.emit()
        super(TSlider, self).mouseReleaseEvent(event)


class Browser(QMainWindow):

    ZOOM_STEP = 1.05

    show_objects_toggled = pyqtSignal('bool')
    show_contours_toggled = pyqtSignal('bool')
    update_regions = pyqtSignal(dict)

    def __init__(self, settings, imagecontainer, parent=None):
        super(Browser, self).__init__(parent)
        self.setWindowTitle('Annotation Browser')

        frame = QFrame(self)
        self.setCentralWidget(frame)

        self._settings = settings
        self._imagecontainer = imagecontainer

        # These params are used by process_image and contour visualization
        self._detect_objects = False
        self._show_objects_by = 'color'
        self._object_region = None
        self._contour_color = '#000000'
        self._show_objects = True

        self.coordinate = Coordinate()

        self.grabGesture(Qt.SwipeGesture)

        self.setStyleSheet("QStatusBar { border-top: 1px solid gray; }")


        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal, frame)
        layout.addWidget(splitter)

        frame = QFrame(self)
        frame_side = QStackedWidget(splitter)
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
        self.image_viewers = {
                             'image'   : ImageViewer(frame, auto_resize=True),
                             'gallery' : GalleryViewer(frame)
                             }

        self.image_viewer = self.image_viewers['image']
        layout.addWidget(self.image_viewer , 0, 0)

        self.image_viewer.zoom_info_updated.connect(self.on_zoom_info_updated)

        self._t_slider = TSlider(Qt.Horizontal, frame)

        self._t_slider.setMinimum(self.min_time)
        self._t_slider.setMaximum(self.max_time)

        self._t_slider.setTickPosition(QSlider.NoTicks)
        self._t_slider.newValue.connect(self.on_time_changed_by_slider,
                                        Qt.DirectConnection)
        self._t_slider.valueChanged.connect(self.timeToolTip)
        self._imagecontainer.check_dimensions()

        if self._imagecontainer.has_timelapse:
            self._t_slider.show()
        else:
            self._t_slider.hide()
        layout.addWidget(self._t_slider, 1, 0)

        self.coordinate.position = meta_data.positions[0]
        self.coordinate.time = self._t_slider.minimum()

        # menus
        act_close = self.create_action('Close',
                                        shortcut=QKeySequence('CTRL+C'),
                                        slot=self.close)

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
        act_next_plate = self.create_action(
            'Next Plate', shortcut=QKeySequence('Shift+Alt+Down'),
                                            slot=self.on_act_next_plate)
        act_prev_plate = self.create_action(
            'Previous Plate', shortcut=QKeySequence('Shift+Alt+Up'),
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

        act_fullscreen = self.create_action(
            'Full Screen',
            shortcut=QKeySequence('CTRL+F'),
            slot=self.on_act_fullscreen,
            signal='triggered(bool)',
            checkable=True,
            checked=False
            )
        self._act_fullscreen = act_fullscreen

        act_show_contours = self.create_action(
            'Show Object Contours',
            shortcut=QKeySequence('ALT+C'),
            slot=self.on_act_show_contours,
            signal='triggered(bool)',
            checkable=True,
            checked=self.image_viewer.show_contours
            )
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
                                     None, act_close))

        self._statusbar = QStatusBar(self)
        self.setStatusBar(self._statusbar)

        toolbar = self.addToolBar('Toolbar')
        toolbar.setObjectName('Toolbar')
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        # fallback if no Segmentation plugins have been specified
        rdict = self._region_names()
        if len(rdict) > 0:
            self._object_region = rdict.keys()[0].split(' - ')
        else:
            self._object_region = ('Primary', 'primary')

        # create a new ModuleManager with a QToolbar and QStackedFrame
        self._module_manager = ModuleManager(toolbar, frame_side)

        NavigationModule(self._module_manager, self, self._imagecontainer)
        defautl_display_module = DisplayModule(
            self._module_manager, self, self._imagecontainer, rdict)

        self.set_display_module(defautl_display_module)
        AnnotationModule(self._module_manager, self, self._settings,
                         self._imagecontainer)

        try:
            CellH5EventModule(self._module_manager,
                              self, self._settings, self._imagecontainer)
        except Exception as e:
            QMessageBox.warning(self, "Warning", str(e))

        # set the Navigation module activated
        self._module_manager.activate_tab(NavigationModule.NAME)

        self.layout = layout
        # process and display the first image
        self._restore_geometry()
        self._process_image()

    def closeEvent(self, event):
        self._save_geometry()

    def _save_geometry(self):
        settings = QSettings(version.organisation, version.appname)
        settings.beginGroup('AnnotationBrowser')
        settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())
        settings.endGroup()

    def _restore_geometry(self):
        settings = QSettings(version.organisation, version.appname)
        settings.beginGroup('AnnotationBrowser')

        if settings.contains('geometry'):
            self.restoreGeometry(settings.value('geometry'))

        if settings.contains('state'):
            self.restoreState(settings.value('state'))
        settings.endGroup()

    def _region_names(self):

        rdict = OrderedDict()
        reginfo = MetaPluginManager().region_info
        for channel, regions in reginfo.names.iteritems():
            for region in regions:
                rdict['%s - %s' % (channel.capitalize(), region)] = \
                    (channel.capitalize(), region)
        return rdict

    def set_image_viewer(self, viewer_type):
        self.image_viewer.hide()
        self.layout.removeWidget(self.image_viewer)
        self.image_viewer = self.image_viewers[viewer_type]
        self.layout.addWidget(self.image_viewer, 0, 0)
        self.image_viewer.show()

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
            if signal == "triggered()":
                action.triggered.connect(slot, Qt.DirectConnection)
            else:
                action.triggered[bool].connect(slot, Qt.DirectConnection)
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
        self.image_viewer.set_objects_by_crackcoords(coords)
        widget = self._module_manager.get_widget(AnnotationModule.NAME)
        widget.set_coords()

    def set_classified_crack_contours(self, coords):
        self.image_viewer.set_objects_by_crackcoords_with_colors(coords)
        widget = self._module_manager.get_widget(AnnotationModule.NAME)
        widget.set_coords()

    def show_image(self, image_dict):
        widget = self.get_display_module()
        widget.set_image_dict(image_dict)
        self.update_statusbar()

    def set_display_module(self, display_module ):
        self.display_module = display_module

    def get_display_module(self):
        return self.display_module

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
               self.image_viewer.scalefactor*100)
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
        self._t_slider.setValue(coordinate.time)

        self._t_slider.blockSignals(False)
        self._process_image()
        # propagate the signal further to other modules
        #self.coordinates_changed.emit(coordinate)

    def set_coordinate(self, coordinate):
        """
        Changes the Navigator to a fixed coordinate
        """
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        nav.nav_to_coordinate(coordinate)

    def _process_image(self, ):
        self.image_viewer.remove_objects()
        settings = BaseProcessorFrame.get_special_settings(self._settings)
        settings.set_section('General')
        settings.set2('constrain_positions', True)
        settings.set2('positions', self.coordinate.position)
        settings.set2('redofailedonly', False)
        settings.set2('framerange', True)
        settings.set2('framerange_begin', self.coordinate.time)
        settings.set2('framerange_end', self.coordinate.time)

        settings.set_section('Processing')
        _classify_objects = self._show_objects_by == 'classification'

        settings.set2('primary_classification', _classify_objects )
        settings.set2('secondary_classification', _classify_objects)
        settings.set2('tertiary_classification', _classify_objects)
        settings.set2('merged_classification', _classify_objects)
        settings.set2('primary_featureextraction', _classify_objects)
        settings.set2('secondary_featureextraction', _classify_objects)
        settings.set2('objectdetection', self._detect_objects)
        settings.set2('tracking', False)

        settings.set('Output', 'hdf5_create_file', False)
        settings.set('General', 'rendering', {})
        settings.set('General', 'rendering_class', {})

        nchannels = len(self._imagecontainer.channels)
        # XXX channel mapping unclear
        # processing channel <--> color channel
        # i.e problems if 2 processing channels have the same color
        if nchannels == 2:
            settings.set('General', 'process_secondary', True)
        elif nchannels >= 3:
            settings.set('General', 'process_secondary', True)
            settings.set('General', 'process_tertiary', True)

        settings.set('General', 'rendering', {})
        analyzer = AnalyzerBrowser(self.coordinate.plate,
                                   settings,
                                   self._imagecontainer)

        res = None
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            res = analyzer()
            self.render_browser(res)
        except Exception, e:
            import traceback
            from cecog.gui.util import exception
            traceback.print_exc()
            exception(self, str(e))
            raise
        finally:
            QApplication.restoreOverrideCursor()

        QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
        return res

    def render_browser(self, cellanalyzer):
        d = {}

        for name in cellanalyzer.get_channel_names():
            channel = cellanalyzer.get_channel(name)
            if bool(channel.strChannelId):
                d[channel.strChannelId] = channel.meta_image.image
                self.show_image(d)

        channel_name, region_name = self._object_region
        try:
            channel = cellanalyzer.get_channel(channel_name)
        except KeyError:
            raise KeyError(("Channel %s may be turned off. "
                            "See section General->Channels" %channel_name))

        if channel.has_region(region_name):
            region = channel.get_region(region_name)
            if self._show_objects_by == 'classification':
                self.set_classified_crack_contours(region)
            else:
                self.set_coords(region)

    def on_refresh(self):
        regnames = self._region_names()
        self.update_regions.emit(regnames)
        self._process_image()

    def on_zoom_info_updated(self, info):
        self.update_statusbar()

    def timeToolTip(self, value):
        QToolTip.showText(QCursor.pos(), str(value), self._t_slider)

    def on_time_changed_by_slider(self):
        frame = self._t_slider.value()
        nav = self._module_manager.get_widget(NavigationModule.NAME)
        meta_data = self._imagecontainer.get_meta_data()
        nav.nav_to_time(frame)

    def on_object_region_changed(self, channel, region):
        self._object_region = channel, region
        self.on_refresh()

    def on_object_color_changed(self, channel, region):
        self._object_region = channel, region
        self.image_viewer._update_contours()

    def on_act_prev_t(self):
        self._t_slider.setValue(self._t_slider.value()-1)
        self.on_time_changed_by_slider()

    def on_act_next_t(self):
        self._t_slider.setValue(self._t_slider.value()+1)
        self.on_time_changed_by_slider()

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

    def detect_objects_toggled(self, state):
        if state:
            if self._settings.get('Output', 'hdf5_reuse'):
                QMessageBox.information(self, 'Information',
                                        ('HDF5 reuse is enabled. Raw data and segmentation '
                                         'will be loaded from HDF5 files. Changes of'
                                         ' normalization and segmentation parameters will'
                                         ' have no effect in browser!'))
            self.on_refresh()

    def on_toggle_show_contours(self, state):
        self._show_objects = state
        self.image_viewer._update()

#     def keyPressEvent(self, ev):
#         super(Browser, self).keyPressEvent(self, ev)
#         # allow to return from fullscreen via the Escape key
#         if self.isFullScreen() and ev.key() == Qt.Key_Escape:
#             self.showNormal()
#             self._act_fullscreen.setChecked(False)
#             self.raise_()

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

def load_image_container_from_settings(settings):
    imagecontainer = ImageContainer()
    infos = imagecontainer.iter_check_plates(settings)
    scan_plates = dict((info[0], False) for info in infos)
    import_iter = imagecontainer.iter_import_from_settings(settings, scan_plates)
    for idx, info in enumerate(import_iter):
        pass

    if len(imagecontainer.plates) > 0:
        plate = imagecontainer.plates[0]
        imagecontainer.set_plate(plate)
    return imagecontainer

def load_settings(settings_file):
    settings = GuiConfigSettings(None)
    settings.read(settings_file)
    return settings

if __name__ == "__main__":
    import sys
    from cecog.environment import CecogEnvironment
    from cecog.version import version
    environ = CecogEnvironment(version)
    app = QApplication(sys.argv)

    settings = load_settings((r'C:\Users\sommerc\data\cecog'
                              '\Settings\exp911_version_150.conf'))
    imagecontainer = load_image_container_from_settings(settings)

    browser = Browser(settings, imagecontainer)


    browser.show()
    app.exec_()
