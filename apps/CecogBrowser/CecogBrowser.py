"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL license.
                     See the LICENSE.txt for details.

"""

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = []

#------------------------------------------------------------------------------
# standard library imports:
#
import time
import sys
import os

#------------------------------------------------------------------------------
# extension module imports:
#
import numpy

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#from pdk.phenes import *
from pdk.ordereddict import OrderedDict
from mito.colors import make_colors
#------------------------------------------------------------------------------
# cecog imports:
#
import qrc_resources
#import VigraQt
import pyvigra

#from cecog.core.workflow import Workflow
from cecog.importer.filetoken import (MetaMorphTokenImporter, 
                                      ZeissLifeTokenImporter,
                                      )
from cecog.core.imagecontainer import (ImageContainer,
                                       )

#------------------------------------------------------------------------------
# constants:
#

DEFAULT_COLORS = [QColor(255,0,0), QColor(0,255,0), QColor(0,0,255), 
                  QColor(0,0,0), QColor(255,255,255)]

STYLESHEET_NATIVE_MODIFIED = \
"""
QToolBox::tab {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                 stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                 stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
     border: 1px solid darkgrey;
     border-radius: 4px;
     color: #333333;
     padding-left: 5px;
}

QToolBox::tab:selected {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                 stop: 0 #F2F2F2, stop: 0.4 #DDDDDD,
                                 stop: 0.5 #D8D8D8, stop: 1.0 #999999);
     font: bold;
     color: #000000;
}

StyledFrame {
     background: #DDDDDD;
     border: 1px solid darkgrey;
     border-radius: 4px;
     padding: 0px;
     margin: 0px;
 }

PositionFrame {
     background: #DDDDDD;
     border: 1px solid darkgrey;
     border-radius: 4px;
     padding: 0px;
     margin: 0px;
 }

ImageViewer {
     background: #000000;
     border: 0;
}
"""

STYLESHEET_CARBON = \
"""

QToolBox::tab {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                 stop: 0 #313131, stop: 0.4 #222222,
                                 stop: 0.5 #282828, stop: 1.0 #232323);
     border: 1px solid #999999;
     border-radius: 4px;
     color: #CCCCCC;
     padding-left: 5px;
}

QToolBox::tab:selected {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                 stop: 0 #424242, stop: 0.4 #222222,
                                 stop: 0.5 #282828, stop: 1.0 #111111);
     font: bold;
     color: #FFFFFF;
}

QComboBox {
    border: 1px solid darkgray;
    border-radius: 3px;
    padding: 1px 1px 1px 20px;
    margin: 1px;
    alignment: center;
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #313131, stop: 0.4 #222222,
                                stop: 0.5 #282828, stop: 1.0 #232323);
    icon-size: 50px;
    selection-background-color: #444444;
    color: white;
}
 
QComboBox::drop-down {
    width: 20px;
    border-left-width: 1px;
    border-left-color: darkgray;
    border-left-style: solid;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background: #222222;
}

QComboBox QAbstractItemView {
    border: 1px solid darkgray;
    background: #222222;
    spacing: 0;
} 

QToolBox {
    background: transparent;
}

StyledFrame {
    border: 1px solid darkgrey;
    border-radius: 4px;
    padding: 0px;
    margin: 0px;
 }

PositionFrame {
    border: 1px solid darkgrey;
    border-radius: 4px;
    padding: 0px;
    margin: 0px;
 }

ImageViewer {
    background: #000000;
    border: 0;     
}

MainWindow QFrame {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #424242, stop: 0.4 #222222,
                                stop: 0.5 #282828, stop: 1.0 #111111);
/*
    background-image: url(':background_carbon');
*/
    color: white;
}

QStatusBar {
    background-color: #333333;
    color: white;
}

