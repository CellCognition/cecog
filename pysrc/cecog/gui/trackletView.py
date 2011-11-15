"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2011 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
import time as timeit
__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import sip
# set PyQt API version to 2.0
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)

from PyQt4 import QtGui, QtCore
import zlib
import base64
from scipy.cluster.vq import kmeans
from matplotlib import mlab
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

#-------------------------------------------------------------------------------
# extension module imports:
#
import random
import getopt
import qimage2ndarray
import sys
import numpy
import time as timing


from functools import partial
#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.imageviewer import HoverPolygonItem
from cecog.io.dataprovider import File
from cecog.io.dataprovider import trajectory_features, TerminalObjectItem, ObjectItem
from pdk.datetimeutils import StopWatch



#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#
import types
def MixIn(pyClass, mixInClass, makeAncestor=0):
    if makeAncestor:
        if mixInClass not in pyClass.__bases__:
            pyClass.__bases__ = pyClass.__bases__ + (mixInClass,)
    else:
        # Recursively traverse the mix-in ancestor
        # classes in order to support inheritance
        baseClasses = list(mixInClass.__bases__)
        baseClasses.reverse()
        for baseClass in baseClasses:
            MixIn(pyClass, baseClass)
        # Install the mix-in methods into the class
        for name in dir(mixInClass):
            if not name.startswith('__'):
            # skip private members
                member = getattr(mixInClass, name)
                if type(member) is types.MethodType:
                    member = member.im_func
                setattr(pyClass, name, member)



        
class ZoomedQGraphicsView(QtGui.QGraphicsView):  
    def wheelEvent(self, event):
        keys = QtGui.QApplication.keyboardModifiers()
        k_ctrl = (keys == QtCore.Qt.ControlModifier)

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
            
class PositionThumbnailBase(QtGui.QLabel):
    item_length = 10
    item_height = 2
    css = 'background-color: transparent; font: white;'
    
    
    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)
        self.parent = parent
        self.setText('Position thumbnail base')
        self.setStyleSheet(self.css)
    
    def mouseDoubleClickEvent(self, *args, **kwargs):
        QtGui.QLabel.mouseDoubleClickEvent(self, *args, **kwargs)
        self.parent.clicked.emit(self.position_key)
        
class PositionThumbnailEvents(PositionThumbnailBase):
    item_length = 10
    item_height = 2
    name = 'Standard'
    
    def __init__(self, position_key, position, parent=None):
        PositionThumbnailBase.__init__(self, parent)
        self.parent = parent
        self.position_key = position_key
        events = position.get_sorted_objects('event', 'state_periods', 2,3,4)
        
        thumbnail_pixmap = QtGui.QPixmap(20*self.item_length, len(events)*self.item_height)
        thumbnail_pixmap.fill(QtCore.Qt.black)
        painter = QtGui.QPainter()
        
        painter.begin(thumbnail_pixmap)
        
        for r, event in enumerate(events):
            for c, pp in enumerate(event.children()):
                line_pen = QtGui.QPen(QtGui.QColor(pp.class_color))
                line_pen.setWidth(self.item_height)
                painter.setPen(line_pen)
                painter.drawLine(c*self.item_length, r*self.item_height, 
                                 (c+1)*self.item_length, r*self.item_height)
        painter.end()
            
        self.height = thumbnail_pixmap.height()
        self.setPixmap(thumbnail_pixmap)
        self.setStyleSheet(self.css)
        self.setToolTip('Sample %s\nPlate %s \nExperiment %s\nPosition %s' % position_key)
        self.setMinimumHeight(self.height)
    
    def mouseDoubleClickEvent(self, *args, **kwargs):
        QtGui.QLabel.mouseDoubleClickEvent(self, *args, **kwargs)
        self.parent.clicked.emit(self.position_key)
        
class PositionThumbnailEvents2(PositionThumbnailBase):
    item_length = 10
    item_height = 2
    name = 'Metaphase count'
    
    def __init__(self, position_key, position, parent=None):
        PositionThumbnailBase.__init__(self, parent)
        self.parent = parent
        self.position_key = position_key
        
        events = position.get_objects('event')
        cnt = 0
        for event in events:
            for pp in event.children():
                if pp.predicted_class == 3:
                    cnt += 1
                
        self.setText('Metaphase count:<br/> <span style=" font-size:32pt; font-weight:600; color: white;">%03d</span>' % cnt)
            
        self.setToolTip('Sample %s\nPlate %s \nExperiment %s\nPosition %s' % position_key)
    
    def mouseDoubleClickEvent(self, *args, **kwargs):
        QtGui.QLabel.mouseDoubleClickEvent(self, *args, **kwargs)
        self.parent.clicked.emit(self.position_key)
        
        
    
            
