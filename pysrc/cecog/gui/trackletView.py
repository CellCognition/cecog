from PyQt4 import QtGui, QtCore
import numpy, vigra
import sys
import random
import qimage2ndarray
import getopt

from cecog.io import dataprovider
from cecog.io.dataprovider import trajectory_features
from cecog.gui.imageviewer import HoverPolygonItem
import copy

BOUNDING_BOX_SIZE = dataprovider.BOUNDING_BOX_SIZE


def argsorted(seq, cmp=cmp, reverse=False):
    temp = enumerate(seq)
    temp_s = sorted(temp, cmp=lambda u,v: cmp(u[1],v[1]), reverse=reverse)
    return [x[0] for x in temp_s]

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
            

class TrackletBrowser(QtGui.QWidget):
    css = '''   QPushButton {background-color: none;
                             border-style: outset;
                             border-width: 2px;
                             border-radius: 4px;
                             border-color: white;
                             color: white;
                             font: bold 14px;
                             min-width: 10em;
                             padding: 2px;}
                QPushButton:pressed {
                             background-color: rgb(50, 50, 50);
                             border-style: inset;}
                     '''
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        
        self.view = ZoomedQGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        
        self.view.setStyleSheet(self.css)
        
        
        self.all_tracks = []
        
        self.main_layout = QtGui.QHBoxLayout()
        self.setLayout(self.main_layout)
        
        self.navi_widget = QtGui.QToolBox()
        
        self.sample_group_box_layout = QtGui.QVBoxLayout()
        self.position_group_box_layout = QtGui.QVBoxLayout()
        self.experiment_group_box_layout = QtGui.QVBoxLayout()
        self.object_group_box_layout = QtGui.QVBoxLayout()
        
        self.sample_group_box = QtGui.QGroupBox('Sample')
        self.sample_group_box.setLayout(self.sample_group_box_layout)
        self.position_group_box = QtGui.QGroupBox('Position')
        self.position_group_box.setLayout(self.position_group_box_layout)
        self.experiment_group_box = QtGui.QGroupBox('Experiment')
        self.experiment_group_box.setLayout(self.experiment_group_box_layout)
        self.object_group_box = QtGui.QGroupBox('Objects')
        self.object_group_box.setLayout(self.object_group_box_layout)
        
        self.drp_sample = QtGui.QSpinBox()
        self.sample_group_box_layout.addWidget(self.drp_sample)
        
        self.drp_position = QtGui.QSpinBox()
        self.position_group_box_layout.addWidget(self.drp_position)
        
        self.drp_experiment = QtGui.QSpinBox()
        self.experiment_group_box_layout.addWidget(self.drp_experiment)
        
        self.drp_object = QtGui.QComboBox()
        self.object_group_box_layout.addWidget(self.drp_object)
        
        self.navi_content_widget = QtGui.QWidget()
        self.navi_content_layout = QtGui.QVBoxLayout()
        self.navi_content_layout.addWidget(self.sample_group_box)
        self.navi_content_layout.addWidget(self.position_group_box)
        self.navi_content_layout.addWidget(self.experiment_group_box)
        self.navi_content_layout.addWidget(self.object_group_box)
        self.navi_content_layout.addStretch()
        self.navi_content_widget.setLayout(self.navi_content_layout)
        
        self.navi_widget.addItem(self.navi_content_widget, 'Navigaton')

        
        
        
        self.navi_widget.setMaximumWidth(150)
        
        self.main_layout.addWidget(self.navi_widget)
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
        

        self.view_hud_btn_layout.addWidget(self.btn_toggle_contours)
        self.view_hud_btn_layout.addStretch()
        
        self.btn_toggle_contours.clicked.connect(self.toggle_contours)
        
 
        self.view_hud_layout.addStretch()
        
#        self.view.setDragMode(self.view.ScrollHandDrag)
        
        
    def open_file(self, filename):
        fh = dataprovider.File(filename)
        self.scene.clear()
        
        outer = []
        for t in fh.traverse_objects('event'):
            inner = []
            for _, data, cc in t:
                inner.append(TrackletItem(data, cc))
            outer.append(inner)
            if len(outer) > 120:
                break
        self.showTracklets(outer)
        
        
    def showTracklets(self, tracklets):
        self._all_contours = []
        for row, t in enumerate(tracklets):
            trackGroup = TrackLetItemGroup(0, row)
            

            for col, ti in enumerate(t):
                scene_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(ti.data)))
                scene_item.setPos(col*BOUNDING_BOX_SIZE,row*BOUNDING_BOX_SIZE)
                
                scene_item_seg = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), ti.crack_contour.tolist())))
                scene_item_seg.setPos(col*BOUNDING_BOX_SIZE,row*BOUNDING_BOX_SIZE)
                
                scene_item_seg.setPen(QtGui.QPen(QtGui.QColor(255,0,0)))
                scene_item_seg.setAcceptHoverEvents(True)
                
                self._all_contours.append(scene_item_seg)
                
                trackGroup.addToGroup(scene_item)
                trackGroup.addToGroup(scene_item_seg)
                
            for tf in trajectory_features:
                trackGroup[tf.name] =  tf.compute(t)
                
            trackGroup.setHandlesChildEvents(False)
            self.scene.addItem(trackGroup)
            self.all_tracks.append(trackGroup)
            
    def sortTracks(self, permutation):        
        for new_row, perm_idx in enumerate(permutation):
            self.all_tracks[perm_idx].moveToRow(new_row)
            
    def sortTracksByFeature(self, feature_name):
        permutation = argsorted([t[feature_name] for t in self.all_tracks], reverse=True)
        self.sortTracks(permutation)
    
    def sortRandomly(self):
        perm = range(len(self.all_tracks))
        random.shuffle(perm)
        self.sortTracks(perm)
        
    def sortByIntensity(self):
        perm = argsorted(self.all_tracks, cmp=lambda u,v: cmp(u.mean_intensity, v.mean_intensity), reverse=True)
        self.sortTracks(perm)
        
    def toggle_contours(self):
        is_visible = self._all_contours[0].isVisible()
        toggle_visibility = lambda x: x.setVisible(not is_visible)
        map(toggle_visibility, self._all_contours)


class TrackLetItemGroup(QtGui.QGraphicsItemGroup):
    def __init__(self, column, row, parent=None):
        QtGui.QGraphicsItemGroup.__init__(self, parent)
        self.row = row
        self.column = column
        self.moveToRow(row)
        self.moveToColumn(column)
        self._features = {}
    
    def moveToRow(self, row):
        self.row = row
        self.setPos(self.column * BOUNDING_BOX_SIZE, row * BOUNDING_BOX_SIZE)
        
    def moveToColumn(self, col):
        self.col = col
        self.setPos(col * BOUNDING_BOX_SIZE, self.row * BOUNDING_BOX_SIZE)    
        
    def __getitem__(self, key):
        return self._features[key]
    
    def __setitem__(self, key, value):
        self._features[key] = value
    
class TrackletItem(object):
    def __init__(self, data, cc, size=BOUNDING_BOX_SIZE):
        self.size = size
        self.data = data
        self.crack_contour = cc.clip(0,BOUNDING_BOX_SIZE)
        
    

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv) 
    file, _ = getopt.getopt(sys.argv[1:], 'f:')
    if len(file) == 1:
        file = file[0][1]
    else:
        file = None
        
    mainwindow = MainWindow(file)
    mainwindow.show()
    app.exec_()
