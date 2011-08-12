"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2011 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
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

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.gui.imageviewer import HoverPolygonItem
from cecog.io.dataprovider import BOUNDING_BOX_SIZE, File
from cecog.io.dataprovider import trajectory_features, TerminalObjectItem, ObjectItem

#-------------------------------------------------------------------------------
# constants:
#
PREDICTION_BAR_HEIGHT = 4
PREDICTION_BAR_X_PADDING = 0
PREDICTION_BAR_Y_PADDING = 2

#-------------------------------------------------------------------------------
# functions:
#
import types
def MixIn(pyClass, mixInClass, makeAncestor=0):
    if makeAncestor:
        if mixInClass not in pyClass.__bases__:
            pyClass.__bases__ = (mixInClass,) + pyClass.__bases__
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




class MainWindow(QtGui.QMainWindow):
    def __init__(self, filename=None, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
         
        self.setGeometry(100,100,1200,700)
        self.setWindowTitle('tracklet browser')
        
        self.mnu_open = QtGui.QAction('&Open', self)
        self.mnu_open.triggered.connect(self.open_file)
        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction(self.mnu_open)

        
        self.tracklet_widget = TrackletBrowser(self)
        self.setCentralWidget(self.tracklet_widget)  
        
        if filename is not None:
            self.tracklet_widget.open_file(filename)
        
    def open_file(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self, 'Open hdf5 file', '.', 'hdf5 files (*.h5  *.hdf5)'))  
        if filename:                                              
            self.tracklet_widget.open_file(filename)
        
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
            
class PositonThumbnail(QtGui.QLabel):
    item_length = 10
    item_height = 3
    css = 'background-color: black;'
    
    def __init__(self, position_key, position, parent=None):
        QtGui.QLabel.__init__(self, parent)
        self.parent = parent
        events = position.get_objects('event')
        self.position_key = position_key
        thumbnail_pixmap = QtGui.QPixmap(20*self.item_length, len(events)*self.item_height)
        thumbnail_pixmap.fill(QtCore.Qt.black)
        painter = QtGui.QPainter()
        painter.begin(thumbnail_pixmap)
        for r, event in enumerate(events):
            for c, pp in enumerate(event.children()):
                line_pen = QtGui.QPen(QtGui.QColor(pp.class_color))
                line_pen.setWidth(3)
                painter.setPen(line_pen)
                painter.drawLine(c*self.item_length, r*self.item_height, 
                                 (c+1)*self.item_length, r*self.item_height)
        painter.end()
            
        self.height = thumbnail_pixmap.height()
        self.setPixmap(thumbnail_pixmap)
        self.setStyleSheet(self.css)
        self.setToolTip('Sample %s\nPlate %s \nExperiment %s\nPosition %s' % position_key)
    
    def mouseDoubleClickEvent(self, *args, **kwargs):
        QtGui.QLabel.mouseDoubleClickEvent(self, *args, **kwargs)
        self.parent.clicked.emit(self.position_key)
        
    
            
class TrackletThumbnailList(QtGui.QWidget):
    css = '* {background-color: black;}'
    clicked = QtCore.pyqtSignal(tuple)
    
    def __init__(self, data_provider, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.main_layout = QtGui.QHBoxLayout()
        
        for position_key in data_provider.positions:
            tn_position = PositonThumbnail(position_key, data_provider[position_key], self)
            self.main_layout.addWidget(tn_position)
            tn_position = PositonThumbnail(position_key, data_provider[position_key], self)
            self.main_layout.addWidget(tn_position)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)
        self.setMinimumHeight(tn_position.height)

        self.setStyleSheet(self.css)
        
    def paintEvent(self, event):
        opt = QtGui.QStyleOption();
        opt.init(self);
        p = QtGui.QPainter(self);
        self.style().drawPrimitive(QtGui.QStyle.PE_Widget, opt, p, self);

        
        
        
        
        

