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
try:
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    sip.setapi('QUrl', 2)
except:
    print 'Warning: Could not set Qt API to versoin 2'

from PyQt4 import QtGui, QtCore
import zlib
import base64


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
from cecog.io.hdfcore import CH5File, GALLERY_SIZE
from cecog.gui.cellbroser_core import TerminalObjectItem, ObjectItem
from pdk.datetimeutils import StopWatch
from cecog.gui.cellbrowser_plugins import EventPCAPlugin



#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#




        
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
        events = position.get_events()
        if len(events) > 0:
            thumbnail_pixmap = QtGui.QPixmap(20*self.item_length, len(events)*self.item_height)
            thumbnail_pixmap.fill(QtCore.Qt.white)
            painter = QtGui.QPainter()
            
            painter.begin(thumbnail_pixmap)
            
            for r, event in enumerate(events):
                for c, pp in enumerate(event):
                    line_pen = QtGui.QPen(QtGui.QColor(str(position.get_class_color(tuple(position.get_class_label(pp)))[0])))
                    line_pen.setWidth(self.item_height)
                    painter.setPen(line_pen)
                    painter.drawLine(c*self.item_length, r*self.item_height, 
                                     (c+1)*self.item_length, r*self.item_height)
            painter.end()
                
            self.height = thumbnail_pixmap.height()

            self.setPixmap(thumbnail_pixmap)
            self.setStyleSheet(self.css)
            self.setToolTip('%s %s %s %s' % position_key)
            self.setMinimumHeight(self.height)
        else:
            self.setText('No thumbnail\navailable...')
    
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
        
        
        for well_key, pos_keys in data_provider.positions.items():
            for pos_key in pos_keys:
                tn_position = ThumbClass(('0', '0', well_key, pos_key), data_provider.get_position(well_key, pos_key), self)
                tn_widget = QtGui.QWidget(self)
                tn_layout = QtGui.QVBoxLayout()
                tn_layout.addWidget(QtGui.QLabel('%s_%s' % (well_key, pos_key)))
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
        
        
def GraphicsItemType(object_item):
    if type(object_item) == TerminalObjectItem:
        return CellGraphicsItem(object_item)
    elif type(object_item) == ObjectItem:
        return EventGraphicsItem(object_item)
    else:
        raise RuntimeError('GraphicsItemType(): No graphics item type specified for object item %s' % type(object_item))
    
def GraphicsItemLayouter(object_type):
    if object_type == TerminalObjectItem:
        return CellGraphicsLayouter
    elif object_type == ObjectItem:
        return EventGraphicsLayouter
    else:
        raise RuntimeError('GraphicsItemLayouter(): No graphics layouter specified for object type %s' % object_type)

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
        self.cmb_object_type.addItems(['event', 'track', 'primary__primary','secondary__expanded'])
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
        
        
    def show_position(self, position_key):
        tic = timing.time()
        self.scene.clear()
        self._current_position_key = position_key
        position = self.data_provider.get_position(position_key[2], position_key[3])
        
        self._root_items = []
        events = position.get_events()
        
        for kk, event in enumerate(events):
            g_event = EventGraphicsItem(kk, event, position)
            g_event.setHandlesChildEvents(False)
            self.scene.addItem(g_event)
            self._root_items.append(g_event)
            
        print '  Loading events took %5.2f' % (timing.time() - tic)
            
        self.GraphicsItemLayouter = EventGraphicsLayouter(self)
            
        self.update_()
        print '  Total Rendering of position took %5.2f' % (timing.time() - tic)
    
    def cb_change_vertical_alignment(self, index): 
        self.GraphicsItemLayouter._align_vertically = index
        self.update_()
        
    def change_object_type(self, object_name):
        self.show_position(self._current_position_key, object_name)
           
    def open_file(self, filename):
        self.data_provider = CH5File(filename)
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
                    
class GraphicsLayouterBase(QtGui.QWidget):
    properties = {}
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self._items = parent._root_items     
    def __call__(self):
        print 'print default layouting'   

