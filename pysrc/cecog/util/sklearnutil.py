"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Qing Zhong'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'


import numpy
import scipy.cluster.vq as scv
from sklearn import mixture
from matplotlib import mlab

def mylogsumexp(A, axis=None):
    """Computes the sum of A assuming A is in the log domain.

    Returns log(sum(exp(A), axis)) while minimizing the possibility of
    over/underflow.
    """
    Amax = A.max(axis)
    if axis and A.ndim > 1:
        shape = list(A.shape)
        shape[axis] = 1
        Amax.shape = shape
    Asum = numpy.log(numpy.sum(numpy.exp(A - Amax), axis))
    Asum += Amax.reshape(Asum.shape)
    if axis:
        # Look out for underflow.
        Asum[numpy.isnan(Asum)] = - numpy.Inf
    return Asum
# overwrite the existing logsumexp with new mylogsumexp

def binary_clustering(data, invert):

    m, idx = scv.kmeans2(data,2)
    w = numpy.array([sum(idx==0)/float(len(idx)),sum(idx==1)/float(len(idx))]);

    c1 = numpy.cov(data[idx==0,:].T)
    c2 = numpy.cov(data[idx==1,:].T)
    c = numpy.dstack((c1,c2)).T
    
    g = mixture.GMM(n_components=2, cvtype = 'full') #thresh=1e-6
    g.weights = w
    g.means = m
    g.covars = c
   
    g.fit(data, init_params='') #n_iter=10, thresh=1e-2
    idx = g.predict(data)
    
    
    # map clusters to labels
    if numpy.sum(idx==1) > numpy.sum(idx==0) :
        idx[idx==0]=2
        idx[idx==1]=0
        idx[idx==2]=1
        
    if invert:
        idx[idx==0]=2
        idx[idx==1]=0
        idx[idx==2]=1
       
    return idx

    
def remove_constant_columns(A):
    ''' A function to remove constant columns from a 2D matrix'''
    return A[:, numpy.sum(numpy.abs(numpy.diff(A, axis=0)), axis=0) != 0]