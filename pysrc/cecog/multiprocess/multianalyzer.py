"""
multianalyzer.py
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
import copy
import logging
import traceback
import threading
import SocketServer
from multiprocessing import Pool

from PyQt4 import QtCore

from cecog import VERSION
from cecog.util.stopwatch import StopWatch
from cecog.threads.link_hdf import link_hdf5_files
from cecog.analyzer.core import AnalyzerCore
from cecog.threads.analyzer import AnalyzerThread
from cecog.threads.corethread import ProgressMsg
from cecog.multiprocess import mplogging as lg
from cecog.environment import CecogEnvironment
from cecog.traits.config import ConfigSettings


class MultiProcessingError(Exception):
    pass


def core_helper(plate, settings_dict, imagecontainer, position, version,
                redirect=True, debug=False):
    """Embeds analysis of a positon in a single function"""
    # see http://stackoverflow.com/questions/3288595/
    # multiprocessing-using-pool-map-on-a-function-defined-in-a-class
    logger =  logging.getLogger(str(os.getpid()))
    import numpy
    reload(numpy)
    try:
        settings = ConfigSettings()
        settings.from_dict(settings_dict)
        settings.set('General', 'constrain_positions', True)
        settings.set('General', 'positions', position)

        environ = CecogEnvironment(version, redirect=redirect, debug=debug)
        if debug:
            environ.pprint()
        analyzer = AnalyzerCore(plate, settings, imagecontainer)
        post_hdf5_link_list = analyzer.processPositions()
        return plate, position, copy.deepcopy(post_hdf5_link_list)
    except Exception as e:
        errortxt = "plate: %s, position: %s\n" %(plate, position)
        errortxt = "".join([errortxt] + \
                               traceback.format_exception(*sys.exc_info()))
        logger.error(errortxt)
        raise e.__class__(errortxt)


class ProgressCallback(QtCore.QObject):
    """Helper class to send progress signals to the main window"""

    def __init__(self, parent, job_count, ncpu):
        self.parent = parent
        self.ncpu = ncpu
        self._timer = StopWatch(start=True)

        self.progress = ProgressMsg(
            max=job_count,
            meta=('Parallel processing %d /  %d positions '
                  '(%d cores)' % (0, job_count, self.ncpu)))
        self.parent.stage_info.emit(self.progress)

    def __call__(self, (plate, pos, hdf_files)):
        self.progress.increment_progress()
        self.progress.meta = 'Parallel processing %d / %d positions %d cores)' \
            % (self.progress.progress, self.progress.max, self.ncpu)

        self.parent.stage_info.emit(self.progress)
        self._timer.reset(start=True)
        return plate, pos, hdf_files


# XXX should not be a child of QThread!
class MultiAnalyzerThread(AnalyzerThread):

    def __init__(self, parent, settings, imagecontainer, ncpu):
        super(MultiAnalyzerThread, self).__init__(parent, settings,
                                                  imagecontainer)

        self._abort = False
        self.ncpu = ncpu
        self.job_result = []

        self.log_receiver = lg.LoggingReceiver(port=0)
        port = self.log_receiver.server_address[1]

        self.pool = Pool(self.ncpu, initializer=lg.initialyze_process,
                         initargs=(port,))

        self.parent().log_window.init_process_list( \
            [str(p.pid) for p in self.pool._pool])

        self.parent().log_window.show()
        self.parent().log_window.raise_()

        SocketServer.ThreadingTCPServer.allow_reuse_address = True

        for p in self.pool._pool:
            logger = logging.getLogger(str(p.pid))
            handler = lg.NicePidHandler(self.parent().log_window)
            handler.setFormatter(logging.Formatter( \
                    '%(asctime)s %(name)-24s %(levelname)-6s %(message)s'))
            logger.addHandler(handler)

        self.log_receiver.handler.log_window = self.parent().log_window

        self.log_receiver_thread = threading.Thread( \
            target=self.log_receiver.serve_forever)
        self.log_receiver_thread.start()

    def close_logreceiver(self):
        self.log_receiver.shutdown()
        self.log_receiver.server_close()
        self.log_receiver_thread.join()

    def join(self):
        self.pool.close()
        self.pool.join()

        hdf5_link_list = list()
        try:
            exceptions = []
            if not self.is_aborted():
                for r in self.job_result:
                    if not r.successful():
                        try:
                            plate, pos, hdf_files = r.get()
                            if len(hdf_files) > 0:
                                hdf5_link_list.append(hdf_files)
                        except Exception, e:
                            exceptions.append(e)

            if len(exceptions) > 0:
                sep = 79*'-'+'\n'
                msg = sep.join([traceback.format_exc(e) for e in exceptions])
                raise MultiProcessingError(msg)
        finally:
            self.close_logreceiver()
            if len(hdf5_link_list) > 0:
                hdf5_link_list = reduce(lambda x, y: x + y, hdf5_link_list)
            link_hdf5_files(sorted(hdf5_link_list))

    def abort(self, wait=False):
        self._mutex.lock()
        try:
            self._abort = True
        finally:
            self._mutex.unlock()
        # timing is essential, flag must be set before terminate is called
        self.pool.terminate()
        if wait:
            self.wait()
        self.aborted.emit()

    def _run(self):
        self._abort = False

        # setup the processes
        jobs = []
        positions = None
        if self._settings.get('General', 'constrain_positions'):
            positions = self._settings('General', 'positions').split(',')

        for plate in self._imagecontainer.plates:
            self._imagecontainer.set_plate(plate)
            meta_data = self._imagecontainer.get_meta_data()

            if positions is not None:
                _positions = tuple(set(meta_data.positions).intersection(positions))
            else:
                _positions = meta_data.positions

            for pos in _positions:
                jobs.append((plate, self._settings.to_dict() , self._imagecontainer, pos,
                             VERSION))

        # submit the jobs
        callback = ProgressCallback(self, len(jobs), self.ncpu)
        for args in jobs:
            self.job_result.append( \
                self.pool.apply_async(core_helper, args,
                                      callback=callback))
        self.join()
