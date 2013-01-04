# -*- coding: utf-8 -*-
"""
test_learner.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import os
import sys
from cecog.learning.learning import CommonClassPredictor
import time

if __name__ ==  "__main__":
    if os.path.isdir(sys.argv[1]):
        learner = CommonClassPredictor(sys.argv[1], None, None)
        learner.importFromArff()
        t0 = time.time()
        print learner.gridSearch()
        print "Grid search took: ", time.time() - t0
        c, g, conf = learner.importConfusion()
        import pdb; pdb.set_trace()
    else:
        raise IOError("%s\n is not a valid directory" %sys.argv[1])
    #learner.statsFromConfusion(conf)

# #benchmark
# # merged channel
# [[23,  1,  1],
#  [ 0, 15,  0],
#  [ 1,  0, 13]])

# # primary channel
# [[23  1  1]
#  [ 1 13  1]
#  [ 2  0 13]]
