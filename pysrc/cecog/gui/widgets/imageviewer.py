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

__all__ = ['ImageViewer',
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
from cecog.gui.util import (DEFAULT_COLORS,
                            StyledFrame,
                            numpy_to_qimage,
                            )

from cecog.util.color import hex_to_rgb
from cecog.ccore import (apply_lut,
                         apply_blending,
                         lut_from_single_color,
                         )
from cecog.core.workflow import workflow_manager, ImageViewerRenderer

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ImageViewer(StyledFrame):

    MOVE_KEY = Qt.Key_Space

    def __init__(self, parent):
        super(ImageViewer, self).__init__(parent)
        self.setMouseTracking(True)

        self.layout = QGridLayout()

        self.label = QLabel(self)
        self.label.show()

        self._qimage = None
        self.connect(self, SIGNAL('MouseMovedOverImage'),
                     self._on_move)

        self._scale = 1.0
        self._scale_transform = Qt.FastTransformation
        self._move_on = False
        self._click_on = False
        self._home_pos = None

        self._renderer = ImageViewerRenderer(self)
        workflow_manager.register_renderer(self._renderer)

    def set_channels(self, channels):
        for name, rgb_tuple in channels:
            lut = lut_from_single_color(rgb_tuple)
            self.channel_mapping[name] = (lut, 1.0)

    def update_lut_by_name(self, name, lut, alpha):
        self.channel_mapping[name] = (lut, alpha)
        self._update_view()

    def update_view(self):
#        rgb_image = make_image_overlay([items[1] for items in self.channel_list],
#                                       [self.channel_mapping[items[0]]
#                                        for items in self.channel_list])

        workflow_manager.process_experiment_channels(self.channel_list)
        #rgb_image = workflow_manager.get_render_result()

#        rgb_image = apply_blending([apply_lut(image,
#                                              self.channel_mapping[channel][0])
#                                    for channel, image in self.channel_list],
#                                   [self.channel_mapping[channel][1]
#                                    for channel, image in self.channel_list])
        #self.from_pyvigra(rgb_image)
        #self.from_pyvigra(self.channel_list[0][1])


    def from_numpy(self, data):
        self._qimage = numpy_to_qimage(data)
        # safe the data for garbage collection
        self._qimage.ndarray = data
        self._update()

    def from_pyvigra(self, image):
        self._qimage = numpy_to_qimage(image.to_array())
        # safe the data for garbage collection
        self._qimage.vigra_image = image
        self._update()

    def from_file(self, filename):
        self._qimage = QImage(filename)
        self._update()

    def from_qimage(self, qimage):
        self._qimage = qimage
        self._update()

    def from_channel_list(self, channel_list):
        self.channel_list = channel_list
        self.update_view()

    def _on_move(self, data):
        pos, color = data
        if self._qimage.isGrayscale():
            print pos, QColor(color).getRgb()[0]
        else:
            print pos, QColor(color).getRgb()[:3]

    def _update(self):
        qimage = self._qimage.scaled(self._qimage.width()*self._scale,
                                     self._qimage.height()*self._scale,
                                     Qt.KeepAspectRatio,
                                     self._scale_transform)
        self.label.setPixmap(QPixmap.fromImage(qimage))
        self.label.resize(self.label.pixmap().size())
        self.setMaximumSize(self.label.size())

    def center(self):
        screen = self.geometry()
        size = self.label.geometry()
        self.label.move((screen.width()-size.width())/2,
                        (screen.height()-size.height())/2)
        self.update()

    def scale_to_value(self, value):
        self._scale = value
        self.label.hide()
        self._update()
        self.center()
        self.label.show()

    def scale_to_original(self):
        self.scale_to_value(1.0)
        return 1.0

    def scale_to_fit(self):
        # fit by width
        size = self.parent().geometry()
        value = size.width() / float(self._qimage.width())
        self.scale_to_value(value)
        return value

    # protected method overload

    def keyPressEvent(self, ev):
        if ev.key() == self.MOVE_KEY and not self._move_on:
            self._move_on = True
            #print self._move_on, self._click_on
            self.setCursor(Qt.OpenHandCursor)

    def keyReleaseEvent(self, ev):
        if ev.key() == self.MOVE_KEY and self._move_on:
            self._move_on = False
            self._click_on = False
            #print self._move_on, self._click_on
            self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, ev):
        self.setFocus()
        if not self._click_on:
            self._move_on = False

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
        self.grabKeyboard()
        self.grabMouse()
        if self._move_on and not self._click_on:
            self._click_on = True
            self.setCursor(Qt.ClosedHandCursor)
            self._home_pos = ev.pos() - self.label.pos()
            #print self._move_on, self._click_on

    def mouseReleaseEvent(self, ev):
        if self._move_on and self._click_on:
            self._click_on = False
            self._home_pos = None
            self.setCursor(Qt.OpenHandCursor)
        elif self._click_on:
            self._click_on = False
            self._home_pos = None
        self.releaseKeyboard()
        self.releaseMouse()
        #print self._move_on, self._click_on

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



#-------------------------------------------------------------------------------
# main:
#

