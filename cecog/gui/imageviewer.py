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

__all__ = ['ImageViewer']


from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from qimage2ndarray import array2qimage

class ZoomedQGraphicsView(QGraphicsView):  
    def wheelEvent(self, event):
        keys = QApplication.keyboardModifiers()
        k_ctrl = (keys == Qt.ControlModifier)

        self.mousePos = self.mapToScene(event.pos())
        grviewCenter  = self.mapToScene(self.viewport().rect().center())

        if k_ctrl is True:
            if event.delta() > 0:
                scaleFactor = 1.1
            else:
                scaleFactor = 0.9
            self.scale(scaleFactor, scaleFactor)
            
            mousePosAfterScale = self.mapToScene(event.pos())
            offset = self.mousePos - mousePosAfterScale
            newGrviewCenter = grviewCenter + offset
            self.centerOn(newGrviewCenter)

class HoverPolygonItem(QGraphicsPolygonItem):

    def __init__(self, *args, **kw):
        super(HoverPolygonItem, self).__init__(*args, **kw)
        self._old_pen = self.pen()

    def set_pen_color(self, color):
        self._old_pen.setColor(color)
        pen = self.pen()
        pen.setColor(color)
        self.setPen(pen)

    def hoverEnterEvent(self, ev):
        pen = self.pen()
        self._old_pen = pen
        new_pen = QPen(pen)
        new_pen.setWidth(3)
        new_pen.setStyle(Qt.SolidLine)
        self.setPen(new_pen)
        super(HoverPolygonItem, self).hoverEnterEvent(ev)

    def hoverLeaveEvent(self, ev):
        self.setPen(self._old_pen)
        super(HoverPolygonItem, self).hoverLeaveEvent(ev)
        
class QGraphicsPixmapHoverItem(QGraphicsPixmapItem):
    def __init__(self, parent):
        QGraphicsPixmapItem.__init__(self, parent)
        self.setAcceptHoverEvents(True)
        #self.setTransformOriginPoint(self.boundingRect().width()/2, self.boundingRect().height()/2)
        
class ItemScaleHover(object):
    SCALE = 3
    def hoverEnterEvent(self, ev):
        QGraphicsPixmapItem.hoverEnterEvent(self, ev)
        self.setScale(self.SCALE)
        self.setZValue(99)

    def hoverLeaveEvent(self, ev):
        QGraphicsPixmapItem.hoverLeaveEvent(self, ev)
        self.setScale(1.0)
        self.setZValue(1)

class GalleryViewer(ZoomedQGraphicsView):
    image_mouse_pressed = pyqtSignal(QPointF, int, int)
    def __init__(self, parent):
        super(GalleryViewer, self).__init__(parent)
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        #self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.setDragMode(self.NoDrag)
        #self.setTransformationAnchor(self.AnchorViewCenter)
        #self.setResizeAnchor(self.AnchorViewCenter)
        #self.setRenderHints(QPainter.Antialiasing |
        #                    QPainter.SmoothPixmapTransform)
        #self.setViewportUpdateMode(self.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor('#0C7A0C')))
        gradient = QRadialGradient (400, 100, 800);
        gradient.setColorAt(0.2, QColor.fromRgb(72, 72, 72));
        gradient.setColorAt(0.8, QColor.fromRgb(42, 42, 42));

  
        brush = QBrush(gradient);
        self.setBackgroundBrush(brush);
        
        
        
        self.setMouseTracking(True)
        self.hide()
        
    def clear(self):
        self._scene.clear()
        
    def mousePressEvent(self, ev):
        super(GalleryViewer, self).mousePressEvent(ev)
        
        # mouse position and mapped scene point do not match exactly, correcting by 1 in x and y
        point = self.mapToScene(ev.pos()-QPoint(1,1))
        self.image_mouse_pressed.emit(point, ev.button(), ev.modifiers())

