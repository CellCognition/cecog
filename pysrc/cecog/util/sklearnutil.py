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
from sklearn import mixture

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

def binary_clustering(data):
    g = mixture.GMM(n_components=2, covariance_type='full', init_params='wmc')
    g.fit(data)
    idx = g.predict(data)

    # map clusters to labels
    if numpy.sum(idx==1) > numpy.sum(idx==0) :
        idx[idx==0]=2
        idx[idx==1]=0
        idx[idx==2]=1
    return idx

def remove_constant_columns(A):
    ''' A function to remove constant columns from a 2D matrix'''
    return A[:, numpy.sum(numpy.abs(numpy.diff(A, axis=0)), axis=0) != 0]