class TrackletThumbnailList(QtGui.QWidget):
    css = '''background-color: transparent; 
             color: white; 
             font: bold 12px;
             min-width: 10em; 
          '''
    clicked = QtCore.pyqtSignal(tuple)
    
    def __init__(self, data_provider, ThumbClass=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.main_layout = QtGui.QHBoxLayout()
        
        if ThumbClass is None:
            ThumbClass = PositionThumbnailEvents
        
        
        for position_key in data_provider.positions:
            tn_position = ThumbClass(position_key, data_provider[position_key], self)
            tn_widget = QtGui.QWidget(self)
            tn_layout = QtGui.QVBoxLayout()
            tn_layout.addWidget(QtGui.QLabel('%s %s' % (position_key[1], position_key[3])))
            tn_layout.addWidget(tn_position)
            tn_layout.addStretch()
            tn_widget.setLayout(tn_layout)
            self.main_layout.addWidget(tn_widget)
            
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)

        self.setStyleSheet(self.css)
        
    def paintEvent(self, event):
        opt = QtGui.QStyleOption();
        opt.init(self);
        p = QtGui.QPainter(self);
        self.style().drawPrimitive(QtGui.QStyle.PE_Widget, opt, p, self)

class TrackletBrowser(QtGui.QWidget):
    css = '''
                QMenu {color: white;}
                QAction {color: white;}
                QPushButton, QComboBox {background-color: black;
                             border-style: outset;
                             border-width: 2px;
                             border-radius: 4px;
                             border-color: white;
                             color: white;
                             font: bold 14px;
                             min-width: 10em;
                             padding: 2px;}
                QPushButton :pressed {
                             background-color: rgb(50, 50, 50);
                             border-style: inset;}
                QScrollBar:horizontal {
                             border: 2px solid grey;
                             background: black;}
                QGroupBox {background-color: transparent;
                             color: white;
                             font: italic 12px;
                             border-radius: 4px;
                             border-style: dotted;
                             border-width: 2px;
                             border-color: #777777;
                             padding: 6px;}
            '''
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.data_provider = None
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        
        self.view = ZoomedQGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        
        self.view.setStyleSheet(self.css)
        
        self.main_layout = QtGui.QVBoxLayout()
        self.setLayout(self.main_layout)
 
        self.main_layout.addWidget(self.view)
        
        self.thumbnails_scroll = None
        self.thumbnails = None
        
        self.view_hud_layout = QtGui.QHBoxLayout(self.view)
        self.view_hud_layout.addStretch()
        self.view_hud_btn_layout = QtGui.QVBoxLayout()
        self.view_hud_layout.addLayout(self.view_hud_btn_layout)
        
        
        # Objects
        gb2 = QtGui.QGroupBox('Objects')
        gb2_layout = QtGui.QVBoxLayout()
        self.cmb_object_type = QtGui.QComboBox()
        self.cmb_object_type.addItems(['event', 'primary__primary','secondary__expanded'])
        self.cmb_object_type.currentIndexChanged[str].connect(self.change_object_type) 
        gb2_layout.addWidget(self.cmb_object_type)
        gb2.setLayout(gb2_layout)
        self.view_hud_btn_layout.addWidget(gb2)
        
        # Sorting
        gb1 = QtGui.QGroupBox('Sorting')
        gb1_layout = QtGui.QVBoxLayout()
        self.btn_sort_randomly = QtGui.QPushButton('Sort random')
        self.btn_sort_randomly.clicked.connect(self.sortRandomly)
        gb1_layout.addWidget(self.btn_sort_randomly)
        gb1.setLayout(gb1_layout)
        self.view_hud_btn_layout.addWidget(gb1)
        
