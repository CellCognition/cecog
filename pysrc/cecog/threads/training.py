# -*- coding: utf-8 -*-
"""
training.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import time
from PyQt4 import QtCore

from cecog.threads.corethread import CoreThread
from cecog.learning.learning import ConfusionMatrix
from cecog.util.stopwatch import StopWatch

class TrainingThread(CoreThread):

    conf_result = QtCore.pyqtSignal(float, float, ConfusionMatrix)

    def __init__(self, parent, settings, learner):
        super(TrainingThread, self).__init__(parent, settings)
        self._learner = learner

    def _run(self):
        c_begin, c_end, c_step = -5,  15, 2
        c_info = c_begin, c_end, c_step

        g_begin, g_end, g_step = -15, 3, 2
        g_info = g_begin, g_end, g_step

        stage_info = {'stage': 0,
                'text': '',
                'min': 0,
                'max': 1,
                'meta': 'Classifier training:',
                'item_name': 'round',
                'progress': 0}
        self.set_stage_info(stage_info)

        i = 0
        best_accuracy = -1
        best_log2c = None
        best_log2g = None
        best_conf = None
        is_abort = False
        stopwatch = StopWatch(start=True)
        self._learner.filterData(apply=True)
        t0 = time.time()
        for info in self._learner.iterGridSearchSVM(c_info=c_info,
                                                    g_info=g_info):
            n, log2c, log2g, conf = info
            stage_info.update({'min': 1,
                               'max': n,
                               'progress': i+1,
                               'text': 'log2(C)=%d, log2(g)=%d' % \
                                   (log2c, log2g),
                               'interval': stopwatch.interim(),
                               })
            self.set_stage_info(stage_info, stime=0.05)
            stopwatch.reset(start=True)
            i += 1
            accuracy = conf.ac_sample
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_log2c = log2c
                best_log2g = log2g
                best_conf = conf
                self.conf_result.emit(log2c, log2g, conf)

            if self.is_aborted():
                is_abort = True
                break

        # overwrite only if grid-search was not aborted by the user
        if not is_abort:
            self._learner.train(2**best_log2c, 2**best_log2g)
            self._learner.exportConfusion(best_log2c, best_log2g, best_conf)
            self._learner.exportRanges()
            # FIXME: in case the meta-data (colors, names, zero-insert) changed
            #        the ARFF file has to be written again
            #        -> better store meta-data outside ARFF
            self._learner.exportToArff()