class EventGraphicsLayouter(GraphicsLayouterBase):
    properties = {'alignment': 0}
    ALIGN_LEFT = 0
    ALIGN_ABSOLUT_TIME = 1
    ALIGN_CUSTOM = 2
    
    def __init__(self, parent):
        GraphicsLayouterBase.__init__(self, parent)
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
        GraphicsLayouterBase.__init__(self, parent)
    
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
    def __init__(self, object_item, position, parent=None):
        GraphicsObjectItemBase.__init__(self, parent)
        self.object_item = object_item
        self.position = position
        
    
    
    
class EventGraphicsItem(GraphicsObjectItem):
    def __init__(self, idx, object_item, position, parent=None):
        GraphicsObjectItem.__init__(self, object_item, position, parent)
        
        self.id = CellGraphicsTextItem()
        self.id.setHtml("<span style='color:white; font:bold 32px'> %r </span>" % idx)
        
        self.addToGroup(self.id)
        self.sub_items = []
        self.sub_items.append(self.id)
        for col, sub_item in enumerate(object_item):
            g_sub_item = CellGraphicsItem(sub_item, position)
            g_sub_item.moveToColumn(col+1)
            self.sub_items.append(g_sub_item)
            self.addToGroup(g_sub_item)
            
        self.row = idx
        self.column = 0
        self.height = self.sub_items[1].height
        self.item_length = self.sub_items[1].width
        
#        self.bar_feature_item = self.make_feature_plot()
#        self.bar_feature_item.setZValue(4)
#        self.bar_feature_item.setPos(self.sub_items[1].width, 0)
#        self.addToGroup(self.bar_feature_item)
        
#        self.set_bar_view('top')
        
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
    
    def make_feature_plot(self, feature_idx = 5):
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
            if obj.class_color is None:
                color_ = QtCore.Qt.white
            else:
                color_ = QtGui.QColor()
            line_pen = QtGui.QPen(color_)
            line_pen.setWidth(3)
            painter.setPen(line_pen)
            painter.drawLine(col*self.item_length, f1, 
                                 (col+1)*self.item_length -1, f2)
            
        painter.end()
        
        g_item = QtGui.QGraphicsPixmapItem(pixmap)
        return g_item
    

        
             
class GraphicsTerminalObjectItem(GraphicsObjectItemBase):
    def __init__(self, text, position, parent=None):
        GraphicsObjectItemBase.__init__(self, parent=None)
        self.position = position
        
        
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
        return GALLERY_SIZE
    
    def set_gallery_view(self, type):
        self.primary_gallery_item.setVisible(False)
#        self.secondary_gallery_item.setVisible(False)
#        self.composed_gallery_item.setVisible(False)
        self.gallery_view_type = type
#        if type != 'off':
#            self.height = self.width + self.PREDICTION_BAR_HEIGHT 
#        else:
#            self.height = self.PREDICTION_BAR_HEIGHT
            
        if type == 'primary':
            self.primary_gallery_item.setVisible(True)
#        elif type == 'secondary':
#            self.secondary_gallery_item.setVisible(True)
#        elif type == 'all':
#            self.composed_gallery_item.setVisible(True)
            
    def set_contour_view(self, type):
        self.primary_contour_item.setVisible(False)
#        self.secondary_contour_item.setVisible(False)

        self.contour_view_type = type
#        if type != 'off':
#            self.height = self.width + self.PREDICTION_BAR_HEIGHT 
#        else:
#            self.height = self.PREDICTION_BAR_HEIGHT
            
        if type == 'primary':
            self.primary_contour_item.setVisible(True)
#        elif type == 'secondary':
#            self.secondary_contour_item.setVisible(True)
#        elif type == 'all':
#            self.primary_contour_item.setVisible(True)
#            self.secondary_contour_item.setVisible(True)
            
    def set_bar_view(self, type):
        self.bar_item.setVisible(False)
        if type == 'top':
            self.bar_item.setVisible(True)

    
    def __init__(self, object_item, position, parent=None):
        GraphicsTerminalObjectItem.__init__(self, object_item, position, parent=None)
        self.object_item = object_item
        
        
        primary_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(self.position.get_gallery_image(object_item))))
        primary_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
        self.primary_gallery_item = primary_gallery_item
        
        primary_contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), self.position.get_crack_contour(object_item)[0])))
        primary_contour_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
        primary_contour_item.setPen(QtGui.QPen(QtGui.QColor(str(self.position.get_class_color(tuple(self.position.get_class_label(object_item)))[0]))))
        primary_contour_item.setAcceptHoverEvents(True)
        primary_contour_item.setZValue(4)
        
        self.primary_contour_item = primary_contour_item
        self.addToGroup(primary_contour_item)
        