#        self.btns_sort = []
#        
#        for tf in trajectory_features:
#            temp = QtGui.QPushButton(tf.name)
#            temp.clicked.connect(lambda state, x=tf.name: self.sortTracksByFeature(x))
#            self.btns_sort.append(temp)
#            self.view_hud_btn_layout.addWidget(temp)
            
        
        
        # Galleries
        gb2 = QtGui.QGroupBox('Galleries')
        gb2_layout = QtGui.QVBoxLayout()
        self.cmb_galleries = QtGui.QComboBox()
        self.cmb_galleries.addItems(['primary', 'secondary', 'all', 'off'])
        self.cmb_galleries.currentIndexChanged[str].connect(self.cb_change_gallery_view)   
        gb2_layout.addWidget(self.cmb_galleries)
        gb2.setLayout(gb2_layout)
        self.view_hud_btn_layout.addWidget(gb2)
        
        # Contours
        gb3 = QtGui.QGroupBox('Contours')
        gb3_layout = QtGui.QVBoxLayout()
        
        self.cmb_contours = QtGui.QComboBox()
        self.cmb_contours.addItems(['primary', 'secondary', 'all', 'off'])
        self.cmb_contours.currentIndexChanged[str].connect(self.cb_change_contour_view) 
        gb3_layout.addWidget(self.cmb_contours)
        gb3.setLayout(gb3_layout)
        self.view_hud_btn_layout.addWidget(gb3)
        
        # Selection
        gb4 = QtGui.QGroupBox('Select')
        gb4_layout = QtGui.QVBoxLayout()
        self.cmb_galleries = QtGui.QComboBox()
        self.cmb_galleries.addItems(['all', '10', 'transition 1,2'])
        self.cmb_galleries.currentIndexChanged[str].connect(self.cb_select_trajectories)   
        gb4_layout.addWidget(self.cmb_galleries)
        gb4.setLayout(gb4_layout)
        self.view_hud_btn_layout.addWidget(gb4)
        
        # Class Bars
        gb2 = QtGui.QGroupBox('Bars')
        gb2_layout = QtGui.QVBoxLayout()
        
        self.btn_toggleBars = QtGui.QComboBox()
        self.btn_toggleBars.addItems(['top', 'off', 'secondary intensity'])
        self.btn_toggleBars.currentIndexChanged[str].connect(self.cb_select_bar_type)  
        gb2_layout.addWidget(self.btn_toggleBars)
        gb2.setLayout(gb2_layout)
        self.view_hud_btn_layout.addWidget(gb2)
        
        # alignment
        gb2 = QtGui.QGroupBox('Alignment')
        gb2_layout = QtGui.QVBoxLayout()
        self.cmb_align = QtGui.QComboBox()
        self.cmb_align.addItems(['Left', 'Absolute time', 'Custom'])
        self.cmb_align.currentIndexChanged.connect(self.cb_change_vertical_alignment)   
        gb2_layout.addWidget(self.cmb_align)
        gb2.setLayout(gb2_layout)
        self.view_hud_btn_layout.addWidget(gb2)
        
        self.view_hud_btn_layout.addStretch()
        
        
        
        self.view.setDragMode(self.view.ScrollHandDrag)
        
    def cb_change_gallery_view(self, type):
        if self._root_items is not None:
            for ti in self._root_items:
                ti.set_gallery_view(type)
            self.update_()
            
            
    def cb_change_contour_view(self, type):
        if self._root_items is not None:
            for ti in self._root_items:
                ti.set_contour_view(type)
            self.update_()
            
    def cb_select_bar_type(self, type):
        if self._root_items is not None:
            for ti in self._root_items:
                ti.set_bar_view(type)
            self.update_()
            
        
        
    def cb_select_trajectories(self, type):
        if type == 'all':
            self.selectAll()
        elif type == '10':
            self.selectTenRandomTrajectories()
        elif type == 'transition 1,2':
            self.selectTransition()
        
    def export_to_file(self, filename):
        rect = self.scene.itemsBoundingRect()
        image = QtGui.QImage(rect.width(), rect.height(), QtGui.QImage.Format_RGB32)
        painter = QtGui.QPainter(image);
        self.scene.setSceneRect(rect)
        self.scene.render(painter);
        painter.end()   
        image.save(filename);
        
        
    def show_position(self, position_key, object_name='event'):
        tic = timing.time()
        self.scene.clear()
        self._current_position_key = position_key
        position = self.data_provider[position_key]
        
        self._root_items = []
        events = position.get_objects(object_name)
        
        for event in events.iter(500):
            g_event = event.GraphicsItemType(event)
            g_event.setHandlesChildEvents(False)
            self.scene.addItem(g_event)
            self._root_items.append(g_event)
        print '  Loading events took %5.2f' % (timing.time() - tic)
            
        self.GraphicsItemLayouter = event.GraphicsItemLayouter(self._root_items, self)
            
        self.update_()
        print '  Total Rendering of position took %5.2f' % (timing.time() - tic)
    
    def cb_change_vertical_alignment(self, index): 
        self.GraphicsItemLayouter._align_vertically = index
        self.update_()
        
    def change_object_type(self, object_name):
        self.show_position(self._current_position_key, object_name)
           
    def open_file(self, filename):
        self.data_provider = File(filename)
        self.make_thumbnails()
        
    def remove_thumbnails(self):
        if self.thumbnails_scroll is not None:
            print 'remove_thumbnail()'
            self.main_layout.removeWidget(self.thumbnails_scroll)
            self.thumbnails_scroll.hide()
            self.thumbnails.hide()
            del self.thumbnails_scroll
            del self.thumbnails
            
    def make_thumbnails(self, ThumbClass=None):
        self.remove_thumbnails()
        
        self.thumbnails_scroll = QtGui.QScrollArea(self)
        self.thumbnails_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.thumbnails_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        self.thumbnails = TrackletThumbnailList(self.data_provider, ThumbClass, self.thumbnails_scroll)
        self.thumbnails.clicked.connect(self.show_position)
        self.thumbnails_scroll.setWidget(self.thumbnails)
        
        self.thumbnails_scroll.setMaximumHeight(200)
        self.thumbnails_scroll.setMinimumHeight(200)
        
        self.main_layout.addWidget(self.thumbnails_scroll)
        
        
    def total_height(self):
        return sum([x.height for x in self._root_items])
    
    def update_(self):
        self.GraphicsItemLayouter()
        
     
    def sortTracks(self):   
        for new_row, perm_idx in enumerate(self._permutation):
            self._root_items[perm_idx].moveToRow(new_row)
            
    def sortRandomly(self):
        random.shuffle(self._root_items)
        self.update_()
        
    def sortTracksByFeature(self, feature_name):
        self._root_items.sort(cmp=lambda x,y: cmp(x.object_item[feature_name],y.object_item[feature_name]))
        self.update_()
    
    def showContours(self, state):
        for ti in self._root_items:
            if ti.is_selected:
                ti.showContours(state)
        self.update_()
        
    def selectTenRandomTrajectories(self):
        for ti in self._root_items:
            ti.is_selected = True
        for r in random.sample(range(len(self._root_items)), len(self._root_items) - 10):
            self._root_items[r].is_selected = False
        self.update_()
        
    def selectAll(self):
        for ti in self._root_items:
            ti.is_selected = True
