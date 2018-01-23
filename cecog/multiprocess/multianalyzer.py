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
import shutil
import logging
import traceback
import threading
import SocketServer
from multiprocessing import Pool
from multiprocessing import cpu_count

from PyQt5 import QtCore

from cecog.version import version
from cecog.util.stopwatch import StopWatch
from cecog.analyzer.plate import PlateAnalyzer
from cecog.threads.analyzer import AnalyzerThread
from cecog.multiprocess import mplogging as lg
from cecog.environment import CecogEnvironment
from cecog.traits.config import ConfigSettings
from cecog.logging import QHandler
from cecog.io.hdf import mergeHdfFiles

class MultiProcessingError(Exception):
    pass


def core_helper(plate, settings_dict, imagecontainer, position, version,
                mode="r+", redirect=True):
    """Embedds analysis of a positon in a single function"""
    # see http://stackoverflow.com/questions/3288595/
    # multiprocessing-using-pool-map-on-a-function-defined-in-a-class
    logger =  logging.getLogger(str(os.getpid()))

    try:
        # FIXME numpy 1.11 does not have ._dotblas
        import numpy.core._dotblas
        reload(numpy.core._dotblas)
    except ImportError as e:
        pass

    try:
        settings = ConfigSettings()
        settings.from_dict(settings_dict)
        settings.set('General', 'constrain_positions', True)
        settings.set('General', 'positions', position)

        environ = CecogEnvironment(version, redirect=redirect)

        analyzer = PlateAnalyzer(plate, settings, imagecontainer, mode=mode)
        analyzer()
        return plate, position

    except Exception as e:
        errortxt = "Plate: %s, Site: %s\n" %(plate, position)
        errortxt = "".join([errortxt] + \
                               traceback.format_exception(*sys.exc_info()))
        logger.error(errortxt)
        raise type(e)(errortxt)


class ProgressCallback(QtCore.QObject):
    """Helper class to send progress signals to the main window"""

    def __init__(self, thread, njobs):
        super(ProgressCallback, self).__init__()
        self.thread = thread
        self.count = 0
        self.njobs = njobs
        self._timer = StopWatch(start=True)

    def __call__(self, (plate, position)):

        self.count += 1
        self.thread.increment.emit()
        self.thread.statusUpdate(
            text = '%d/%d - last finished site: %s' %(self.count, self.njobs, position))

        self._timer.reset(start=True)
        return plate, position


# XXX should not be a child of QThread!
class MultiAnalyzerThread(AnalyzerThread):

    def __init__(self, parent, settings, imagecontainer):
        super(MultiAnalyzerThread, self).__init__(parent, settings,
                                                  imagecontainer)

        self._abort = False

        if settings("General", "constrain_positions"):
            count = self._settings("General", "positions").count(",") +1
        else:
            # FIXME - implcitly assume same number of postions for all plates
            count = len(self._imagecontainer.get_meta_data().positions)

        self.ncpu = min(count, cpu_count())

        self.job_result = []

        self.log_receiver = lg.LoggingReceiver(port=0)
        port = self.log_receiver.server_address[1]

        self.pool = Pool(self.ncpu, initializer=lg.initialyze_process,
                         initargs=(port,))

        self.parent().log_window.initProcessLogs( \
            [str(p.pid) for p in self.pool._pool])

        self.parent().log_window.show()
        self.parent().log_window.raise_()

        SocketServer.ThreadingTCPServer.allow_reuse_address = True

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

        try:
            exceptions = []
            if not self.is_aborted():
                for r in self.job_result:
                    if r.successful():
                        try:
                            plate, pos  = r.get()
                        except Exception, e:
                            exceptions.append(e)

            if len(exceptions) > 0:
                sep = 79*'-'+'\n'
                msg = sep.join([traceback.format_exc(e) for e in exceptions])
                raise MultiProcessingError(msg)
        finally:
            self.close_logreceiver()

        if not self._abort:
            self.mergeFiles()

    def mergeFiles(self):
        # last step is to merge all hdf files into one
        for plate in self._imagecontainer.plates:
            outdir  = self._imagecontainer.get_path_out(plate)
            hdffile = os.path.join(outdir, "%s.ch5" %plate)
            hdfdir = os.path.join(outdir, "cellh5")
            mergeHdfFiles(hdffile, hdfdir, remove_source=True)
        os.rmdir(hdfdir)

    def clearOutputDir(self, directory):
        """Remove the content of the output directory except the structure file."""

        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                if not name.endswith(".xml"):
                    os.remove(os.path.join(root, name))
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass

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

        if not self._settings('General', 'skip_finished'):
            self.clearOutputDir(self._settings('General', 'pathout'))

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

            modes = ["w"] + ["r+"]*len(_positions)
            for mode, pos in zip(modes, _positions):
                jobs.append((plate, self._settings.to_dict() , self._imagecontainer, pos,
                             version, mode))

        self.statusUpdate(min=0, max=len(jobs),
            text = 'Parallel processing %d /  %d positions '
                          '(%d cores)' % (0, len(jobs), self.ncpu))

        # submit the jobs
        callback = ProgressCallback(self, len(jobs))

        for args in jobs:
            self.job_result.append( \
                self.pool.apply_async(core_helper, args, callback=callback))
        self.join()
