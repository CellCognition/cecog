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

__all__ = ['ImageViewer',
           ]

#-------------------------------------------------------------------------------
# standard library imports:
#
import math

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.util import numpy_to_qimage

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
class ItemHoverMixin:

    SCALE = 1.1

    def __init__(self):
        self._old_pen = self.pen()

    def set_pen_color(self, color):
        self._old_pen.setColor(color)
        pen = self.pen()
        pen.setColor(color)
        self.setPen(pen)

    # overwrite QGraphicsItem event methods

    def hoverEnterEvent(self, ev):
        pen = self.pen()
        self._old_pen = pen
        new_pen = QPen(pen)
        new_pen.setWidth(3)
        new_pen.setStyle(Qt.SolidLine)
        self.setPen(new_pen)
        QGraphicsItem.hoverEnterEvent(self, ev)

    def hoverLeaveEvent(self, ev):
        self.setPen(self._old_pen)
        QGraphicsItem.hoverLeaveEvent(self, ev)


class HoverPolygonItem(QGraphicsPolygonItem, ItemHoverMixin):

    def __init__(self, polygon):
        QGraphicsPolygonItem.__init__(self, polygon)
        ItemHoverMixin.__init__(self)


class ImageScene(QGraphicsScene):

    def __init__(self, parent):
        super(ImageScene, self).__init__(parent)


class ImageViewer(QGraphicsView):

    MOVE_KEY = Qt.Key_Space
    MAX_SCALE = 200

    image_mouse_pressed = pyqtSignal(QPointF, int, int)
    image_mouse_dblclk = pyqtSignal(QPointF)
    zoom_info_updated = pyqtSignal(float)
    #object_clicked = pyqtSignal(QGraphicsItem)

    def __init__(self, parent, auto_resize=False):
        super(ImageViewer, self).__init__(parent)
        #self.setMouseTracking(True)

        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(self.NoDrag)
        self.setTransformationAnchor(self.AnchorViewCenter)
        self.setResizeAnchor(self.AnchorViewCenter)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(self.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor('#666666')))

        self._qimage = None
        self.connect(self, SIGNAL('MouseMovedOverImage'),
                     self._on_move)

        self._scale = 1.0
        self._auto_resize = auto_resize
        self._move_on = False
        self._click_on = False
        self._home_pos = None
        self._objects = set()
        self.contour_color = QColor('white')
        self.show_contours = True
        self.show_mouseover = True

        self._pixmap = QGraphicsPixmapItem()
        self._pixmap.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self._pixmap.setTransformationMode(Qt.SmoothTransformation)
        self._scene.addItem(self._pixmap)

        self.grabGesture(Qt.PinchGesture)

    def from_numpy(self, data):
        self._qimage = numpy_to_qimage(data)
        # safe the data for garbage collection
        self._qimage.ndarray = data
        self._update()

    def from_vigra(self, image):