#            ti.moveToColumn(0)
#        self.GraphicsItemLayouter._align_vertically = self.cmb_align.setCurrentIndex(self.GraphicsItemLayouter.ALIGN_LEFT)
        self.update_()
        
    def selectTransition(self):
        for ti in self._root_items:
            ti.is_selected = False
            trans_pos = reduce(lambda x,y: str(x) + str(y), ti.object_item['prediction']).find('01')
            if trans_pos > 0:
                ti.is_selected = True
                ti.column = - (trans_pos + 1)
        self.GraphicsItemLayouter._align_vertically = self.cmb_align.setCurrentIndex(self.GraphicsItemLayouter.ALIGN_CUSTOM)
    
    def reset(self):
        for t in self._root_items:
            t.resetPos()
                    
class GraphicsObjectItemBase(QtGui.QGraphicsItemGroup):
    def __init__(self, parent):
        QtGui.QGraphicsItemGroup.__init__(self, parent)
        self.is_selected = True
        
    def moveToRow(self, row):
        self.row = row
        self.setPos(self.column * self.width, row * self.height)
        
    def moveToColumn(self, col):
        self.column = col
        self.setPos(col * self.width, self.row * self.height)
    
class GraphicsObjectItem(GraphicsObjectItemBase):
    def __init__(self, object_item, parent=None):
        GraphicsObjectItemBase.__init__(self, parent)
        self.object_item = object_item
        
    
    
    
class EventGraphicsItem(GraphicsObjectItem):
    def __init__(self, object_item, parent=None):
        GraphicsObjectItem.__init__(self, object_item, parent)
        
        self.id = CellGraphicsTextItem()
        self.id.setHtml("<span style='color:white; font:bold 32px'> %r </span>" % self.object_item.id)
        
        self.addToGroup(self.id)
        self.sub_items = []
        self.sub_items.append(self.id)
        for col, sub_item in enumerate(object_item.children()):
            g_sub_item = sub_item.GraphicsItemType(sub_item, self)
            g_sub_item.moveToColumn(col+1)
            self.sub_items.append(g_sub_item)
            self.addToGroup(g_sub_item)
            
        self.row = object_item.id
        self.column = 0
        self.height = self.sub_items[1].height
        self.item_length = self.sub_items[1].width
        
        self.bar_feature_item = self.make_feature_plot()
        self.bar_feature_item.setZValue(4)
        self.bar_feature_item.setPos(self.sub_items[1].width, 0)
        self.addToGroup(self.bar_feature_item)
        
        self.set_bar_view('top')
        
    def set_gallery_view(self, type):
        for o in self.sub_items:
            o.set_gallery_view(type)
            
    def set_contour_view(self, type):
        for o in self.sub_items:
            o.set_contour_view(type)
            
    def set_bar_view(self, type):
        self.bar_feature_item.setVisible(False)
        for o in self.sub_items:
            o.set_bar_view('off')
            
        if type == 'top':
            for o in self.sub_items:
                o.set_bar_view('top')
        elif type == 'secondary intensity':
            self.bar_feature_item.setVisible(True)
        
            
        
            
            
            
    @property
    def width(self):
        return self.sub_items[1].width#sum([x.width for x in self.sub_items])
    
    def make_feature_plot(self, feature_idx = 222):
        features = self.object_item.sibling_item_features[:, feature_idx]
        min_, max_ = self.object_item.sibling_item_feature_min_max(feature_idx)

        self.item_cnt = features.shape[0]
        width = self.item_length*self.item_cnt
        
        pixmap = QtGui.QPixmap(width, self.height)
        
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter()
  
        painter.begin(pixmap)

        
        features = ((1 - (features-min_)/(max_ - min_)) * self.height).astype(numpy.uint8)
        
        for col, (f1, f2, obj) in enumerate(zip(features, numpy.roll(features, -1), self.object_item.children())):
            color_ = QtGui.QColor(obj.class_color)
            line_pen = QtGui.QPen(color_)
            line_pen.setWidth(3)
            painter.setPen(line_pen)
            painter.drawLine(col*self.item_length, f1, 
                                 (col+1)*self.item_length -1, f2)
            
        painter.end()
        
        g_item = QtGui.QGraphicsPixmapItem(pixmap)
        return g_item
    

        
             
class GraphicsTerminalObjectItem(GraphicsObjectItemBase):
    def __init__(self, text, parent=None):
        GraphicsObjectItemBase.__init__(self, parent=None)
        
        
    @property
    def width(self):
        return self.object_item.BOUNDING_BOX_SIZE
        
    def set_bar_view(self, type):
        pass
    def set_contour_view(self, type):
        pass
    def set_gallery_view(self, type):
        pass
        
class CellGraphicsItemSettings(object):
    def __init__(self, name):
        self.name = name
        self.enabled = True
        self.show_gallery_image = True
        self.gallery_image_min = 0
        self.gallery_image_max = 255
        self.show_contours = True
        self.show_class_bar = True
        
        self.color = 0
        
        
class CellGraphicsItem(GraphicsTerminalObjectItem):
    PREDICTION_BAR_HEIGHT = 4
    PREDICTION_BAR_X_PADDING = 0
    
    @property
    def width(self):
        return self.object_item.BOUNDING_BOX_SIZE
    
    def set_gallery_view(self, type):
        self.primary_gallery_item.setVisible(False)
        self.secondary_gallery_item.setVisible(False)
        self.composed_gallery_item.setVisible(False)
        self.gallery_view_type = type