#        sib_object_item = object_item.get_siblings()
#        if sib_object_item is not None:
#            secondary_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(sib_object_item.image)))
#            secondary_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
#            self.secondary_gallery_item = secondary_gallery_item
#            
#            image_sib = sib_object_item.image
#            image_own = object_item.image
#            new_shape = (object_item.BOUNDING_BOX_SIZE,)*2 + (3,)
#            composed_image = numpy.zeros(new_shape, dtype=numpy.uint8)
#            composed_image[0:image_own.shape[0],0:image_own.shape[1],0] = image_own
#            composed_image[0:image_sib.shape[0],0:image_sib.shape[1],1] = image_sib
#
#            composed_gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(composed_image)))
#            composed_gallery_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
#            self.composed_gallery_item = composed_gallery_item
#            
#            secondary_contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), sib_object_item.crack_contour.tolist())))
#            secondary_contour_item.setPos(0, self.PREDICTION_BAR_HEIGHT)
#            if sib_object_item.class_color is not None:
#                secondary_contour_item.setPen(QtGui.QPen(QtGui.QColor(sib_object_item.class_color)))
#            secondary_contour_item.setAcceptHoverEvents(True)
#            secondary_contour_item.setZValue(3)
#            
#            self.secondary_contour_item = secondary_contour_item
#            self.addToGroup(secondary_contour_item)
        
        
        self.addToGroup(primary_gallery_item)
#        self.addToGroup(secondary_gallery_item)
#        self.addToGroup(composed_gallery_item)
        
        bar_item = QtGui.QGraphicsLineItem(self.PREDICTION_BAR_X_PADDING, 0, self.width - self.PREDICTION_BAR_X_PADDING, 0)
        bar_pen = QtGui.QPen(QtGui.QColor(str(self.position.get_class_color(tuple(self.position.get_class_label(object_item)))[0])))
        bar_pen.setWidth(self.PREDICTION_BAR_HEIGHT)
        bar_item.setPen(bar_pen)
        self.bar_item = bar_item
        self.addToGroup(bar_item)
        
 
        self.row = 0 
        self.column = self.position['object']['primary__primary'][object_item]['time_idx']
        self.height = self.width + self.PREDICTION_BAR_HEIGHT 
        
        self.set_gallery_view('primary')
        self.set_contour_view('primary')

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
                                            value=CellTerminalObjectItem.BOUNDING_BOX_SIZE, 
                                            min=10, 
                                            max=1000)
        if ok:
            CellTerminalObjectItem.BOUNDING_BOX_SIZE = val
            self.tracklet_widget.data_provider.clearObjectItemCache()
                    
            self.tracklet_widget.show_position(self.tracklet_widget._current_position_key)
        
    
        
    def open_file(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self, 'Open hdf5 file', '.', 'hdf5 files (*.h5  *.hdf5)'))  
        if filename:                                              
            self.tracklet_widget.open_file(filename)  
            
            

      
def main():
    app = QtGui.QApplication(sys.argv) 
    file, _ = getopt.getopt(sys.argv[1:], 'f:')
    if len(file) == 1:
        file = file[0][1]
    else:
        file = r'C:\Users\sommerc\cellcognition\pysrc\cecog\io\0038-cs.h5'
        
    mainwindow = MainWindow(file)
    mainwindow.show()
    app.exec_()
    
#def test():
#    # read tracking information
#    tic = timeit.time()
##    f = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump/_all_positions.hdf5')
#    f = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump_save/two_positions.hdf5')
#    pos = f[f.positions[0]]
#    track = pos.get_objects('event')
#    feature_matrix = []
#    for t in track.iter_random(50):
#        item_features = t.item_features 
#        if item_features is not None:
#            feature_matrix.append(item_features)
#    
#    feature_matrix = numpy.concatenate(feature_matrix)
#    print feature_matrix.shape
#            
#    print timeit.time() - tic, 'seconds'
    
        
if __name__ == "__main__":
    main()
#    test()