class TrackletBrowser(QtGui.QWidget):
    css = '''QPushButton, QComboBox {background-color: transparent;
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
            
                     '''
    ALIGN_LEFT = 0
    ALIGN_ABSOLUT_TIME = 1
    ALIGN_CUSTOM = 2
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        
        self.view = ZoomedQGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        
        self.view.setStyleSheet(self.css)
        
        self.main_layout = QtGui.QVBoxLayout()
        self.setLayout(self.main_layout)
        
#        self.navi_widget = QtGui.QToolBox()
#        
#        self.sample_group_box_layout = QtGui.QVBoxLayout()
#        self.position_group_box_layout = QtGui.QVBoxLayout()
#        self.experiment_group_box_layout = QtGui.QVBoxLayout()
#        self.object_group_box_layout = QtGui.QVBoxLayout()
#        
#        self.sample_group_box = QtGui.QGroupBox('Sample')
#        self.sample_group_box.setLayout(self.sample_group_box_layout)
#        self.position_group_box = QtGui.QGroupBox('Position')
#        self.position_group_box.setLayout(self.position_group_box_layout)
#        self.experiment_group_box = QtGui.QGroupBox('Experiment')
#        self.experiment_group_box.setLayout(self.experiment_group_box_layout)
#        self.object_group_box = QtGui.QGroupBox('Objects')
#        self.object_group_box.setLayout(self.object_group_box_layout)
#        
#        self.drp_sample = QtGui.QSpinBox()
#        self.sample_group_box_layout.addWidget(self.drp_sample)
#        
#        self.drp_position = QtGui.QSpinBox()
#        self.position_group_box_layout.addWidget(self.drp_position)
#        
#        self.drp_experiment = QtGui.QSpinBox()
#        self.experiment_group_box_layout.addWidget(self.drp_experiment)
#        
#        self.drp_object = QtGui.QComboBox()
#        self.object_group_box_layout.addWidget(self.drp_object)
#        
#        self.navi_content_widget = QtGui.QWidget()
#        self.navi_content_layout = QtGui.QVBoxLayout()
#        self.navi_content_layout.addWidget(self.sample_group_box)
#        self.navi_content_layout.addWidget(self.position_group_box)
#        self.navi_content_layout.addWidget(self.experiment_group_box)
#        self.navi_content_layout.addWidget(self.object_group_box)
#        self.navi_content_layout.addStretch()
#        self.navi_content_widget.setLayout(self.navi_content_layout)
#        
#        self.navi_widget.addItem(self.navi_content_widget, 'Navigaton')
#      
#        self.navi_widget.setMaximumWidth(150)
#        
#        self.main_layout.addWidget(self.navi_widget)
        self.main_layout.addWidget(self.view)
        
        self.view_hud_layout = QtGui.QHBoxLayout(self.view)
        self.view_hud_btn_layout = QtGui.QVBoxLayout()
        self.view_hud_layout.addLayout(self.view_hud_btn_layout)
        
        self.btn_sort_randomly = QtGui.QPushButton('Sort random')
        self.btn_sort_randomly.clicked.connect(self.sortRandomly)
        self.view_hud_btn_layout.addWidget(self.btn_sort_randomly)
        
        self.btns_sort = []
        
        for tf in trajectory_features:
            temp = QtGui.QPushButton(tf.name)
            temp.clicked.connect(lambda state, x=tf.name: self.sortTracksByFeature(x))
            self.btns_sort.append(temp)
            self.view_hud_btn_layout.addWidget(temp)
            
        self.btn_toggle_contours = QtGui.QPushButton('Toggle contours')
        self.btn_toggle_contours.setCheckable(True)
        self.btn_toggle_contours.setChecked(True)

        self.view_hud_btn_layout.addWidget(self.btn_toggle_contours)
        
        self.btn_selectTen = QtGui.QPushButton('Select 10')
        self.btn_selectTen.clicked.connect(self.selectTenRandomTrajectories)
        self.view_hud_btn_layout.addWidget(self.btn_selectTen)
        
        self.btn_selectAll = QtGui.QPushButton('Select All')
        self.btn_selectAll.clicked.connect(self.selectAll)
        self.view_hud_btn_layout.addWidget(self.btn_selectAll)
        
        self.btn_selectTransition = QtGui.QPushButton('Select Transition 0,1')
        self.btn_selectTransition.clicked.connect(self.selectTransition)
        self.view_hud_btn_layout.addWidget(self.btn_selectTransition)
        
        self.btn_toggleBars = QtGui.QPushButton('Toggle Bars')
        self.btn_toggleBars.setCheckable(True)
        self.btn_toggleBars.setChecked(True)
        self.btn_toggleBars.toggled.connect(self.showGalleryImage)
        self.view_hud_btn_layout.addWidget(self.btn_toggleBars)
        
        self.cmb_align = QtGui.QComboBox()
        self.cmb_align.addItems(['Left', 'Absolute time', 'Custom'])
        self.cmb_align.currentIndexChanged.connect(self.cb_change_vertical_alignment)        
        self.view_hud_btn_layout.addWidget(self.cmb_align)
        
        self.view_hud_btn_layout.addStretch()
        
        self.btn_toggle_contours.toggled.connect(self.toggle_contours)
        
        self.view_hud_layout.addStretch()
        
        self.view.setDragMode(self.view.ScrollHandDrag)
        
        self._align_vertically = self.ALIGN_LEFT
        
        
    def show_position(self, position_key):
        self.scene.clear()
        position = self.data_provider[position_key]
        
        self._root_items = []
        events = position.get_objects('event')
        for event in events:
            g_event = event.GraphicsItemType(event)
            g_event.setHandlesChildEvents(False)
            self.scene.addItem(g_event)
            self._root_items.append(g_event)
            
        self.update_()
    
    def cb_change_vertical_alignment(self, index): 
        self._align_vertically = index
        self.update_()
           
    def open_file(self, filename):
        self.data_provider = File(filename)
        self.thumbnails = TrackletThumbnailList(self.data_provider, self)
        self.thumbnails.clicked.connect(self.show_position)
        self.main_layout.addWidget(self.thumbnails)
        
        
    def total_height(self):
        return sum([x.height for x in self._root_items])
    
    def update_(self):
        row = 0
        for ti in self._root_items:
            if ti.is_selected:
                ti.moveToRow(row)
                row += 1
                ti.setVisible(True)
            else:
                ti.setVisible(False)
            if self._align_vertically == self.ALIGN_LEFT:
                ti.moveToColumn(0)
            elif self._align_vertically == self.ALIGN_ABSOLUT_TIME:
                ti.moveToColumn(ti.sub_items[0].object_item.time)
            elif self._align_vertically == self.ALIGN_CUSTOM:
                ti.moveToColumn(ti.column)
        
    def showGalleryImage(self, state):
        for ti in self._root_items:
            ti.showGalleryImage(state)
        self.update_()
            
    def sortTracks(self):   
        for new_row, perm_idx in enumerate(self._permutation):
            self._root_items[perm_idx].moveToRow(new_row)
            
    def sortRandomly(self):
        random.shuffle(self._root_items)
        self.update_()
        
    def sortTracksByFeature(self, feature_name):
        self._root_items.sort(cmp=lambda x,y: cmp(x.object_item[feature_name],y.object_item[feature_name]))
        self.update_()
    
    def toggle_contours(self, state):
        toggle_visibility = lambda x: x.setContoursVisible(state)
        map(toggle_visibility, self._root_items)
        
    def selectTenRandomTrajectories(self):
        for ti in self._root_items:
            ti.is_selected = True
        for r in random.sample(range(len(self._root_items)), len(self._root_items) - 10):
            self._root_items[r].is_selected = False
        self.update_()
        
    def selectAll(self):
        for ti in self._root_items:
            ti.is_selected = True
            ti.moveToColumn(0)
        self._align_vertically = self.cmb_align.setCurrentIndex(self.ALIGN_LEFT)
        
    def selectTransition(self):
        for ti in self._root_items:
            ti.is_selected = False
            trans_pos = reduce(lambda x,y: str(x) + str(y), ti['prediction']).find('01')
            if trans_pos > 0:
                ti.is_selected = True
                ti.column = - (trans_pos + 1)
        self._align_vertically = self.cmb_align.setCurrentIndex(self.ALIGN_CUSTOM)
    
    def reset(self):
        for t in self._root_items:
            t.resetPos()
               
            