#        if type != 'off':
#            self.height = self.width + self.PREDICTION_BAR_HEIGHT 
#        else:
#            self.height = self.PREDICTION_BAR_HEIGHT
            
        if type == 'primary':
            self.primary_gallery_item.setVisible(True)
        elif type == 'secondary':
            self.secondary_gallery_item.setVisible(True)
        elif type == 'all':
            self.composed_gallery_item.setVisible(True)
            
    def set_contour_view(self, type):
        self.primary_contour_item.setVisible(False)
        self.secondary_contour_item.setVisible(False)

        self.contour_view_type = type
#        if type != 'off':
#            self.height = self.width + self.PREDICTION_BAR_HEIGHT 
#        else:
#            self.height = self.PREDICTION_BAR_HEIGHT
            
        if type == 'primary':
            self.primary_contour_item.setVisible(True)
        elif type == 'secondary':
            self.secondary_contour_item.setVisible(True)
        elif type == 'all':
            self.primary_contour_item.setVisible(True)
            self.secondary_contour_item.setVisible(True)
            
    def set_bar_view(self, type):
        self.bar_item.setVisible(False)
        if type == 'top':
            self.bar_item.setVisible(True)

    
    def __init__(self, object_item, parent=None):
        GraphicsTerminalObjectItem.__init__(self, object_item, parent=None)
        self.object_item = object_item
        
        
        primary_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(object_item.image)))
        primary_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
        self.primary_gallery_item = primary_gallery_item
        
        primary_contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), object_item.crack_contour.tolist())))
        primary_contour_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
        primary_contour_item.setPen(QtGui.QPen(QtGui.QColor(object_item.class_color)))
        primary_contour_item.setAcceptHoverEvents(True)
        primary_contour_item.setZValue(3)
        
        self.primary_contour_item = primary_contour_item
        self.addToGroup(primary_contour_item)
        
        sib_object_item = object_item.get_siblings()
        if sib_object_item is not None:
            secondary_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(sib_object_item.image)))
            secondary_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
            self.secondary_gallery_item = secondary_gallery_item
            
            image_sib = sib_object_item.image
            image_own = object_item.image
            new_shape = (object_item.BOUNDING_BOX_SIZE,)*2 + (3,)
            composed_image = numpy.zeros(new_shape, dtype=numpy.uint8)
            composed_image[0:image_own.shape[0],0:image_own.shape[1],0] = image_own
            composed_image[0:image_sib.shape[0],0:image_sib.shape[1],1] = image_sib

            composed_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(composed_image)))
            composed_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
            self.composed_gallery_item = composed_gallery_item
            
            secondary_contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), sib_object_item.crack_contour.tolist())))
            secondary_contour_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
            secondary_contour_item.setPen(QtGui.QPen(QtGui.QColor(sib_object_item.class_color)))
            secondary_contour_item.setAcceptHoverEvents(True)
            secondary_contour_item.setZValue(3)
            
            self.secondary_contour_item = secondary_contour_item
            self.addToGroup(secondary_contour_item)
        
        
        self.addToGroup(primary_gallery_item)
        self.addToGroup(secondary_gallery_item)
        self.addToGroup(composed_gallery_item)
        
        bar_item = QtGui.QGraphicsLineItem(self.PREDICTION_BAR_X_PADDING, 0, self.width - self.PREDICTION_BAR_X_PADDING, 0)
        bar_pen = QtGui.QPen(QtGui.QColor(object_item.class_color))
        bar_pen.setWidth(self.PREDICTION_BAR_HEIGHT)
        bar_item.setPen(bar_pen)
        self.bar_item = bar_item
        self.addToGroup(bar_item)
        
        
        
        
        
        
        
        
        self.row = 0 
        self.column = object_item.time
        self.height = self.width + self.PREDICTION_BAR_HEIGHT 
        
        self.set_gallery_view('primary')
        self.set_contour_view('primary')
        
        

        
class GraphicsLayouterBase(QtGui.QWidget):
    properties = {}
    def __init__(self, items, parent):
        QtGui.QWidget.__init__(self, parent)
        self._items = items     
    def __call__(self):
        'print default layouting'   

class EventGraphicsLayouter(GraphicsLayouterBase):
    properties = {'alignment': 0}
    ALIGN_LEFT = 0
    ALIGN_ABSOLUT_TIME = 1
    ALIGN_CUSTOM = 2
    
    def __init__(self, items, parent):
        GraphicsLayouterBase.__init__(self, items, parent)
        self._align_vertically = self.ALIGN_LEFT
        
    def __call__(self):
        row = 0
        for ti in self._items:
            if ti.is_selected:
                ti.moveToRow(row)
                row += 1
                ti.setVisible(True)
            else:
                ti.setVisible(False)
            if self._align_vertically == self.ALIGN_LEFT:
                ti.moveToColumn(0)
            elif self._align_vertically == self.ALIGN_ABSOLUT_TIME:
                ti.moveToColumn(ti.sub_items[1].object_item.time)
            elif self._align_vertically == self.ALIGN_CUSTOM:
                ti.moveToColumn(ti.column)
        