#        if image.width % 4 != 0:
#            image = ccore.subImage(image, ccore.Diff2D(0,0),
#                                   ccore.Diff2D(image.width-(image.width % 4),
#                                                image.height))
#        qimage = numpy_to_qimage(image.toArray(copy=True))

        self._qimage = numpy_to_qimage(image.toArray(copy=False))
        # safe the data for garbage collection
        self._qimage.vigra_image = image
        self._update()

    def from_file(self, filename):
        self._qimage = QImage(filename)
        self._update()

    def from_qimage(self, qimage):
        self._qimage = qimage
        self._update()

    def from_pixmap(self, pixmap):
        self._qimage = None
        self._pixmap.setPixmap(pixmap)

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
        self._pixmap.setPixmap(QPixmap.fromImage(self._qimage))

    @property
    def scale_factor(self):
        return self.transform().m11()

    def _update_zoom_info(self):
        self.zoom_info_updated.emit(self.scale_factor)

    def scale(self, sx, sy):
        if sx*self.scale_factor <= self.MAX_SCALE:
            super(ImageViewer, self).scale(sx, sy)

    def scale_relative(self, value, ensure_fit=False, small_only=False):
        # prevent scaling beyond the viewport size (either below or above,
        # depending on zoom in (value > 1.) or zoom out (value < 1.)
        # only one side is required for fit (the entire image is visible)
        if ensure_fit:
            # the size of the scene (transform independent)
            rect = self.sceneRect()
            # the size of the viewport
            size = self.size()
            # map the width/height to the scene to see how big the scene within
            # the viewport really is -> any simpler solution?
            coord = self.mapFromScene(rect.width(), rect.height()) * value
            if (value < 1. and
                (coord.x() >= size.width() or coord.y() >= size.height()) or
                value > 1. and (small_only or
                 coord.x() <= size.width() or coord.y() <= size.height())):
                self.scale(value, value)
            else:
                self.scale_to_fit()
        else:
            self.scale(value, value)
        self._update_zoom_info()

    def scale_reset(self):
        self.resetTransform()
        self._update_zoom_info()

    def scale_to_fit(self):
        #rect = self.sceneRect()
        #rect.setWidth(rect.width()-3)
        #rect.setHeight(rect.height()-3)
        self.fitInView(self._pixmap, mode=Qt.KeepAspectRatio)
        self._update_zoom_info()

    def set_auto_resize(self, state):
        self._auto_resize = state

    def set_contour_color(self, color):
        self.contour_color = color
        self._update_contours()

    def set_show_contours(self, state=True):
        self.show_contours = state
        self._update_contours()

    def set_show_mouseover(self, state=True):
        self.show_mouseover = state
        self._update_contours()

    def _update_contours(self):
        pen = QPen(self.contour_color)
        pen.setStyle(Qt.SolidLine if self.show_contours else Qt.NoPen)
        for item in self._objects:
            item.setPen(pen)
            item.setAcceptHoverEvents(self.show_mouseover)

    def set_objects_by_crackcoords(self, coords):
        scene = self.scene()
        for obj_id, crack in coords.iteritems():
            poly = QPolygonF([QPointF(*pos) for pos in crack])
            item = HoverPolygonItem(poly)
            #item.setPen(self.object_pen)
            item.setData(0, obj_id)
            scene.addItem(item)
            self._objects.add(item)
        self._update_contours()

    def remove_objects(self):
        scene = self.scene()
        for item in self._objects:
            scene.removeItem(item)
        self._objects.clear()

    def purify_objects(self):
        scene = self.scene()
        for item in self._objects:
            for item2 in item.childItems():
                scene.removeItem(item2)

    def get_object_item(self, point):
        scene = self.scene()
        item = scene.itemAt(point)
        if isinstance(item, HoverPolygonItem):
            found_item = item
        elif isinstance(item.parentItem(), HoverPolygonItem):
            found_item = item.parentItem()
        else:
            found_item = None
        return found_item

    # protected method overload

    def event(self, ev):
        if ev.type() == QEvent.Gesture:
            return self.gestureEvent(ev)
        return super(ImageViewer, self).event(ev)

    def keyPressEvent(self, ev):
        super(ImageViewer, self).keyPressEvent(ev)
        if ev.key() == self.MOVE_KEY and not self._move_on:
            self._move_on = True
            self.setDragMode(self.ScrollHandDrag)

    def keyReleaseEvent(self, ev):
        super(ImageViewer, self).keyReleaseEvent(ev)
        if ev.key() == self.MOVE_KEY and self._move_on:
            self.setDragMode(self.NoDrag)
            self._move_on = False

    def enterEvent(self, ev):
        super(ImageViewer, self).enterEvent(ev)
        self.setFocus()
        self._scene.setFocus()

    def mousePressEvent(self, ev):
        super(ImageViewer, self).mousePressEvent(ev)
        if not self._move_on:
            point = self.mapToScene(ev.pos())
            self.image_mouse_pressed.emit(point, ev.button(), ev.modifiers())

    def resizeEvent(self, ev):
        super(ImageViewer, self).resizeEvent(ev)
        if self._auto_resize:
            self.scale_to_fit()

    def gestureEvent(self, ev):
        # a pinch gesture was detected
        if not ev.gesture(Qt.PinchGesture) is None:
            gesture = ev.gesture(Qt.PinchGesture)
            if gesture.state() == Qt.GestureStarted:
                self.setTransformationAnchor(self.AnchorUnderMouse)
            f = gesture.scaleFactor()
            if f != 1.0:
                self.scale_relative(math.sqrt(f), ensure_fit=True,
                                    small_only=True)
                self.set_auto_resize(False)
            if gesture.state() in [Qt.GestureCanceled, Qt.GestureFinished]:
                self.setTransformationAnchor(self.AnchorViewCenter)
        return True