class GraphicsObjectItemBase(QtGui.QGraphicsItemGroup):
    def moveToRow(self, row):
        self.row = row
        self.setPos(self.column * BOUNDING_BOX_SIZE, row * self.height)
        
    def moveToColumn(self, col):
        self.column = col
        self.setPos(col * BOUNDING_BOX_SIZE, self.row * self.height)  
        
    @property
    def is_selected(self):
        return True
    
class GraphicsObjectItem(GraphicsObjectItemBase):
    def __init__(self, object_item, parent=None):
        GraphicsObjectItemBase.__init__(self, parent)
        self.object_item = object_item
        
    
class EventGraphicsItem(GraphicsObjectItem):
    def __init__(self, object_item, parent=None):
        GraphicsObjectItem.__init__(self, object_item, parent)
    
        self.sub_items = []
        for col, sub_item in enumerate(object_item.children()):
            g_sub_item = sub_item.GraphicsItemType(sub_item, self)
            g_sub_item.moveToColumn(col)
            self.sub_items.append(g_sub_item)
            self.addToGroup(g_sub_item)
        self.row = object_item.id
        self.column = 0
        self.height = BOUNDING_BOX_SIZE + PREDICTION_BAR_HEIGHT
        
             
class GraphicsTerminalObjectItem(GraphicsObjectItemBase):
    def __init__(self, object_item, parent=None):
        GraphicsObjectItemBase.__init__(self, parent=None)
        self.object_item = object_item
        