class CellGraphicsLayouter(GraphicsLayouterBase):
    def __init__(self, items, parent):
        GraphicsLayouterBase.__init__(self, items, parent)
    
    def __call__(self):
        row = 0
        col = 0
        for ti in self._items:
            if ti.is_selected:
                ti.moveToRow(row)
                ti.moveToColumn(col)
                ti.setVisible(True)
                col += 1
            else:
                ti.setVisible(False)
            
            if col > 26:
                row += 1
                col = 0
               
class CellTerminalObjectItemMixin():
    GraphicsItemType = CellGraphicsItem
    GraphicsItemLayouter = CellGraphicsLayouter
    BOUNDING_BOX_SIZE = 100
    
    @property
    def image(self):
        if not hasattr(self, '_image'):
            channel_idx = self.channel_idx
            self._image = self._get_image(self.time, self.local_idx, channel_idx)
            
#            sib = self.get_siblings()
#            if sib is not None:
#                image_sib = sib.image
#                new_shape = (self.BOUNDING_BOX_SIZE,)*2 + (3,)
#                image = numpy.zeros(new_shape, dtype=numpy.uint8)
#                image[0:image_own.shape[0],0:image_own.shape[1],0] = image_own
#                image[0:image_sib.shape[0],0:image_sib.shape[1],1] = image_sib
#            else:
#                image = image_own
#            self._image = image
        
        return self._image 
    
    @property
    def crack_contour(self):
        crack_contour = self._get_crack_contours(self.time, self.local_idx)
        bb = self.bounding_box
        crack_contour[:,0] -= bb[0][0]
        crack_contour[:,1] -= bb[0][1]  
        return crack_contour.clip(0, self.BOUNDING_BOX_SIZE)
    
    @property
    def predicted_class(self):
        # TODO: This can access can be cached by parent
        if not hasattr(self, '_predicted_class'):
            classifier_idx = self.classifier_idx()
            self._predicted_class = self._get_additional_object_data(self.name, 'classifier', classifier_idx) \
                                        ['prediction'][self.idx]
        return self._predicted_class[0]
    
    @property
    def features(self):
        # TODO: This can access can be cached by parent
        if not hasattr(self, '_features'):
            self._features = self._get_additional_object_data(self.name, 'feature')[self.idx,:]
            self._features.shape = (1,) + self._features.shape
        return self._features
    
    @property
    def feature_names(self):
        return self.get_position().object_feature[self.name]
    
    @property
    def time(self):
        return self._local_idx[0]
    
    @property
    def local_idx(self):
        return self._local_idx[1]
    
    def classifier_idx(self):
        return self.get_plate().object_classifier_index[self.name]
    
    @property
    def channel_idx(self):
        if not hasattr(self, '_channel_idx'):
            self._channel_idx = self.get_plate().regions[self.get_position().sub_objects[self.name]]['channel_idx']
        return self._channel_idx
        
    @property
    def bounding_box(self):
        if not hasattr(self, '_bounding_box'):   
            objects = self.parent.object_np_cache['terminals'][self.time]['object']
            self._bounding_box = (objects['upper_left'][self.local_idx], objects['lower_right'][self.local_idx])
        return self._bounding_box
    
    def _get_image(self, t, obj_idx, c, bounding_box=None):
        self.get_position().read_image_data()
        
        if bounding_box is None:
            ul, lr = self.bounding_box
        else:
            ul, lr = bounding_box
        offset_0 = (self.BOUNDING_BOX_SIZE - lr[0] + ul[0])
        offset_1 = (self.BOUNDING_BOX_SIZE - lr[1] + ul[1]) 
        ul[0] = max(0, ul[0] - offset_0/2 - cmp(offset_0%2,0) * offset_0 % 2) 
        ul[1] = max(0, ul[1] - offset_1/2 - cmp(offset_1%2,0) * offset_1 % 2)      
        lr[0] = min(self.get_position()._hf_group_np_copy.shape[4], lr[0] + offset_0/2) 
        lr[1] = min(self.get_position()._hf_group_np_copy.shape[3], lr[1] + offset_1/2) 
        
        self._bounding_box = (ul, lr)
        # TODO: get_iamge returns am image which might have a smaller shape than 
        #       the requested BOUNDING_BOX_SIZE, I dont see a chance to really
        #       fix it, without doing a copy...
        res = self.get_position()._hf_group_np_copy[c, t, 0, ul[1]:lr[1], ul[0]:lr[0]]
        return res

    def _get_crack_contours(self, t, obj_idx):  
        crack_contours_string = self.parent.object_np_cache['terminals'][t]['crack_contours'][obj_idx]                               
        return numpy.asarray(zlib.decompress( \
                             base64.b64decode(crack_contours_string)).split(','), \
                             dtype=numpy.float32).reshape(-1,2)
        
    def _get_object_data(self, t, obj_idx, c):
        bb = self.get_bounding_box(t, obj_idx, c)
        img, new_bb = self.get_image(t, obj_idx, c, bb)
        cc = self.get_crack_contours(t, obj_idx, c)
        cc[:,0] -= new_bb[0][0]
        cc[:,1] -= new_bb[0][1]
        return img, cc
    
    def _get_additional_object_data(self, object_name, data_fied_name, index=None):
        if index is None:
            return self.get_position()._hf_group['object'][object_name][data_fied_name]
        else:
            return self.get_position()._hf_group['object'][object_name][data_fied_name][str(index)]
    
    @property
    def class_color(self):
        if not hasattr(self, '_class_color'):
            classifier = self.get_plate().object_classifier[self.name, self.get_plate().object_classifier_index[self.name]]
            self._class_color = dict(enumerate(classifier['schema']['color'].tolist()))       
        return self._class_color[self.predicted_class]
    
    def compute_features(self):