class ImageViewer(QGraphicsView):

    image_mouse_pressed = pyqtSignal(QPointF, int, int)
    image_mouse_dblclk = pyqtSignal(QPointF)
    zoom_info_updated = pyqtSignal(float)

    def __init__(self, parent, auto_resize=False):
        super(ImageViewer, self).__init__(parent)
        self.setScene(QGraphicsScene())

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(self.NoDrag)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setResizeAnchor(self.AnchorViewCenter)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(self.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor('#666666')))

        self._qimage = None
        self._auto_resize = auto_resize
        self._click_on = False
        self._home_pos = None
        self._objects = set()
        self.contour_color = QColor('white')
        self.show_contours = True
        self.show_mouseover = True
        
    
        self.init_pixmap()
        
        self.grabGesture(Qt.PinchGesture)
        
    def init_pixmap(self):
        self._pixmap = QGraphicsPixmapItem()
        self._pixmap.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self._pixmap.setTransformationMode(Qt.SmoothTransformation)
        self.scene().addItem(self._pixmap)
        self.setToolTip("ctrl+mouse to pan/zoom")
    def from_numpy(self, data):

        self._qimage = array2qimage(data)
        # safe the data for garbage collection
        # do I really need this??
        self._update()

    def from_vigra(self, image):
        self._qimage = array2qimage(image.toArray(copy=False))
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

    def _update(self):
        self._pixmap.setPixmap(QPixmap.fromImage(self._qimage))

    @property
    def scalefactor(self):
        return self.transform().m11()

    def _update_zoom_info(self):
        self.zoom_info_updated.emit(self.scalefactor)

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
        self.fitInView(self._pixmap, mode=Qt.KeepAspectRatio)
        self._update_zoom_info()

    def set_auto_resize(self, state):
        self._auto_resize = state

    def set_contour_color(self, color):
        self.contour_color = color
        for item in self._objects:
            pen = item.pen()
            pen.setColor(QColor(self.contour_color))
            item.setPen(pen)
            item.setAcceptHoverEvents(self.show_mouseover)
        self._update_contours()

    def set_show_contours(self, state=True):
        self.show_contours = state
        self._update_contours()

    def set_show_mouseover(self, state=True):
        self.show_mouseover = state
        self._update_contours()


    def _update_contours(self):
        for item in self._objects:
            pen = item.pen()
            pen.setStyle(Qt.SolidLine if self.show_contours else Qt.NoPen)
            item.setPen(pen)
            item.setAcceptHoverEvents(self.show_mouseover)

    def set_objects_by_crackcoords(self, coords):
        scene = self.scene()
        for obj_id, obj in coords.iteritems():
            crack = obj.crack_contour
            poly = QPolygonF([QPointF(*pos) for pos in crack])
            item = HoverPolygonItem(poly)
            item.setData(0, obj_id)
            item.setPen(QPen(self.contour_color))
            scene.addItem(item)
            self._objects.add(item)
        self._update_contours()

    def set_objects_by_crackcoords_with_colors(self, coords):
        scene = self.scene()
        for obj_id, obj in coords.iteritems():
            crack = obj.crack_contour
            poly = QPolygonF([QPointF(*pos) for pos in crack])
            item = HoverPolygonItem(poly)
            item.setData(0, obj_id)
            if obj.roisize is not None:
                item.setToolTip(('Object: %d\nSize: %d\nIntensity: '
                                 '%6.2f\nClass: %s (%3.2f)')
                                %(obj_id, obj.roisize, obj.signal,
                                  obj.strClassName, obj.dctProb[obj.iLabel]))
            scene.addItem(item)
            self._objects.add(item)
            item.setPen(QColor(obj.strHexColor))
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
        found_item = None
        scene = self.scene()
        # mouse cursor and mapped scene position seem now to match exactly.
        # increased the search radius from a point to a 3x3 square around
        # the point to identify the scene item
        items = scene.items(point.x()-1, point.y()-1, 3, 3,
                            Qt.IntersectsItemShape)
        items = [i for i in items if isinstance(i, HoverPolygonItem)]
        if len(items) > 0:
            found_item = items[0]
        return found_item

    def enterEvent(self, ev):
        super(ImageViewer, self).enterEvent(ev)
        self.setFocus()
        self.scene().setFocus()

    def mousePressEvent(self, event):
        modified = (event.modifiers() == Qt.ControlModifier)

        if event.button() == Qt.LeftButton and modified:
            self.setDragMode(self.ScrollHandDrag)
            QApplication.setOverrideCursor(QCursor(Qt.ClosedHandCursor))
        else:
            point = self.mapToScene(event.pos()-QPoint(1,1))
            self.image_mouse_pressed.emit(point, event.button(),
                                          event.modifiers())

        super(ImageViewer, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setDragMode(self.NoDrag)
            QApplication.restoreOverrideCursor()
        super(ImageViewer, self).mousePressEvent(event)

    def resizeEvent(self, ev):
        super(ImageViewer, self).resizeEvent(ev)
        if self._auto_resize:
            self.scale_to_fit()

    def wheelEvent(self, event):

        if event.modifiers() == Qt.ControlModifier:
            if event.delta() > 0:
                factor = 1.1
            else:
                factor = 0.9
            self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            QApplication.setOverrideCursor(
                QCursor(Qt.OpenHandCursor))
        super(ImageViewer, self).keyReleaseEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            QApplication.restoreOverrideCursor()
        super(ImageViewer, self).keyReleaseEvent(event)
