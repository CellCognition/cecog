"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
              See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['MainWindow',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import sys
import os

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.importer.filetoken import (MetaMorphTokenImporter,
                                      ZeissLifeTokenImporter,
                                      )
from cecog.core.imagecontainer import (ImageContainer,
                                       )

from cecog.gui.util import (StyledFrame,
                            StyledTabWidget,
                            DEFAULT_COLORS,
                            STYLESHEET_CARBON,
                            STYLESHEET_NATIVE_MODIFIED,
                            CoordinateHolder,
                            )
from cecog.util.color import hex_to_rgb

from cecog.gui.widgets.imageviewer import ImageViewer
from cecog.gui.widgets.positionframe import PositionFrame
from cecog.gui.widgets.metadataframe import MetaDataFrame
from cecog.gui.widgets.channelframe import ChannelFrame
from cecog.gui.widgets.displayframe import DisplayFrame
from cecog.gui.widgets.maskframe import MaskFrame

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ViewerFrame(StyledFrame):

    def __init__(self, parent):
        StyledFrame.__init__(self, parent)


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setBackgroundRole(QPalette.Dark)

        self.frame = QFrame(self)
        self.setCentralWidget(self.frame)

        action_about = self.create_action('&About', slot=self._on_about)
        action_quit = self.create_action('&Quit', slot=self._on_quit)
        action_pref = self.create_action('&Preferences',
                                         slot=self._on_preferences)

        action_new = self.create_action('&New...', shortcut=QKeySequence.New,
                                          icon='filenew')
        action_open = self.create_action('&Open...',
                                         shortcut=QKeySequence.Open,
                                         slot=self._on_file_open)
        file_menu = self.menuBar().addMenu('&File')
        self.add_actions(file_menu, (action_about,  action_pref,
                                     None, action_open,
                                     None, action_quit))

        act_next_t = self.create_action('Move to next time-point',
                                        shortcut=QKeySequence.SelectNextChar,
                                        slot=self._on_shortcut_right)
        act_prev_t = self.create_action('Move to previous time-point',
                                       shortcut=QKeySequence.SelectPreviousChar,
                                       slot=self._on_shortcut_left)
        act_next_z = self.create_action('Move to next z-slice',
                                       shortcut=QKeySequence.SelectPreviousLine,
                                       slot=self._on_shortcut_up)
        act_prev_z = self.create_action('Move to previous z-slice',
                                       shortcut=QKeySequence.SelectNextLine,
                                       slot=self._on_shortcut_down)
        act_fullscreen = self.create_action('Fullscreen',
                                            shortcut=QKeySequence(QKeySequence.Find),
                                            slot=self._on_shortcut_fullscreen)
        act_stylesheet = self.create_action('Use carbon style',
                                            shortcut=QKeySequence(QKeySequence.New),
                                            slot=self._on_shortcut_stylesheet,
                                            signal='triggered(bool)',
                                            checkable=True,
                                            checked=True)
        view_menu = self.menuBar().addMenu('&View')
        self.add_actions(view_menu, (act_prev_t, act_next_t, None,
                                     act_prev_z, act_next_z, None,
                                     act_fullscreen, None,
                                     act_stylesheet))

        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.image_container = None
        self.current_coordinates = None

        self.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding,
                                       QSizePolicy.MinimumExpanding))
        self.layout = QGridLayout()

        dummy_frame = StyledFrame(self.frame)
        dummy_frame.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum,
                        QSizePolicy.Expanding|QSizePolicy.Maximum))
        dummy_frame.setStyleSheet(#"background-color: #000000;"
                                  "margin: 0; border: 0;")
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.viewer = ImageViewer(dummy_frame)
        self.viewer.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding,
                        QSizePolicy.Expanding))
        self.viewer.setStyleSheet(#"background-color: #000000;"
                                  "margin: 0; border: 0;")

        # set the cecog logo as place-holder of the yet empty viewer
        qimage = QImage(':cecog_logo_small_black')
        # do some alpha-blending here
        pixmap = QPixmap(qimage.size())
        pixmap.fill(QColor(*(160,)*3))
        qimage.setAlphaChannel(pixmap.toImage())
        self.viewer.from_qimage(qimage)

        layout.addWidget(self.viewer, 0, 0)
        dummy_frame.setLayout(layout)

        self.slider_t = QSlider(Qt.Horizontal, self.frame)
        self.slider_t.setRange(0, 0)
        self.slider_t.setTracking(True)
        self.slider_t.setTickPosition(QSlider.TicksBelow)
        self.slider_t.setTickInterval(1)
        self.slider_t.setFocusPolicy(Qt.StrongFocus)
        self.slider_t.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                QSizePolicy.Minimum))
        self.slider_t.hide()
        self.slider_t.setToolTip('press Shift+Left/Right for '
                                 'scrolling along time')
        self.connect(self.slider_t, SIGNAL('valueChanged(int)'),
                     self.on_slider_t_valueChanged)

        self.slider_z = QSlider(Qt.Vertical, self.frame)
        self.slider_z.hide()
        self.slider_z.setRange(0, 0)
        self.slider_z.setTracking(True)
        self.slider_z.setTickPosition(QSlider.TicksLeft)
        self.slider_z.setTickInterval(1)
        self.slider_z.setFocusPolicy(Qt.StrongFocus)
        self.slider_z.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                                QSizePolicy.Expanding))
        self.slider_z.setToolTip('press Shift+Up/Down for scrolling '
                                 'along zslices')

        self.connect(self.slider_z, SIGNAL('valueChanged(int)'),
                     self.on_slider_z_valueChanged)

        self.layout.addWidget(dummy_frame, 0, 1)
        self.layout.addWidget(self.slider_t, 1, 1)
        self.layout.addWidget(self.slider_z, 0, 0)
        self.frame.setLayout(self.layout)

    def _finalize_init(self):
        self.center()
        self.show()
        self.raise_()

    def _add_toolbox(self):
        self.toolbox = QToolBox(self.frame)

        self.metadata_frame = MetaDataFrame(self.toolbox)
        self.position_frame = PositionFrame(self.toolbox)
        self.channel_frame = ChannelFrame(self.toolbox, self.viewer,
                                          DEFAULT_COLORS)
        self.view_frame = DisplayFrame(self.toolbox, self.viewer)

        self.position_frame.setFocusPolicy(Qt.StrongFocus)

        self.connect(self.position_frame,
                     SIGNAL('itemSelectionChanged()'),
                     self.on_position_changed)

        self.toolbox.addItem(self.metadata_frame, 'MetaData')
        self.toolbox.addItem(self.position_frame, 'Positions')
        self.toolbox.addItem(self.channel_frame, 'Channels')
        self.toolbox.addItem(self.view_frame, 'Display')

        self.toolbox.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                               QSizePolicy.Expanding))
        #self.toolbox.setMaximumWidth(140)
        #self.toolbox.setCurrentIndex(2)
        #self.layout.addWidget(self.toolbox, 0, 2)


    def _on_shortcut_left(self):
        self.slider_t.setValue(self.slider_t.value()-1)

    def _on_shortcut_right(self):
        self.slider_t.setValue(self.slider_t.value()+1)

    def _on_shortcut_up(self):
        self.slider_z.setValue(self.slider_z.value()+1)

    def _on_shortcut_down(self):
        self.slider_z.setValue(self.slider_z.value()-1)

    def _on_shortcut_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            #self.viewer.center()
            self.setWindowState(Qt.WindowActive)
        else:
            self.showFullScreen()
            #self.viewer.center()

    def _on_shortcut_stylesheet(self, state):
        if state:
            qApp.setStyleSheet(STYLESHEET_CARBON)
        else:
            qApp.setStyleSheet(STYLESHEET_NATIVE_MODIFIED)

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

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2,
        (screen.height()-size.height())/2)

    def _on_file_open(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec_():
            path = str(dialog.selectedFiles()[0])
            self._load(path)

    def on_position_changed(self):
        #FIXME: problematic int conversion
        item = self.position_frame.currentItem()
        self._update_image(position=int(item.text()))

    def on_slider_t_valueChanged(self, time):
        self._update_image(time=time)

    def on_slider_z_valueChanged(self, zslice):
        self._update_image(zslice=zslice)

    def on_slider_c_valueChanged(self, channel_int):
        meta_data = self.image_container.meta_data
        channel = meta_data.channels[channel_int]
        self._update_image(channel=channel)

    def _update_image(self, position=None, time=None, channel=None,
                      zslice=None):
        if not self.current_coordinates is None:
            meta_data = self.image_container.meta_data

            position = position if not position is None else \
                       self.current_coordinates.position
            time = time if not time is None else \
                   self.current_coordinates.time
            channel = channel if not channel is None else \
                      self.current_coordinates.channel
            zslice = zslice if not zslice is None else \
                     self.current_coordinates.zslice

            self.current_coordinates.position = position
            self.current_coordinates.time = time
            self.current_coordinates.zslice = zslice

            channel_list = []
            for channel in meta_data.channels:
                channel_list.append(
                     (channel,
                      self.image_container.get_image(position, time,
                                                     channel, zslice))
                     )
            self.viewer.from_channel_list(channel_list)
            self._update_statusbar()


    def _update_statusbar(self):
        meta_data = self.image_container.meta_data
        position = self.current_coordinates.position
        time = self.current_coordinates.time
        channel = meta_data.channels[0]
        zslice = self.current_coordinates.zslice
        timestamp = meta_data.get_timestamp_relative(position, time) / 60.
        self.statusbar.showMessage('P %s, T %s (%.1f min), C %s, Z %s' %\
                                   (position, time, timestamp, channel, zslice))

    def _on_about(self):
        print "about"
        dialog = StyledDialog(self)
        dialog.setWindowTitle('About...')
        layout = QGridLayout()
        layout.setContentsMargins(50,50,50,50)
        image = QImage(':cecog_logo_small_black')
        label1 = StyledLabel()
        label1.setPixmap(QPixmap.fromImage(image))
        layout.addWidget(label1, 0, 0)
        label2 = StyledLabel('CecogBrowser\n'
                            'A fast cross-platform browser for bio-images.\n'
                            'Copyright (c) 2006 - 2009 by Michael Held\n'
                            'Gerlich Lab, ETH Zurich, Switzerland')
        label2.setAlignment(Qt.AlignCenter)
        layout.addWidget(label2, 1, 0)
        layout.setAlignment(Qt.AlignCenter|
                            Qt.AlignVCenter)
        dialog.setLayout(layout)
        dialog.show()

    def _on_preferences(self):
        print "pref"

    def _on_quit(self):
        print "quit"
        QApplication.quit()

    def _load(self, path):
        self.image_container = ImageContainer(MetaMorphTokenImporter(path))
        meta_data = self.image_container.meta_data
        print meta_data

        # important step to prevent unwanted updates from signals

        self.position_frame.update_positions(meta_data.positions)
        self.metadata_frame.update_metadata(meta_data)

        if len(meta_data.times) > 1:
            self.slider_t.setRange(meta_data.times[0], meta_data.times[-1])
            self.slider_t.show()
        else:
            self.slider_t.hide()

        if len(meta_data.zslices) > 1:
            self.slider_z.setRange(meta_data.zslices[0], meta_data.zslices[-1])
            self.slider_z.show()
        else:
            self.slider_z.hide()

        COLOR_MAPPING = {'rfp' : '#FF0000',
                         'gfp' : '#00FF00'}

        self.channel_frame.set_channels([(c,
                                          QColor(*hex_to_rgb(COLOR_MAPPING[c])))
                                         for c in meta_data.channels])
        self.viewer.set_channels([(c, hex_to_rgb(COLOR_MAPPING[c]))
                                  for c in meta_data.channels])

        self.current_coordinates = CoordinateHolder()
        self.current_coordinates.position = meta_data.positions[0]
        self.current_coordinates.time = meta_data.times[0]
        self.current_coordinates.channel = meta_data.channels[0]
        self.current_coordinates.zslice = meta_data.zslices[0]

        self._update_image()
        self.viewer.show()
        self.viewer.center()
        self.layout.update()

    def _on_info(self):
        widget = QDialog(self)
        layout = QGridLayout()
        layout.addWidget(QLabel('Positions:', self), 0, 0)
        layout.addWidget(QLabel('Time:', self), 1, 0)
        layout.addWidget(QLabel('Channels:', self), 2, 0)
        layout.addWidget(QLabel('ZSlices:', self), 3, 0)
        layout.addWidget(QLabel('Height:', self), 4, 0)
        layout.addWidget(QLabel('Width:', self), 5, 0)

        if not self.image_container is None:
            meta_data = self.image_container.meta_data
            layout.addWidget(QLabel(str(meta_data.dim_p), self), 0, 1)
            layout.addWidget(QLabel(str(meta_data.dim_t), self), 1, 1)
            layout.addWidget(QLabel(str(meta_data.dim_c), self), 2, 1)
            layout.addWidget(QLabel(str(meta_data.dim_z), self), 3, 1)
            layout.addWidget(QLabel(str(meta_data.dim_y), self), 4, 1)
            layout.addWidget(QLabel(str(meta_data.dim_x), self), 5, 1)

        widget.setLayout(layout)
        widget.show()


class BrowserMainWindow(MainWindow):

    def __init__(self):
        super(BrowserMainWindow, self).__init__()

        self.setGeometry(0, 0, 1000, 700)
        self.setWindowTitle('CecogBrowser')

        self._add_toolbox()
        self.toolbox.setMaximumWidth(140)
        self.layout.addWidget(self.toolbox, 0, 2, 2, 1)

        self._finalize_init()


class AnalyzerMainWindow(MainWindow):

    def __init__(self):
        super(AnalyzerMainWindow, self).__init__()

        self.setGeometry(0, 0, 1000, 700)
        self.setWindowTitle('CecogAnalyzer')

        self._add_toolbox()
        #self.toolbox.setMaximumWidth(140)
        #self.layout.addWidget(self.toolbox, 0, 2)


        self.tabwidget = StyledTabWidget(self.frame)
        self.tabwidget.setUsesScrollButtons(True)
        self.tabwidget.addTab(self.toolbox, 'General')

        self.tabwidget.addTab(StyledFrame(self.frame), 'Channels')

        self.mask_frame = MaskFrame(self.tabwidget)
        self.tabwidget.addTab(self.mask_frame, 'Masks')

        self.tabwidget.addTab(StyledFrame(self.frame), 'Features')
        self.tabwidget.addTab(StyledFrame(self.frame), 'Classification')


        self.tabwidget.setMaximumWidth(400)
        self.layout.addWidget(self.tabwidget, 0, 2, 2, 1)

        self._finalize_init()


#-------------------------------------------------------------------------------
# main:
#