#        print 'compute feature call for', self.name, self.id  
        pass
    

class EventObjectItemMixin():
    GraphicsItemType = EventGraphicsItem
    GraphicsItemLayouter = EventGraphicsLayouter
    def compute_features(self):
#        print 'compute feature call for', self.name, self.id  
#        for feature in trajectory_features:
#            if isinstance(self, feature.type):
#                self[feature.name] =  feature.compute(self.children())
#                
        self['prediction'] = [x.predicted_class for x in self.children()]
        
    @property
    def item_features(self):
        children = self.children()
        if children is not None:
            return numpy.concatenate([c.features for c in children], axis=0)
        else:
            return None
        
    @property
    def sibling_item_features(self):
        children = self.children()
        if children is not None:
            return numpy.concatenate([c.get_siblings().features for c in children], axis=0)
        else:
            return None
        
    @property
    def item_colors(self):
        children = self.children()
        if children is not None:
            return [c.class_color for c in children]
        else:
            return None
        
    @property
    def item_feature_names(self):
        return self.get_plate().object_feature[self.get_position().sub_objects[self.name]]
    
    def item_feature_min_max(self, feature_idx):
        if not hasattr(self.parent, 'feature_min_max'):
            self.parent.feature_min_max = {}
        
        min_ = 1000000
        max_ = - 1000000
        if feature_idx not in self.parent.feature_min_max.keys():
            for p in self.parent:
                tmin = p.item_features[:,feature_idx].min()
                tmax = p.item_features[:,feature_idx].max()
                
                if tmin < min_:
                    min_ = tmin 
                    
                if tmax > max_:
                    max_ = tmax 
                     
            self.parent.feature_min_max[feature_idx] = min_, max_
            
        return self.parent.feature_min_max[feature_idx]
    
    def sibling_item_feature_min_max(self, feature_idx):
        if not hasattr(self.parent, 'sibling_feature_min_max'):
            self.parent.sibling_feature_min_max = {}
        
        min_ = 1000000
        max_ = - 1000000
        if feature_idx not in self.parent.sibling_feature_min_max.keys():
            for p in self.parent:
                tmin = p.sibling_item_features[:,feature_idx].min()
                tmax = p.sibling_item_features[:,feature_idx].max()
                
                if tmin < min_:
                    min_ = tmin 
                    
                if tmax > max_:
                    max_ = tmax 
                     
            self.parent.sibling_feature_min_max[feature_idx] = min_, max_
            
        return self.parent.sibling_feature_min_max[feature_idx]
            
            
        
        
        
        
MixIn(TerminalObjectItem, CellTerminalObjectItemMixin, True)
MixIn(ObjectItem, EventObjectItemMixin, True)


class CellGraphicsTextItem(QtGui.QGraphicsTextItem, GraphicsTerminalObjectItem):
    def __init__(self, parent=None):
        QtGui.QGraphicsTextItem.__init__(self, parent)
    @property
    def width(self):
        return self.textWidth()
        
        
        
