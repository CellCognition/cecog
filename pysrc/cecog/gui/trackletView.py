from PyQt4 import QtGui, QtCore
import numpy
import sys
import random
import qimage2ndarray
import vigra

from cecog.io import dataprovider


class ContainterDialog(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
         
        self.setGeometry(100,100,1200,700)
        self.setWindowTitle('tracklet playground')
        
        tracklet_widget = TrackletBrowser(self)
        
        self.setCentralWidget(tracklet_widget)  
        

class TrackletBrowser(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.layout_1 = QtGui.QVBoxLayout(self)
        self.layout_2 = QtGui.QHBoxLayout()
        self.container_widget = QtGui.QWidget(self)
        self.container_widget.setLayout(self.layout_2)
        
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        
        self.view = QtGui.QGraphicsView(self.scene)
        self.layout_1.addWidget(self.view)
        self.layout_1.addWidget(self.container_widget)
        
        self.update_btn = QtGui.QPushButton('Update')
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
        self.hudv.addWidget(QtGui.QPushButton('Clear'))
        self.hudv.addWidget(QtGui.QPushButton('Sort'))
        self.hudv.addStretch()
 
        self.hudh.addStretch()
        
        
        self.setLayout(self.layout_1)
        
        self.view.setDragMode(self.view.ScrollHandDrag)
        
        fh = dataprovider.File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911/dump/0037.hdf5')
        
        outer = []
        for t in fh.traverse_objects('event'):
            inner = []
            for ti, data in t:
                inner.append(TrackletItem(data))
            outer.append(inner)
            if len(outer)>30:
                break
        
        self.showTracklets(outer)
        
    def update(self):
        fh = dataprovider.File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911/dump/0037.hdf5')
        
        outer = []
        for t in fh.traverse_objects('event'):
            inner = []
            for ti, data in t:
                inner.append(TrackletItem(data))
            outer.append(inner)
            if len(outer)>3:
                break
        
        self.showTracklets(outer)
        
        
    def showTracklets(self, tracklets):


        for row, t in enumerate(tracklets):
            for col, ti in enumerate(t):
                scene_item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(qimage2ndarray.array2qimage(ti.data)))
                scene_item.setPos(col*50,row*50)
                self.scene.addItem(scene_item)
            
        
    
        
        

                
            
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
    def __init__(self, data, size=50):
        self.size = size
        self.data = data
        
class Tracklet(list):
    pass

        
        
        

        
        
        

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv) 
    mainwindow = ContainterDialog()
    mainwindow.show()
    app.exec_()
