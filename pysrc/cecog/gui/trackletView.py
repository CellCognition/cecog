from PyQt4 import QtGui, QtCore
import numpy
import sys
import random
import qimage2ndarray
import vigra

from cecog.io import dataprovider
from cecog.gui.imageviewer import HoverPolygonItem


def argsorted(seq, cmp, reverse=False):
    temp = enumerate(seq)
    temp_s = sorted(temp, cmp=lambda u,v: cmp(u[1],v[1]), reverse=reverse)
    return [x[0] for x in temp_s]

class ContainterDialog(QtGui.QMainWindow):
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
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.layout_1 = QtGui.QVBoxLayout(self)
        self.layout_2 = QtGui.QHBoxLayout()
        self.container_widget = QtGui.QWidget(self)
        self.container_widget.setLayout(self.layout_2)
        
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        
        self.view = ZoomedQGraphicsView(self.scene)
        self.view.setMouseTracking(True)
        
        self.layout_1.addWidget(self.view)
        self.layout_1.addWidget(self.container_widget)
        
        self.update_btn = QtGui.QPushButton('Reload')
        self.view.setStyleSheet(''' QPushButton {background-color: none;
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
                                         ''')
        self.update_btn.clicked.connect(self.update)
        
#        self.layout_2.addStretch()
#        self.layout_2.addWidget(self.update_btn)
        
        self.hudh = QtGui.QHBoxLayout(self.view)
        self.hudv = QtGui.QVBoxLayout()
        self.hudh.addLayout(self.hudv)
        
        self.hudv.addWidget(self.update_btn)
        self.btn_sort1 = QtGui.QPushButton('Sort random')
        self.btn_sort2 = QtGui.QPushButton('Sort intensity')
        self.btn_sort3 = QtGui.QPushButton('Sort std')
        self.hudv.addWidget(self.btn_sort1)
        self.hudv.addWidget(self.btn_sort2)
        self.hudv.addWidget(self.btn_sort3)
        
        self.btn_sort1.clicked.connect(self.sortRandomly)
        self.btn_sort2.clicked.connect(self.sortByIntensity)
        self.btn_sort3.clicked.connect(self.sortByStd)
        self.hudv.addStretch()
 
        self.hudh.addStretch()
        
        
        self.setLayout(self.layout_1)
        
#        self.view.setDragMode(self.view.ScrollHandDrag)
        
        
    def open_file(self, filename):
        fh = dataprovider.File(filename)
        self.scene.clear()
        outer = []
        for t in fh.traverse_objects('event'):
            inner = []
            for ti, data, cc in t:
                inner.append(TrackletItem(data, cc))
            outer.append(inner)
            if len(outer) > 400:
                break
        
        self.showTracklets(outer)
        
        
    def showTracklets(self, tracklets):

        self.all_tracks = []
        for row, t in enumerate(tracklets):
            trackGroup = TrackLetItemGroup(0, row)
            
            average_int = 0
            for col, ti in enumerate(t):
                average_int += ti.data.mean()
                scene_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(ti.data)))
                scene_item.setPos(col*50,row*50)
                
                scene_item_seg = HoverPolygonItem(QtGui.QPolygonF(map(lambda x: QtCore.QPointF(x[0],x[1]), ti.cc.clip(0,50).tolist())))
                scene_item_seg.setPos(col*50,row*50)
                
                scene_item_seg.setPen(QtGui.QPen(QtGui.QColor(255,0,0)))
                scene_item_seg.setAcceptHoverEvents(True)
                
                trackGroup.addToGroup(scene_item)
                trackGroup.addToGroup(scene_item_seg)
                
            trackGroup.setHandlesChildEvents(False)
            trackGroup.mean_intensity = average_int / len(t)
            trackGroup.std = numpy.concatenate(map(lambda g: g.data[..., None], t), axis=2).std(axis=2).mean()
            self.scene.addItem(trackGroup)
            self.all_tracks.append(trackGroup)
            
    def sortTracks(self, permutation):
#        self.all_tracks = [self.all_tracks[i] for i in permutation]
        for new_row, perm_idx in enumerate(permutation):
#            print 'track with intensity', self.all_tracks[perm_idx].mean_intensity, 'moves to', new_row
            self.all_tracks[perm_idx].moveToRow(new_row)

#        for x in self.all_tracks:
#            print x.mean_intensity
        
   
    def sortRandomly(self):
        perm = range(len(self.all_tracks))
        import random
        random.shuffle(perm)
        self.sortTracks(perm)
        
    def sortByIntensity(self):
        perm = argsorted(self.all_tracks, cmp=lambda u,v: cmp(u.mean_intensity, v.mean_intensity), reverse=True)
        self.sortTracks(perm)
        
    def sortByStd(self):
        perm = argsorted(self.all_tracks, cmp=lambda u,v: cmp(u.std, v.std), reverse=True)
        self.sortTracks(perm)
        
        
               

class TrackLetItemGroup(QtGui.QGraphicsItemGroup):
    def __init__(self, column, row, parent=None):
        QtGui.QGraphicsItemGroup.__init__(self, parent)
        self.row = row
        self.column = column
        self.moveToRow(row)
        self.moveToColumn(column)
    
    def moveToRow(self, row):
        self.row = row
        self.setPos(self.column * 50, row * 50)
        
    def moveToColumn(self, col):
        self.col = col
        self.setPos(col * 50, self.row * 50)
        

                
            
class GraphicsTrackletWidget(QtGui.QGraphicsItem):
    def __init__(self, parent=None):
        QtGui.QGraphicsItem.__init__(self,parent=parent)
        self.tracklet_item_list = []
        self.current_col = 0
        
    def append(self, tracklet_item):
        scene_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(tracklet_item.data)), parent=self)
        self.tracklet_item_list.append(scene_item)
        scene_item.setPos(self.current_col*tracklet_item.size, 0)
        self.current_col += 1
        

    def extend(self, tracklet_list):
        for t in tracklet_list:
            self.append(t)
            
    def paint(self, *args):
        print 'paint track'
    
    def boundingRect(self, *args):
        return QtCore.QRectF(0,0,50,50)
            
class GraphicsTrackletsWidget(QtGui.QGraphicsItem):
    def __init__(self, parent=None):
        QtGui.QGraphicsItem.__init__(self)
        self.tracklet_list = []
        self.current_row = 0
        
    def paint(self, *args):
        print 'paint tracklets'
    
    def boundingRect(self, *args):
        return QtCore.QRectF(0,0,500,50)
    
    def append(self, tracklet):
        tmp = GraphicsTrackletWidget(self)
        self.tracklet_list.append(tmp)
        
        tmp.setPos(0, self.current_row*50)
        self.current_row += 1
        
    def extend(self, tracklet_list):
        for t in enumerate(tracklet_list):
            self.append(t)

        
    
    
class TrackletItem(object):
    def __init__(self, data, cc, size=50):
        self.size = size
        self.data = data
        self.cc = cc
        
class Tracklet(list):
    pass

        
        
        

        
        
        

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv) 
    mainwindow = ContainterDialog()
    mainwindow.show()
    app.exec_()
