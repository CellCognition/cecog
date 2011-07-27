from PyQt4 import QtGui, QtCore
import numpy, vigra
import sys
import random
import qimage2ndarray
import getopt

from cecog.io import dataprovider
from cecog.io.dataprovider import trajectory_features
from cecog.gui.imageviewer import HoverPolygonItem

BOUNDING_BOX_SIZE = dataprovider.BOUNDING_BOX_SIZE
PREDICTION_BAR_HEIGHT = 4
PREDICTION_BAR_X_PADDING = 2
CLASS_TO_COLOR = { \
                  0 : QtCore.Qt.red, \
                  1 : QtCore.Qt.green,\
                  2 : QtCore.Qt.blue,\
                  3 : QtCore.Qt.yellow,\
                  4 : QtCore.Qt.magenta,\
                  5 : QtCore.Qt.cyan,\
                  6 : QtCore.Qt.darkRed,\
                  7 : QtCore.Qt.darkBlue,\
                  8 : QtCore.Qt.darkGreen,\
                  }


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
        
        self.main_layout = QtGui.QHBoxLayout()
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
        

        self.view_hud_btn_layout.addWidget(self.btn_toggle_contours)
        
        self.btn_selectTen = QtGui.QPushButton('Select 10')
        self.btn_selectTen.clicked.connect(self.selectTenRandomTrajectories)
        self.view_hud_btn_layout.addWidget(self.btn_selectTen)
        
        self.btn_selectAll = QtGui.QPushButton('Select All')
        self.btn_selectAll.clicked.connect(self.selectAll)
        self.view_hud_btn_layout.addWidget(self.btn_selectAll)
        
        self.btn_selectTransition = QtGui.QPushButton('Select Transition 4,0')
        self.btn_selectTransition.clicked.connect(self.selectTransition)
        self.view_hud_btn_layout.addWidget(self.btn_selectTransition)
        
        self.view_hud_btn_layout.addStretch()
        
        self.btn_toggle_contours.clicked.connect(self.toggle_contours)
        
        self.view_hud_layout.addStretch()
        
        self.view.setDragMode(self.view.ScrollHandDrag)
        
        
    def open_file(self, filename):
        fh = dataprovider.File(filename)
        self.scene.clear()
        
        outer = []
        for t in fh.traverse_objects('event'):
            inner = []
            for _, image, crack_contour, prediction in t:
                inner.append(TrackletItem(image, crack_contour, prediction))
            outer.append(inner)
            
        self.initTracks(outer)
        
        
    def initTracks(self, tracklets):
        self._all_tracks = []
        
        for row, trajectory in enumerate(tracklets):
            trajectoryGroup = GraphicsTrajectoryGroup(0, row, trajectory)
            trajectoryGroup.setHandlesChildEvents(False)
            self.scene.addItem(trajectoryGroup)
            self._all_tracks.append(trajectoryGroup)
            
        zero_line = QtGui.QGraphicsLineItem(0, 0, 0, len(self._all_tracks) * (PREDICTION_BAR_HEIGHT + BOUNDING_BOX_SIZE))
        zero_line.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.white), 1))
        
        self.scene.addItem(zero_line)
        self._selected_tracks = [True] * len(self._all_tracks)
            
    def sortTracks(self, permutation):  
        self.reset()      
        for new_row, perm_idx in enumerate(permutation):
            self._all_tracks[perm_idx].moveToRow(new_row)
        self.update()
            
    def sortTracksByFeature(self, feature_name):
        permutation = argsorted([t[feature_name] for t in self._all_tracks], reverse=True)
        self.sortTracks(permutation)
    
    def sortRandomly(self):
        perm = range(len(self._all_tracks))
        random.shuffle(perm)
        self.sortTracks(perm)
        
    def sortByIntensity(self):
        perm = argsorted(self._all_tracks, cmp=lambda u,v: cmp(u.mean_intensity, v.mean_intensity), reverse=True)
        self.sortTracks(perm)
        
    def toggle_contours(self):
        are_visible = self._all_tracks[0].areContoursVisible()
        toggle_visibility = lambda x: x.setContoursVisible(not are_visible)
        map(toggle_visibility, self._all_tracks)
        
    def selectTenRandomTrajectories(self):
        self.reset()
        self._selected_tracks = [False] * len(self._selected_tracks)
        for r in random.sample(xrange(len(self._selected_tracks)), 10):
            self._selected_tracks[r] = True
        self.update()
        
    def selectAll(self):
        self.reset()
        self._selected_tracks = [True] * len(self._selected_tracks)
        self.update()
        
    def selectTransition(self):
        self.reset()
        self._selected_tracks = [False] * len(self._selected_tracks)
        for row, t in enumerate(self._all_tracks):
            trans_pos = reduce(lambda x,y: str(x) + str(y), t['prediction']).find('40')
            if trans_pos > 0:
                self._selected_tracks[row] = True
                t.moveToColumn(t.column - trans_pos -1)
        self.update()

    def _cum_selected_tracks(self):
        return numpy.cumsum(1 - numpy.asarray(self._selected_tracks))
    
    def update(self):
        cum_selected_tracks = self._cum_selected_tracks()
        for row, t in enumerate(self._all_tracks):
            if self._selected_tracks[row]:
                t.moveToRow(t.row - cum_selected_tracks[row])
                t.setVisible(True)
            else:
                t.setVisible(False)
                
    def reset(self):
        for t in self._all_tracks:
            t.resetPos()

