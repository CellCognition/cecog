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

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import numpy

#-------------------------------------------------------------------------------
# extension module imports:
#
from matplotlib import mlab
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import scipy.stats as stats
from scipy.cluster.vq import kmeans

from PyQt4 import QtGui, QtCore


#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.io.dataprovider import File

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#
def remove_constant_columns(mat):
    return mat[:, numpy.sum(numpy.diff(mat,axis=0),axis=0) != 0]
    
def get_test_data():
    f = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump_save/two_positions.hdf5')
    pos = f[f.positions[0]]
    print f.positions[0]
    events = pos.get_objects('event')
    feature_matrix = []
    labels = []
    for e in events:
        item_features = e.item_features 
        item_labels = e.item_labels
        if item_features is not None:
            feature_matrix.append(item_features)
            labels.append(item_labels)
    feature_matrix = numpy.concatenate(feature_matrix)
    feature_matrix = remove_constant_columns(feature_matrix)
    feature_matrix = stats.zscore(feature_matrix)
    pca = mlab.PCA(feature_matrix)
    feature_matrix = pca.project(feature_matrix)
    feature_matrix = feature_matrix.reshape(len(events), len(item_features), -1)
    f.close()
    return feature_matrix, numpy.asarray(labels)

#-------------------------------------------------------------------------------
# classes:
#

class EventPCAPlugin(FigureCanvas):
    def __init__(self, data_provider, parent=None, width=8, height=8):
        self.data_provider = data_provider
        
        self.fig = Figure(figsize=(width, height))
        self._run_pca()

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
            for t in events:
                item_features = t.item_features 
                if item_features is not None:
                    self.feature_matrix.append(item_features)
                    
                item_colors = t.item_colors 
                if item_colors is not None:
                    self.item_colors.extend(item_colors)
    
        print 'number ofevents', len(self.feature_matrix)
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

class DynamicTimeWarping(object):
    Inf = numpy.Inf
    class State(object):
        def __init__(self, cost):
            self.cost = cost
            
        def __str__(self):
            if self.cost == numpy.Inf:
                return 'xxxxxx'
            else:
                return "%6.2f" % int(self.cost)
            
    def __init__(self, features, labels):
        self.features = features
        self.labels = labels
        self.nr_classes = len(numpy.unique(labels)) + 1
        self.track_length = self.features.shape[1] 
        
        self.dtw = numpy.zeros((self.nr_classes + 1, self.track_length+1), dtype=object)
        for i in range(self.dtw.shape[0]):
            for j in range(self.dtw.shape[1]):
                self.dtw[i,j] = DynamicTimeWarping.State(self.Inf if (i ==0 or j==0) else 0)
                
        self.dtw[0, 0].cost = 0
                
    def __str__(self):
        s = ''
        for i in range(self.dtw.shape[0]):
            s += " ".join(map(str, [x for x in self.dtw[i,:]])) + '\n'
        return s
        
    def run(self, index):
        for i in range(1, self.dtw.shape[0]):
            for j in range(1, self.dtw.shape[1]): 
                own_cost = 1
                stay_cost, move_cost  = self._cost_feature_space_dist(i,j, index)
                self.dtw[i,j].cost = own_cost + min(self.dtw[i,j-1].cost + stay_cost, self.dtw[i-1,j-1].cost + move_cost)
                
        prediction = self.get_track()
        actual = self.labels[index,:] 
        
        acc = 0
        for p, a in zip(prediction, actual):
            if p==a:
                acc+=1
        return float(acc)/len(prediction)
                
    def run_oracle(self, index):
        for i in range(1, self.dtw.shape[0]):
            for j in range(1, self.dtw.shape[1]): 
                own_cost = self._cost_oracle(i,j, index)
                self.dtw[i,j].cost = own_cost + min(self.dtw[i,j-1].cost, self.dtw[i-1,j-1].cost)
    
    def _cost_oracle(self, i,j, index):
        if i==8:
            i=1
        return int(i!=self.labels[index, j-1])
        
    def _cost_feature_space_dist(self, i, j, index):
        f_pre = self.features[index,j-2,:]
        f_now = self.features[index,j-1,:]
        dist = numpy.sqrt(numpy.sum(numpy.square(f_pre - f_now)))
        print dist
        return dist, 14- dist
        
    def get_track(self):
        path = []
        def get_track_impl(i,j):
            i_ = i
            if i == 8:
                i_ = 1
            path.append(i_)
            if i == 1 and j == 1:
                return
            else:
                if self.dtw[i, j-1].cost >= self.dtw[i-1, j-1].cost:
                    get_track_impl(i-1, j-1)
                else:
                    get_track_impl(i, j-1)
        
        if self.dtw[-1,-1].cost > self.dtw[-2,-1].cost: 
            print "mitosis not ended" 
            get_track_impl(self.dtw.shape[0]-2, self.dtw.shape[1]-1)
            
        else:
            print "coming back to interphase"
            get_track_impl(self.dtw.shape[0]-1, self.dtw.shape[1]-1)
            
        path.reverse()
        return numpy.asarray(path)
    
if __name__ == "__main__":
    fm, lab = get_test_data()
    