class MainWindow(QtGui.QMainWindow):
    def __init__(self, filename=None, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setStyleSheet('background-color: qlineargradient(x1: 0, y1: 0, x2: 500, y2: 500, stop: 0 #444444, stop: 1 #0A0A0A);') 
        self.setGeometry(100,100,1200,800)
        self.setWindowTitle('tracklet browser')
        
        self.mnu_open = QtGui.QAction('&Open', self)
        self.mnu_open.triggered.connect(self.open_file)
        
        self.mnu_change_view = QtGui.QAction('&Change gallery size', self)
        self.mnu_change_view.triggered.connect(self.change_gallery_size)
        
        file_menu = self.menuBar().addMenu('&File')
        view_menu = self.menuBar().addMenu('&View')
        export_menu = self.menuBar().addMenu('&Export')
        plugin_menu = self.menuBar().addMenu('&Plugin')
        
        pca_comopute = QtGui.QAction('PCA Plots', self)
        pca_comopute.triggered.connect(self.cb_compute_pca)
        plugin_menu.addAction(pca_comopute)
        
        exportSceneAction = QtGui.QAction('Export scene to file', self)
        exportSceneAction.triggered.connect(self.cb_export_scene_to_file)
        export_menu.addAction(exportSceneAction)
        
        file_menu.addAction(self.mnu_open)
        view_menu.addAction(self.mnu_change_view)
        
        thumb_menu = view_menu.addMenu('&Thumbnails')
        

        self.tracklet_widget = TrackletBrowser(self)
        self.setCentralWidget(self.tracklet_widget)  
        
        for ThumbClass in PositionThumbnailBase.__subclasses__():
            a = QtGui.QAction(ThumbClass.name, self)
            a.triggered.connect(partial(self.tracklet_widget.make_thumbnails, ThumbClass))
            thumb_menu.addAction(a)
        
        if filename is not None:
            self.tracklet_widget.open_file(filename)
            
            
    def cb_export_scene_to_file(self):
        filename = QtGui.QFileDialog.getSaveFileName(parent=self, caption='Select image file...')
        if filename:
            self.tracklet_widget.export_to_file(filename)
            
    def cb_compute_pca(self):
        print " *** called ***"
        self._temp_pca = EventPCAPlugin(self.tracklet_widget.data_provider)
        self.setGeometry(100,100,1000,1000)
        self._temp_pca.show()
        self._temp_pca.raise_()
        
        
            
    def closeEvent(self, cevent):
        try:
            if self.tracklet_widget.data_provider is not None:
                self.tracklet_widget.data_provider.close()
                print 'Closing hdf5 file'
        except:
            print 'Could not close file or no file has been open'
        finally:
            cevent.accept()
        
    def change_gallery_size(self):
        val, ok = QtGui.QInputDialog.getInt(self, 'New gallery image size', 'Size', 
                                            value=CellTerminalObjectItemMixin.BOUNDING_BOX_SIZE, 
                                            min=10, 
                                            max=1000)
        if ok:
            CellTerminalObjectItemMixin.BOUNDING_BOX_SIZE = val
            self.tracklet_widget.data_provider.clearObjectItemCache()
                    
            self.tracklet_widget.show_position(self.tracklet_widget._current_position_key)
        
    
        
    def open_file(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self, 'Open hdf5 file', '.', 'hdf5 files (*.h5  *.hdf5)'))  
        if filename:                                              
            self.tracklet_widget.open_file(filename)  
            
            
class EventPCAPlugin(FigureCanvas):
    def __init__(self, data_provider, parent=None, width=8, height=8):
        self.data_provider = data_provider
        
        self.fig = Figure(figsize=(width, height))
        

#        self.axes.hold(False)

        self._run_pca()

        #
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
 
    def _run_pca(self):
        self.feature_matrix = []
        self.item_colors = []
        for position_key in self.data_provider.positions:
            position = self.data_provider[position_key]
            events = position.get_objects('event')
            for t in events.iter_random(500):
                item_features = t.item_features 
                if item_features is not None:
                    self.feature_matrix.append(item_features)
                    
                item_colors = t.item_colors 
                if item_colors is not None:
                    self.item_colors.extend(item_colors)
    
        self.feature_matrix = numpy.concatenate(self.feature_matrix)
            
        nan_index = ~numpy.isnan(self.feature_matrix).any(1)
        self.feature_matrix = self.feature_matrix[nan_index,:]
        self.item_colors = numpy.asarray(self.item_colors)[nan_index]
        print self.feature_matrix.shape, self.item_colors.shape
        
        temp_pca = mlab.PCA(self.feature_matrix)
        result = temp_pca.project(self.feature_matrix)[:,:4]
        
        for cnt, (i,j) in enumerate([(1,2), (1,3), (2,3), (1,4)]):
            self.axes = self.fig.add_subplot(221+cnt)
            
            
            means = kmeans(result[:,[i-1,j-1]], 7)[0]
            
            self.axes.scatter(result[:,i-1], result[:,j-1], c=self.item_colors)
            self.axes.plot(means[:,0], means[:,1], 'or', markeredgecolor='r', markerfacecolor='None', markersize=12, markeredgewidth=3)
            self.axes.set_xlabel('Principle component %d'%i)
            self.axes.set_ylabel('Principle component %d'%j)
            self.axes.set_title('Events in PCA Subspace %d' % (cnt+1))

            
            
            
            
            
            
        
        
def main():
    app = QtGui.QApplication(sys.argv) 
    file, _ = getopt.getopt(sys.argv[1:], 'f:')
    if len(file) == 1:
        file = file[0][1]
    else:
#        file = r'C:\Users\sommerc\data\Chromatin-Microtubles\Analysis\H2b_aTub_MD20x_exp911_2_channels_nozip\dump\_all_positions.hdf5'
        file = r'C:\Users\sommerc\data\Chromatin-Microtubles\Analysis\H2b_aTub_MD20x_exp911_2_channels_nozip\dump_save\_all_positions.hdf5'
        
    mainwindow = MainWindow(file)
    
#    import cProfile, pstats
#    cProfile.run('mainwindow = MainWindow(file)', 'profile-result')
#    ps = pstats.Stats('profile-result')
#    ps.strip_dirs().sort_stats('cumulative').print_stats()
    
    mainwindow.show()
    app.exec_()
    
def test():
    # read tracking information
    tic = timeit.time()
#    f = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump/_all_positions.hdf5')
    f = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump_save/two_positions.hdf5')

    pos = f[f.positions[0]]
    track = pos.get_objects('event')
    feature_matrix = []
    for t in track.iter_random(50):
        item_features = t.item_features 
        if item_features is not None:
            feature_matrix.append(item_features)
    
    feature_matrix = numpy.concatenate(feature_matrix)
    print feature_matrix.shape
            
    print timeit.time() - tic, 'seconds'
        
        
if __name__ == "__main__":
    main()
#    test()


