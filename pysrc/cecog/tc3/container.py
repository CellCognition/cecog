"""
container.py

Data containers for tc3 and cluster analysis
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['TC3Container', 'TC3Params', 'GmmParams']

from collections import namedtuple

TC3Container = namedtuple('TC3Container', ['model', 'parameters', 'labels'])

TC3Params = namedtuple('TC3Params', ['n_clusters'])
GmmParams = namedtuple('GmmParams', ['means', 'covars', 'weigths', 'probabilities'])