class CellGraphicsItem(GraphicsTerminalObjectItem):
    def __init__(self, object_item, parent=None):
        GraphicsTerminalObjectItem.__init__(self, object_item, parent=None)
        gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(object_item.image)))
        
        bar_item = QtGui.QPixmap(BOUNDING_BOX_SIZE - 2 * PREDICTION_BAR_X_PADDING, PREDICTION_BAR_HEIGHT)
        bar_item.fill(QtGui.QColor(object_item.class_color))
        bar_item = QtGui.QGraphicsPixmapItem(bar_item)
        bar_item.setPos(PREDICTION_BAR_X_PADDING, 0) 
        
        contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), object_item.crack_contour.tolist())))
        contour_item.setPos(0, PREDICTION_BAR_HEIGHT)
        contour_item.setPen(QtGui.QPen(QtGui.QColor(object_item.class_color)))
        contour_item.setAcceptHoverEvents(True)
        
        self.addToGroup(gallery_item)
        self.addToGroup(bar_item)
        self.addToGroup(contour_item)
        
        self.row = 0 
        self.column = object_item.time
        self.height = BOUNDING_BOX_SIZE + PREDICTION_BAR_HEIGHT 
        
class CellTerminalObjectItemMixin(object):
    GraphicsItemType = CellGraphicsItem
    @property
    def image(self):
        channel_idx = self.channel_idx()
        image_own, self._bounding_box = self._get_image(self.time, self.local_idx, channel_idx)
        
        sib = self.get_siblings()
        if sib is not None:
            image_sib = sib.image
            new_shape = (BOUNDING_BOX_SIZE,)*2 + (3,)
            image = numpy.zeros(new_shape, dtype=numpy.uint8)
            image[0:image_own.shape[0],0:image_own.shape[1],0] = image_own
            image[0:image_sib.shape[0],0:image_sib.shape[1],1] = image_sib
        else:
            image = image_own
        
        return image 
    @property
    def crack_contour(self):
        crack_contour = self._get_crack_contours(self.time, self.local_idx)
        crack_contour[:,0] -= self._bounding_box[0][0]
        crack_contour[:,1] -= self._bounding_box[0][1]  
        return crack_contour.clip(0, BOUNDING_BOX_SIZE)
    @property
    def predicted_class(self):
        # TODO: This can access can be cached by parent
        if not hasattr(self, '_predicted_class'):
            classifier_idx = self.classifier_idx()
            self._predicted_class = self._get_additional_object_data(self.name, 'classifier', classifier_idx) \
                                        ['prediction'][self.idx]
        return self._predicted_class[0]
    @property
    def time(self):
        return self._local_idx[0]
    @property
    def local_idx(self):
        return self._local_idx[1]
    
    def classifier_idx(self):
        return self.get_position.object_classifier_index[self.name]
    
    def channel_idx(self):
        return self.get_position.regions[self.get_position.sub_objects[self.name]]['channel_idx']
        
    def _get_bounding_box(self, t, obj_idx, c=0):
        objects = self.parent.object_np_cache['terminals'][t]['object']
        return (objects['upper_left'][obj_idx], objects['lower_right'][obj_idx])
    
    def _get_image(self, t, obj_idx, c, bounding_box=None, min_bounding_box_size=BOUNDING_BOX_SIZE):
        if bounding_box is None:
            ul, lr = self._get_bounding_box(t, obj_idx, c)
        else:
            ul, lr = bounding_box
        
        offset_0 = (min_bounding_box_size - lr[0] + ul[0])
        offset_1 = (min_bounding_box_size - lr[1] + ul[1]) 
        
        ul[0] = max(0, ul[0] - offset_0/2 - cmp(offset_0%2,0) * offset_0 % 2) 
        ul[1] = max(0, ul[1] - offset_1/2 - cmp(offset_1%2,0) * offset_1 % 2)  
        
        lr[0] = min(self.get_position._hf_group_np_copy.shape[4], lr[0] + offset_0/2) 
        lr[1] = min(self.get_position._hf_group_np_copy.shape[3], lr[1] + offset_1/2) 
        
        bounding_box = (ul, lr)
        
        # TODO: get_iamge returns am image which might have a smaller shape than 
        #       the requested BOUNDING_BOX_SIZE, I dont see a chance to really
        #       fix it, without doing a copy...
        
        return self.get_position._hf_group_np_copy[c, t, 0, ul[1]:lr[1], ul[0]:lr[0]], bounding_box

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
    
    def _get_additional_object_data(self, object_name, data_fied_name, index):
        return self.get_position._hf_group['object'][object_name][data_fied_name][str(index)]
    @property
    def class_color(self):
        if not hasattr(self, '_CLASS_TO_COLOR'):
            classifier = self.get_position.object_classifier[self.name, self.get_position.object_classifier_index[self.name]]
            self._class_color = dict(enumerate(classifier['schema']['color'].tolist()))       
        return self._class_color[self.predicted_class]
    
    def compute_features(self):
        pass
    
    

