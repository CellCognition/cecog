"""
unsupervised.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ("GMM", )


from .classdefinition import ClassDefinitionUnsup


class GMM(object):

    SaveProbs = False
    Library = "sklearn.mixture.GMM"
    Method = "Gaussian Mixture Model"

    # just a wrapper class to fit the API

    def __init__(self, nclusters, channels=None, feature_names=None):
        self.feature_names = feature_names
        self.channels = channels
        self.classdef  = ClassDefinitionUnsup(nclusters)

    # XXX rename to masks
    @property
    def regions(self):
        if len(self.channels) == 1:
            return self.channels.values()[0]
        else:
            return self.channels.values()
