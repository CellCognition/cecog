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
from cecog.gui.util import (#DEFAULT_COLORS,
                            #StyledFrame,
                            numpy_to_qimage,
                            )

from cecog.util.color import hex_to_rgb
#from cecog.ccore import (apply_lut,
#                         apply_blending,
#                         lut_from_single_color,
#                         )
#from cecog.core.workflow import workflow_manager, ImageViewerRenderer

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class ImageScene(QGraphicsScene):

    def __init__(self, parent):
        super(ImageScene, self).__init__(parent)


class ImageViewer(QGraphicsView):

    MOVE_KEY = Qt.Key_Space

    image_mouse_pressed = pyqtSignal(QPointF, int)
    image_mouse_dblclk = pyqtSignal(QPointF)

    def __init__(self, parent, auto_resize=False):
        super(ImageViewer, self).__init__(parent)
        #self.setMouseTracking(True)

        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setDragMode(QGraphicsView.NoDrag)

        #self.label.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
        #                                     QSizePolicy.Expanding))

        #self.label.show()

        self._qimage = None
        self.connect(self, SIGNAL('MouseMovedOverImage'),
                     self._on_move)

        self._scale = 1.0
        self._auto_resize = auto_resize
        self._move_on = False
        self._click_on = False
        self._home_pos = None

        #self._renderer = ImageViewerRenderer(self)
        #workflow_manager.register_renderer(self._renderer)

#    def set_channels(self, channels):
#        for name, rgb_tuple in channels:
#            lut = lut_from_single_color(rgb_tuple)
#            self.channel_mapping[name] = (lut, 1.0)

    def update_lut_by_name(self, name, lut, alpha):
        self.channel_mapping[name] = (lut, alpha)
        self._update_view()

    def update_view(self):
        pass
#        rgb_image = make_image_overlay([items[1] for items in self.channel_list],
#                                       [self.channel_mapping[items[0]]
#                                        for items in self.channel_list])

        #workflow_manager.process_experiment_channels(self.channel_list)
        #rgb_image = workflow_manager.get_render_result()

#        rgb_image = apply_blending([apply_lut(image,
#                                              self.channel_mapping[channel][0])
#                                    for channel, image in self.channel_list],
#                                   [self.channel_mapping[channel][1]
#                                    for channel, image in self.channel_list])
        #self.from_pyvigra(rgb_image)
        #self.from_pyvigra(self.channel_list[0][1])

    def set_scale_transform(self, transform):
        self._scale_transform = transform

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
#        qimage = self._qimage.scaled(self._qimage.width()*self._scale,
#                                     self._qimage.height()*self._scale,
#                                     Qt.KeepAspectRatio,
#                                     self._scale_transform)
#        self.label.setPixmap(QPixmap.fromImage(qimage))
#        self.label.resize(self.label.pixmap().size())
#        self.setMaximumSize(self.label.size())
        self._scene.addPixmap(QPixmap.fromImage(self._qimage))

    def center(self):
        screen = self.geometry()
        size = self.label.geometry()
        self.label.move((screen.width()-size.width())/2,
                        (screen.height()-size.height())/2)
        self.update()

    def scale_relative(self, value, ensure_fit=False):
        # prevent scaling beyond the viewport size (either below or above,
        # depending on zoom in (value > 1.) or zoom out (value < 1.)
        # only one side is required for fit (the entire image is visible)
        if ensure_fit:
            # the size of the scene (transform independent)
            rect = self.sceneRect()
            # the size of the viewport
            size = self.viewport().size()
            # map the width/height to the scene to see how big the scene within
            # the viewport really is -> any simpler solution?
            coord = self.mapFromScene(rect.width(), rect.height())
            if (value < 1. and
                (coord.x() >= size.width() or coord.y() >= size.height()) or
                value > 1. and
                (coord.x() <= size.width() or coord.y() <= size.height())):
                self.scale(value, value)
        else:
            self.scale(value, value)

    def scale_reset(self):
        self.resetTransform()

    def scale_to_fit(self):
        self.fitInView(self.sceneRect(), mode=Qt.KeepAspectRatio)

    def set_auto_resize(self, state):
        self._auto_resize = state

    # protected method overload

    def keyPressEvent(self, ev):
        if ev.key() == self.MOVE_KEY and not self._move_on:
            self._move_on = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)

    def keyReleaseEvent(self, ev):
        if ev.key() == self.MOVE_KEY and self._move_on:
            self.setDragMode(QGraphicsView.NoDrag)
            self._move_on = False

    def enterEvent(self, ev):
        self.setFocus()

    def mousePressEvent(self, ev):
        super(ImageViewer, self).mousePressEvent(ev)
        if not self._move_on:
            point = self.mapToScene(ev.pos())
            self.image_mouse_pressed.emit(point, ev.modifiers())

#    def mouseDoubleClickEvent(self, ev):
#        super(ImageViewer, self).mouseDoubleClickEvent(ev)
#        if not self._move_on:
#            point = self.mapToScene(ev.pos())
#            self.image_mouse_dblclk.emit(point)

    def resizeEvent(self, ev):
        super(ImageViewer, self).resizeEvent(ev)
        if self._auto_resize:
            self.scale_to_fit()