class GraphicsTrajectoryGroup(QtGui.QGraphicsItemGroup):
    class GraphicsTrajectoryItem(object):
        def __init__(self, gallery_item, contour_item, bar_item, is_visible=True):
            self.gallery_item = gallery_item
            self.contour_item = contour_item
            self.bar_item = bar_item

    def __init__(self, column, row, trajectory, parent=None):
        QtGui.QGraphicsItemGroup.__init__(self, parent)
        self._row = row
        self.row = row
        self._column = column
        self.column = column
        self._features = {}
        
        self['prediction'] = []
        
        self._items = []
        
        for col, t_item in enumerate(trajectory):
            gallery_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(t_item.data)))
            gallery_item.setPos(col * BOUNDING_BOX_SIZE, PREDICTION_BAR_HEIGHT)
            
            self['prediction'].append(t_item.predicted_class[0])
            bar_item = QtGui.QPixmap(BOUNDING_BOX_SIZE - 2 * PREDICTION_BAR_X_PADDING, PREDICTION_BAR_HEIGHT)
            bar_item.fill(CLASS_TO_COLOR[t_item.predicted_class[0]])
            bar_item = QtGui.QGraphicsPixmapItem(bar_item)
            bar_item.setPos(col*BOUNDING_BOX_SIZE + PREDICTION_BAR_X_PADDING, 0) 
            
            contour_item = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), t_item.crack_contour.tolist())))
            contour_item.setPos(col*BOUNDING_BOX_SIZE, PREDICTION_BAR_HEIGHT)
            contour_item.setPen(QtGui.QPen(CLASS_TO_COLOR[t_item.predicted_class[0]]))
            
            contour_item.setAcceptHoverEvents(True)
            
            self.addToGroup(gallery_item)
            self.addToGroup(bar_item)
            self.addToGroup(contour_item)
            
            self._items.append(self.GraphicsTrajectoryItem(gallery_item, contour_item, bar_item))
                
            for tf in trajectory_features:
                self[tf.name] =  tf.compute(trajectory)
        
        id_item = QtGui.QGraphicsTextItem('%03d' % row)
        id_item.setPos( (col+1) * BOUNDING_BOX_SIZE, PREDICTION_BAR_HEIGHT)
        id_item.setDefaultTextColor(QtCore.Qt.white)
        id_item.setFont(QtGui.QFont('Helvetica', 24))
        self.addToGroup(id_item)
        
        self.moveToRow(row)
        self.moveToColumn(column)
    
    def moveToRow(self, row):
        self.row = row
        self.setPos(self.column * BOUNDING_BOX_SIZE, row * (PREDICTION_BAR_HEIGHT + BOUNDING_BOX_SIZE))
        
    def moveToColumn(self, col):
        self.column = col
        self.setPos(col * BOUNDING_BOX_SIZE, self.row * (PREDICTION_BAR_HEIGHT + BOUNDING_BOX_SIZE))    
        
    def __getitem__(self, key):
        return self._features[key]
    
    def __setitem__(self, key, value):
        self._features[key] = value
        
    def areContoursVisible(self):
        return self._items[0].contour_item.isVisible()
    
    def setContoursVisible(self, state):
        map(lambda x: x.contour_item.setVisible(state), self._items)
        
    def resetPos(self):
        self.moveToColumn(self._column)
        self.moveToRow(self._row)
    
class TrackletItem(object):
    def __init__(self, data, crack_contour, predicted_class, size=BOUNDING_BOX_SIZE):
        self.size = size
        self.data = data
        self.crack_contour = crack_contour.clip(0, BOUNDING_BOX_SIZE)
        self.predicted_class = predicted_class
        
    

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
