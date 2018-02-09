"""
preprocessor.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('ZScore', 'ZScore2', 'PreProcessor')

import numpy as np


class ZScore(object):

    def __init__(self, data, min_variance=10e-9, replace_inf=True):
        self.mean = data.mean(axis=0)
        self.std = data.std(axis=0)

        if replace_inf:
            # supresses RuntimeWarning nan < 0.0
            self.std[np.isnan(self.std)] = 0.0
            # features with no variance should be filtered out later
            self.std[self.std <= min_variance] = np.nan

    def normalize(self, data):
        return (data - self.mean)/self.std


class ZScore2(object):
    """Z-score data using predefined offset, scale and binary mask."""


    def __init__(self, offset, scale, mask):
        # offset and scale are save unmasked
        self._offset = offset[mask]
        self._scale = scale[mask]
        self._mask = mask

    def __call__(self, features):
        return self.normalize(self.filter(features))

    def normalize(self, data):
        return (data - self._offset)/self._scale

    def filter(self, data):

        if data.ndim == 1:
            data = data.reshape((-1, data.size))

        return data[:, self._mask]


class PreProcessor(object):
    """PreProcessor is used to normalize the data and remove columns that
    contain NaN's and have zero variance. If index is None all features are
    taken into account otherwise only those specified with index. Index can
    be an integer or a list of integers.
    """

    def __init__(self, data, index=None, min_std=10e-9):

        self.data = data
        self._zs = ZScore(data, replace_inf=True)
        data = self._zs.normalize(data)

        # to remove columns that contaim nan's and have zero variance
        mask_nan = np.invert(np.isnan(data.sum(axis=0)))
        self._mask = np.ones(mask_nan.shape).astype(bool)

        if index is not None:
            self._mask[:] = False
            self._mask[index] = True

        self._mask *= mask_nan

        data = self.filter(data)
        self.traindata = data #self.normalize(data)

    @property
    def std(self):
        return self.data.std(axis=0)

    @property
    def mean(self):
        return self.data.mean(axis=0)

    @property
    def mask(self):
        return self._mask

    @property
    def nfeatures(self):
        return self.traindata.shape[1]

    @property
    def nsamples(self):
        return self.data.shape[0]

    def normalize(self, data):
        return self._zs.normalize(data)

    def filter(self, data):
        return data[:, self._mask]

    def __call__(self, data):
        data1 = self.filter(self.normalize(data))
        return data1
