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
import numpy
import argparse
from cecog.learning.learning import CommonClassPredictor
import time



if __name__ ==  "__main__":

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('directory', type=str,
                        help='Directory to the classifier')
    args = parser.parse_args()

    if os.path.isdir(args.directory):
        learner = CommonClassPredictor(args.directory, None, None)
        learner.importFromArff()
        t0 = time.time()
        n, c, g, conf =learner.gridSearch()
        print "Grid search took: ", time.time() - t0
        #c, g, conf = learner.importConfusion()

        numpy.set_printoptions(linewidth=80)
        print "Confusion Matrix:"
        for row in conf.conf:
            print row
    else:
        raise IOError("%s\n is not a valid directory" %args.directory)
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
