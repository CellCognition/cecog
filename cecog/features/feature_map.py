"""
feature_map.py

Map feature groups from compuational groups to application oriented groups

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'



FEATURE_MAP = {
    'featurecategory_intensity': {'normbase': None,
                                  'normbase2': None},
    'featurecategory_haralick': {'haralick': (1, 2, 4, 8),
                                 'haralick2': (1, 2, 4, 8)},
    'featurecategory_stat_geom': {'levelset': None},
    'featurecategory_granugrey': {'granulometry': None},
    'featurecategory_basicshape': {'roisize': None,
                                   'circularity': None,
                                   'irregularity': None,
                                   'irregularity2': None,
                                   'axes': None},
    'featurecategory_convhull': {'convexhull': None},
    'featurecategory_distance': {'distance': None},
    'featurecategory_moments': {'moments': None},
    'featurecategory_lbp': {'lbp': (1, 2, 4, 8)}

    }