"""

#------------------------------------------------------------------------------
# classes:
#

def numpy_to_qimage(data, colors=None):
    h, w = data.shape[:2]   
    if data.dtype == numpy.uint8:
        if data.ndim == 2:
            shape = (h, numpy.ceil(w / 4.) * 4)
            if shape != data.shape:
                image = numpy.zeros(shape, numpy.uint8, 'C')
                image[:,:w] = data
            else:
                image = data
            format = QImage.Format_Indexed8
            #colors = [QColor(i,i,i) for i in range(256)] 
        elif data.ndim == 3:
            shape = (h, int(numpy.ceil(w / 4.) * 4), data.shape[2])
            if data.shape[2] == 3:
                if shape != data.shape:
                    image = numpy.zeros(shape, numpy.uint8, 'C')
                    image[:,:w,:] = data[:,:,:]
                    print data
                    print image
                else:
                    image = data#numpy.require(data, numpy.uint8, 'C')
                format = QImage.Format_RGB888
            elif data.shape[2] == 4:
                format = QImage.Format_RGB32
    elif data.dtype == numpy.uint16:
        if data.ndim == 2:
            shape = (h, numpy.ceil(w / 4.) * 4)
            print shape != data.shape
            if shape != data.shape:
                image = numpy.zeros(shape, numpy.uint16, 'C')
                image[:,:w] = data
            else:
                image = data
            minv = numpy.min(image)
            maxv = numpy.max(image)
            data = (255/(maxv-minv)) * (image - minv)
            image = numpy.require(image, numpy.uint8, 'C')
            format = QImage.Format_Indexed8
            #colors = [QColor(i,i,i) for i in range(256)] 
            
    qimage = QImage(image, w, h, format)
    if not colors is None:
        for idx, col in enumerate(colors):
            qimage.setColor(idx, col.rgb())
    return qimage

   
class ImageViewer(QFrame):
    
    MOVE_KEY = Qt.Key_Space

    def __init__(self, parent):
        super(ImageViewer, self).__init__(parent)
        self.setMouseTracking(True)

        self.layout = QGridLayout()

        self.color = QColor(255,255,255)
        self.colors = self.make_color_range(self.color)

        self.label = QLabel(self)
        self.label.show()
        
        self._qimage = None
        self.connect(self, SIGNAL('MouseMovedOverImage'),
                     self._on_move)
        
        self._move_on = False
        self._click_on = False
        self._home_pos = None
        
    def make_color_range(self, color):
        colors = make_colors([(0,0,0), (color.red()/255.,
                                       color.green()/255.,
                                       color.blue()/255.)], 256, False)
        colors = [QColor(r*255, g*255, b*255) for r,g,b in colors]
        return colors
        
    def update_color(self, color):
        self.colors = self.make_color_range(color)
        self.color = color
        for idx, col in enumerate(self.colors):
            self._qimage.setColor(idx, col.rgb())
        self.label.setPixmap(QPixmap.fromImage(self._qimage))

        
    def from_numpy(self, data):
        self._qimage = numpy_to_qimage(data, self.colors)
        # safe the data for garbage collection
        self._qimage.ndarray = data
        self._update()

    def from_pyvigra(self, image):
        self._qimage = numpy_to_qimage(image.to_array(), self.colors)
        # safe the data for garbage collection
        self._qimage.vigra_image = image
        self._update()

    def from_file(self, filename):
        self._qimage = QImage(filename) 
        self._update()

    def from_qimage(self, qimage):
        self._qimage = qimage
        self._update()

    def _on_move(self, data):
        pos, color = data
        if self._qimage.isGrayscale():
            print pos, QColor(color).getRgb()[0]
        else:
            print pos, QColor(color).getRgb()[:3]
        
    def _update(self):
        self.label.setPixmap(QPixmap.fromImage(self._qimage))
        self.label.resize(self.label.pixmap().size())
        self.setMaximumSize(self.label.size())

    def center(self):
        screen = self.geometry()
        size = self.label.geometry()
        self.label.move((screen.width()-size.width())/2,
                        (screen.height()-size.height())/2)

    # protected method overload

    def keyPressEvent(self, ev):
        if ev.key() == self.MOVE_KEY and not self._move_on:
            self._move_on = True
            self.setCursor(Qt.OpenHandCursor)
        
    def keyReleaseEvent(self, ev):
        if ev.key() == self.MOVE_KEY and self._move_on:
            self._move_on = False
            self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, ev):
        self.setFocus()
    
    def mouseMoveEvent(self, ev):
        if self._click_on:
            geom = self.label.geometry()
            size = self.size()
            point = ev.pos() - self._home_pos
            if point.x() >= 0: point.setX(0) 
            if point.y() >= 0: point.setY(0)
            if size.width()-point.x() > geom.width():
                point.setX(size.width() - geom.width())
            if size.height()-point.y() > geom.height():
                point.setY(size.height() - geom.height())
            #print point, geom, size
            self.label.move(point)
            
    def mousePressEvent(self, ev):
        if self._move_on and not self._click_on:
            self._click_on = True
            self.setCursor(Qt.ClosedHandCursor)
            self._home_pos = ev.pos() - self.label.pos()

    def mouseReleaseEvent(self, ev):
        if self._move_on and self._click_on:
            self._click_on = False
            self._home_pos = None
            self.setCursor(Qt.OpenHandCursor)
            
    def resizeEvent(self, ev):
        super(ImageViewer, self).resizeEvent(ev)
        geom = self.label.geometry()
        size = ev.size()
        point = QPoint(geom.x(), geom.y())
        move = False
        if size.width() > geom.width() + geom.x():
            point.setX(size.width() - geom.width())
            move = True
        if size.height() > geom.height() + geom.y():
            point.setY(size.height() - geom.height())
            move = True
        if move:
            self.label.move(point)
        


class ColorBox(QComboBox):
    
    COLOR_SIZE = (50, 10)
    colorSelected = pyqtSignal('QColor')
    
    def __init__(self, parent, color, colors):
        super(ColorBox, self).__init__(parent)
        self.setIconSize(QSize(*self.COLOR_SIZE))
        self._popup_shown = False
        self._base_count = len(colors) + 1
        self._user_count = 0
        self._highlight_index = None  

        for col in colors:
            self.add_color(col)
            
        self.insertSeparator(self.maxCount())
        self.insertItem(self.maxCount(), 'more...')

        #print "moo", color, colors
        #print color in colors
        rgb_values = map(lambda c: c.rgb(), colors)
        if color.rgb() in rgb_values:
            self.setCurrentIndex(rgb_values.index(color.rgb()))
        else:
            index = self.add_color(color, user=True)
            self.setCurrentIndex(index)
        
        self.connect(self, SIGNAL('activated(int)'), self.on_activated)
        self.connect(self, SIGNAL('highlighted(int)'), self.on_highlighted)       
        self.current = self.currentIndex()
        
    def add_color(self, color, user=False):
        pixmap = QPixmap(*self.COLOR_SIZE)
        pixmap.fill(color)
        #painter = QPainter(pixmap)
        #painter.drawRect(0,0,self.COLOR_SIZE[0]-1,self.COLOR_SIZE[1]-1)
        icon = QIcon(pixmap)
        if user:
            index = self._base_count+self._user_count
            self.insertItem(index, icon, '', QVariant(color))
            if self._user_count == 0:
                self.insertSeparator(index+1)
            self._user_count += 1
        else:
            index = None
            self.addItem(icon, '', QVariant(color))
        return index
    
    def get_current(self):
        return QColor(self.itemData(self.current))
    
    def on_activated(self, index):
        if self.itemData(index).isNull():
            dialog = QColorDialog(self.get_current(), self)
            #dialog.setOption(QColorDialog.ShowAlphaChannel)
            if dialog.exec_():
                color = dialog.selectedColor()
                self.current = self.add_color(color, user=True)
                self.colorSelected.emit(self.get_current())
            self.setCurrentIndex(self.current)
        elif self.current != self.currentIndex():
            self.current = self.currentIndex()
            self.colorSelected.emit(self.get_current())

    def on_highlighted(self, index):
        self._highlight_index = index
    
    # protected method overload
        
    def showPopup(self):
        super(ColorBox, self).showPopup()
        self.grabKeyboard()
        self._popup_shown = True
                
    def hidePopup(self):
        self.releaseKeyboard()
        self._popup_shown = False
        super(ColorBox, self).hidePopup()
    
    def keyPressEvent(self, ev):
        if self._popup_shown and ev.key() == Qt.Key_Delete:
            ev.accept()
            if (self._user_count > 0 and 
                self._highlight_index >= self._base_count):
                self.removeItem(self._highlight_index)
                self._user_count -= 1
                if self._user_count == 0:
                    self.removeItem(self._base_count)
                old = self.current
                self.current = self.currentIndex()
                while self.itemData(self.current).isNull():
                    self.current -= 1
                    self.setCurrentIndex(self.current)
                self.hidePopup()
                if old != self.current:
                    self.colorSelected.emit(self.get_current())
        else:
            ev.ignore()
            
class StyledFrame(QFrame):
    pass            
        
class MetaDataFrame(StyledFrame):
    
    def __init__(self, parent):
        super(MetaDataFrame, self).__init__(parent)
        
        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.addWidget(QLabel('Positions:', self), 0, 0)
        self.layout.addWidget(QLabel('Time:', self), 1, 0)
        self.layout.addWidget(QLabel('Channels:', self), 2, 0)
        self.layout.addWidget(QLabel('ZSlices:', self), 3, 0)
        self.layout.addWidget(QLabel('Height:', self), 4, 0)
        self.layout.addWidget(QLabel('Width:', self), 5, 0)

        self.positions_label = QLabel(self)
        self.times_label = QLabel(self)
        self.channels_label = QLabel(self)
        self.zslices_label = QLabel(self)
        self.height_label = QLabel(self)
        self.width_label = QLabel(self)
        
        self.layout.addWidget(self.positions_label, 0, 1)
        self.layout.addWidget(self.times_label, 1, 1)
        self.layout.addWidget(self.channels_label, 2, 1)
        self.layout.addWidget(self.zslices_label, 3, 1)
        self.layout.addWidget(self.height_label, 4, 1)
        self.layout.addWidget(self.width_label, 5, 1)
        
        self.setLayout(self.layout)

    def update_metadata(self, meta_data):
        self.positions_label.setText(str(meta_data.dim_p))
        self.times_label.setText(str(meta_data.dim_t))
        self.channels_label.setText(str(meta_data.dim_c))
        self.zslices_label.setText(str(meta_data.dim_z))
        self.height_label.setText(str(meta_data.dim_y))
        self.width_label.setText(str(meta_data.dim_x))
        
            
#class ChannelFrame(StyledFrame):
#    
#    def __init__(self, parent, viewer, default_colors):
#        super(ChannelFrame, self).__init__(parent)
#        self.viewer = viewer
#        self.layout = QVBoxLayout()
#        self.layout.setAlignment(Qt.AlignTop|Qt.AlignHCenter)
#        self.setLayout(self.layout)        
#        self.default_colors = default_colors 
#
#    def set_channels(self, channels):
#        self.layout.removeWidget()
#        for name, color in channels:
#            self.add_channel(name, self.default_colors)
#
#        line = QFrame(self)
#        line.setFrameShape(QFrame.HLine)
#        self.layout.addWidget(line)
#        self.add_channel('gfp', colors)
#
#    def _add_color_box(self, channel, colors):
#        frame = QFrame(self)
#        frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, 
#                                        QSizePolicy.Minimum))
#        layout = QVBoxLayout()
#        layout.setMargin(0)
#        label = QLabel(channel, frame)
#        box = ColorBox(frame, colors)
#        box.colorSelected.connect(self.on_test)
#        layout.addWidget(label)
#        layout.addWidget(box)
#        frame.setLayout(layout)
#        self.layout.addWidget(frame)
#
#        
#    def on_test(self, color):
#        print color
#        self.viewer.update_color(color)
#                
#    def on_button_pressed(self):
#        self.test = QFrame(self, Qt.Tool)
#        #self.test.set
#        #geom = self.button.geometry()
#        #self.test.setGeometry(geom.x()+geom.width(),geom.y()+geom.height(),50,50)
#        self.test.show()
#        
#    def on_button_released(self):
#        self.test.hide()
        
class ChannelFrame(StyledFrame):
    
    def __init__(self, parent, viewer, default_colors):
        super(ChannelFrame, self).__init__(parent)
        self.viewer = viewer
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop|Qt.AlignHCenter)
        self.setLayout(self.layout)        
        self.default_colors = default_colors
        self._widgets = [] 

    def clear(self):
        # this looks more like hack :-(
        for widget in self._widgets:
            self.layout.removeWidget(widget)
            widget.deleteLater()
        self._widgets = []
    
    def set_channels(self, channels):
        self.clear()
        for idx, (name, color) in enumerate(channels):
            if idx > 0:
                line = QFrame(self)
                line.setFrameShape(QFrame.HLine)
                self.layout.addWidget(line)
                self._widgets.append(line)
            self._add_color_box(name, color, self.default_colors)

    def _add_color_box(self, name, color, colors):
        frame = QFrame(self)
        frame.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, 
                                        QSizePolicy.Minimum))
        layout = QVBoxLayout()
        layout.setMargin(0)
        label = QLabel(name, frame)
        box = ColorBox(frame, color, colors)
        box.colorSelected.connect(self.on_test)
        layout.addWidget(label)
        layout.addWidget(box)
        frame.setLayout(layout)
        self.layout.addWidget(frame)
        self._widgets.append(frame)
        
    def on_test(self, color):
        print color
        self.viewer.update_color(color)
                
    def on_button_pressed(self):
        self.test = QFrame(self, Qt.Tool)
        #self.test.set
        #geom = self.button.geometry()
        #self.test.setGeometry(geom.x()+geom.width(),geom.y()+geom.height(),50,50)
        self.test.show()
        
    def on_button_released(self):
        self.test.hide()        

        
class PositionFrame(QListWidget):
        
    def update_positions(self, positions):
        self.clear()
        for idx, position in enumerate(positions):
            item = QListWidgetItem(str(position))
            self.addItem(item)
            if idx == 0:
                self.setCurrentItem(item)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setBackgroundRole(QPalette.Dark)

        self.setGeometry(0, 0, 900, 700)
        self.setWindowTitle('cecog browser')

        self.frame = QFrame(self)
        self.setCentralWidget(self.frame)
        
        self.center()
        self.show()
        self.raise_()

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
        self.meta_image = None
        
        self.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, 
                                       QSizePolicy.MinimumExpanding))
        self.layout = QGridLayout()
        
        dummy_frame = QFrame(self.frame)
        dummy_frame.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding|QSizePolicy.Maximum, 
                        QSizePolicy.Expanding|QSizePolicy.Maximum))
        dummy_frame.setStyleSheet("background-color: #000000;" 
                                  "margin: 0; border: 0;")
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.viewer = ImageViewer(dummy_frame)
        self.viewer.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, 
                        QSizePolicy.Expanding))
        self.viewer.setStyleSheet("background-color: #000000;"
                                  "margin: 0; border: 0;")
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


        self.toolbox = QToolBox(self.frame)
        
        self.metadata_frame = MetaDataFrame(self.toolbox)
        self.position_frame = PositionFrame(self.toolbox)
        self.channel_frame = ChannelFrame(self.toolbox, self.viewer,
                                          DEFAULT_COLORS)
        
        self.position_frame.setFocusPolicy(Qt.StrongFocus)
        
        self.connect(self.position_frame, 
                     SIGNAL('itemSelectionChanged()'),
                     self.on_position_changed)

        self.toolbox.addItem(self.metadata_frame, 'MetaData')
        self.toolbox.addItem(self.position_frame, 'Positions')
        self.toolbox.addItem(self.channel_frame, 'Channels')
        self.toolbox.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, 
                                               QSizePolicy.Expanding))
        self.toolbox.setMaximumWidth(140)
        self.toolbox.setCurrentIndex(2)

        self.layout.addWidget(dummy_frame, 0, 1)
        self.layout.addWidget(self.slider_t, 1, 1)
        self.layout.addWidget(self.slider_z, 0, 0)
        self.layout.addWidget(self.toolbox, 0, 2)
        self.frame.setLayout(self.layout)
               
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
            self.viewer.center()
            self.setWindowState(Qt.WindowActive)
        else:
            self.showFullScreen()
            self.viewer.center()

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
        if not self.meta_image is None:
            meta_data = self.image_container.meta_data
            position = position if not position is None else \
                       self.meta_image.position 
            time = time if not time is None else self.meta_image.time
            channel = channel if not channel is None else \
                      self.meta_image.channel
            zslice = zslice if not zslice is None else self.meta_image.zslice
            self.meta_image = self.image_container.get_meta_image(position, 
                                                                  time, 
                                                                  channel, 
                                                                  zslice)
            self.viewer.from_pyvigra(self.meta_image.image)
            self._update_statusbar()

    def _update_statusbar(self):
        meta_data = self.image_container.meta_data
        position = self.meta_image.position 
        time = self.meta_image.time
        channel = self.meta_image.channel
        zslice = self.meta_image.zslice
        timestamp = meta_data.get_timestamp_relative(position, time) / 60.
        self.statusbar.showMessage('P %s, T %s (%.1f min), C %s, Z %s' %\
                                   (position, time, timestamp, channel, zslice))

    def _on_about(self):
        print "about"
        dialog = QDialog(self)
        layout = QGridLayout()
        image = QImage(':/logo')
        label1 = QLabel()
        label1.setPixmap(QPixmap.fromImage(image))
        layout.addWidget(label1, 0, 0)
        label2 = QLabel('cecog browser\n'
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
        self.meta_image = None
        
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

        self.channel_frame.set_channels([(c,QColor(255,255,0))
                                          for c in meta_data.channels])
        
        position = meta_data.positions[0]
        time = meta_data.times[0]
        channel = meta_data.channels[0]
        zslice = meta_data.zslices[0]
        self.meta_image = self.image_container.get_meta_image(position, time, 
                                                              channel, zslice)
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
        
    # Qt method overloads
    
    #def keyPressEvent(self, ev):
    #    print ev.key() == Qt.Key_Left

#------------------------------------------------------------------------------
# main:
#

if __name__ == "__main__":
    from pdk.platform import on_windows
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET_CARBON)
    main = MainWindow()
    main.raise_()
    sys.exit(app.exec_())
