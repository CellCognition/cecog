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


import numpy as np
from sklearn import mixture
from sklearn.cluster import KMeans


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
    Asum = np.log(np.sum(np.exp(A - Amax), axis))
    Asum += Amax.reshape(Asum.shape)
    if axis:
        # Look out for underflow.
        Asum[np.isnan(Asum)] = - np.Inf
    return Asum
# overwrite the existing logsumexp with new mylogsumexp

def binary_clustering(data, n_clusters=2):

    # at least n_init=5 for robustness
    km = KMeans(n_clusters, n_init=5)
    prd = km.fit_predict(data)

    # XXX
    # assign labels,
    # from now on labels have a biologial meaning
    if np.sum(prd==1) > np.sum(prd==0) :
        prd = np.where(prd, 0, 1)
    return prd

# def binary_clustering(data, n_components=2):

#     gmm = mixture.GMM(n_components, covariance_type='full',
#                       n_iter=5, init_params='wmc')
#     gmm.fit(data)
#     prd = gmm.predict(data)

#     # XXX
#     # assign labels,
#     # from now on labels a biologial meaning
#     if np.sum(prd==1) > np.sum(prd==0) :
#         prd = np.where(prd, 0, 1)
#     return prd

def remove_constant_columns(A):
    """A function to remove constant columns from a 2D matrix."""
    return A[:, np.sum(np.abs(np.diff(A, axis=0)), axis=0) != 0]