class EventObjectItemMixin(object):
    GraphicsItemType = EventGraphicsItem
    def compute_features(self):
        for feature in trajectory_features:
            if isinstance(self, feature.type):
                self[feature.name] =  feature.compute(self.children())

MixIn(TerminalObjectItem, CellTerminalObjectItemMixin)
MixIn(ObjectItem, EventObjectItemMixin)

#        
#
#class GraphicsTrajectoryGroup(QtGui.QGraphicsItemGroup):
#    class GraphicsTrajectoryItem(object):
#        def __init__(self, gallery_item, contour_item, bar_item, is_visible=True):
#            self.gallery_item = gallery_item
#            self.contour_item = contour_item
#            self.bar_item = bar_item
#
#    def __init__(self, column, row, trajectory, parent=None):
#        QtGui.QGraphicsItemGroup.__init__(self, parent)
#        self._row = row
#        self.row = row
#        self._column = column
#        self.column = column
#        
#        self.is_selected = True
#        self._features = {}
#        
#        self['prediction'] = []
#        self._show_gallery_image = True
#        
#        self._items = []
#        
#        self.start_time = trajectory[0].time
#        
#        for col, t_item in enumerate(trajectory):
#            gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(t_item.image)))
#            gallery_item.setPos(col * BOUNDING_BOX_SIZE, PREDICTION_BAR_HEIGHT)
#            
#            self['prediction'].append(t_item.predicted_class)
#            bar_item = QtGui.QPixmap(BOUNDING_BOX_SIZE - 2 * PREDICTION_BAR_X_PADDING, PREDICTION_BAR_HEIGHT)
#            bar_item.fill(QtGui.QColor(t_item.class_color))
#            bar_item = QtGui.QGraphicsPixmapItem(bar_item)
#            bar_item.setPos(col*BOUNDING_BOX_SIZE + PREDICTION_BAR_X_PADDING, 0) 
#            
#            contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), t_item.crack_contour.tolist())))
#            contour_item.setPos(col*BOUNDING_BOX_SIZE, PREDICTION_BAR_HEIGHT)
#            contour_item.setPen(QtGui.QPen(QtGui.QColor(t_item.class_color)))
#            
#            contour_item.setAcceptHoverEvents(True)
#            
#            self.addToGroup(gallery_item)
#            self.addToGroup(bar_item)
#            self.addToGroup(contour_item)
#            
#            self._items.append(self.GraphicsTrajectoryItem(gallery_item, contour_item, bar_item))
#                
#            for tf in trajectory_features:
#                self[tf.name] =  tf.compute(trajectory)
#        
#        id_item = QtGui.QGraphicsTextItem('%03d' % row)
#        id_item.setPos( (col+1) * BOUNDING_BOX_SIZE, 0)
#        id_item.setDefaultTextColor(QtCore.Qt.white)
#        id_item.setFont(QtGui.QFont('Helvetica', 24))
#        self.addToGroup(id_item)
#        self.id_item = id_item
#        
#    
#      
#        
#    def __getitem__(self, key):
#        return self._features[key]
#    
#    def __setitem__(self, key, value):
#        self._features[key] = value
#        
#    def areContoursVisible(self):
#        return self._items[0].contour_item.isVisible()
#    
#    def setContoursVisible(self, state):
#        if self._show_gallery_image:
#            for i in self._items:
#                i.contour_item.setVisible(state)
#        
#    def resetPos(self):
#        self.moveToColumn(self._column)
#        self.moveToRow(self._row)
#        
#    @property
#    def height(self):
#        if self._show_gallery_image:
#            return PREDICTION_BAR_HEIGHT + BOUNDING_BOX_SIZE
#        else:
#            return PREDICTION_BAR_HEIGHT + PREDICTION_BAR_Y_PADDING
#        
#    def showGalleryImage(self, state):
#        self._show_gallery_image = state
#        for i in self._items:
#            i.gallery_item.setVisible(state)
#            i.contour_item.setVisible(state)
#        self.id_item.setFont(QtGui.QFont('Helvetica', [24 if state else 8][0])) 
        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv) 
    file, _ = getopt.getopt(sys.argv[1:], 'f:')
    if len(file) == 1:
        file = file[0][1]
    else:
        file = None
        
    mainwindow = MainWindow(file)
    
#    import cProfile, pstats
#    cProfile.run('mainwindow = MainWindow(file)', 'profile-result')
#    ps = pstats.Stats('profile-result')
#    ps.strip_dirs().sort_stats('cumulative').print_stats()
    
    mainwindow.show()
    app.exec_()

