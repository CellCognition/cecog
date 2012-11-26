# -*- coding: utf-8 -*-
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
import copy
import struct
import socket
import pickle
import logging
import traceback
import SocketServer
import threading
from multiprocessing import Pool, Queue, cpu_count

from PyQt4 import QtCore

from pdk.datetimeutils import StopWatch
from cecog import ccore
from cecog.threads.link_hdf import link_hdf5_files
from cecog.analyzer.core import AnalyzerCore
from cecog.threads.analyzer import AnalyzerThread
from cecog.traits.settings import ConfigSettings
from cecog.traits.analyzer import SECTION_REGISTRY
from cecog.traits.analyzer.general import SECTION_NAME_GENERAL

class MultiProcessingError(Exception):
    def __init__(self, exceptions):
        self.msg = ('%s-----------%sError in job item:%s' \
                        %(os.linesep, os.linesep, os.linesep)).join(
            [str(e) for e in exceptions])

# see http://stackoverflow.com/questions/3288595/
# multiprocessing-using-pool-map-on-a-function-defined-in-a-class
def AnalyzerCoreHelper(plate_id, settings_str, imagecontainer, position):

    settings = ConfigSettings(SECTION_REGISTRY)
    settings.from_string(settings_str)
    settings.set(SECTION_NAME_GENERAL, 'constrain_positions', True)
    settings.set(SECTION_NAME_GENERAL, 'positions', position)
    try:
        analyzer = AnalyzerCore(plate_id, settings, imagecontainer)
        result = analyzer.processPositions()
    except Exception:
        traceback.print_exc()
        raise
    return plate_id, position, copy.deepcopy(result['post_hdf5_link_list'])

def initialyze_process(port):
    oLogger = logging.getLogger(str(os.getpid()))
    oLogger.setLevel(logging.NOTSET)
    socketHandler = logging.handlers.SocketHandler('localhost', port)
    socketHandler.setLevel(logging.NOTSET)
    oLogger.addHandler(socketHandler)
    oLogger.info('logger init')

# perhaps a QObject
class ProcessCallback(object):

    def __init__(self, parent):
        super(ProcessCallback, self).__init__()
        self.parent = parent
        self.ncpu = None
        self.cnt = 0
        self.job_count = None
        self._timer = StopWatch()

    def notify_execution(self, job_list, ncpu):
        self.job_count = len(job_list)
        self.ncpu = ncpu
        stage_info = {'stage': 0,
                      'progress': 0,
                      'text': '',
                      'meta': 'Parallel processing %d / %d positions (%d cores)' \
                          % (0, self.job_count, self.ncpu),
                      'min': 0,
                      'max': self.job_count}
        self.parent.set_stage_info(stage_info)

    def __call__(self, (plate, pos, hdf_files)):
        self.cnt += 1
        stage_info = {'progress': self.cnt,
                      'meta': 'Parallel processing %d / %d positions (%d cores)' \
                          % (self.cnt, self.job_count, self.ncpu),
                      'text': 'finished %s - %s' % (str(plate), str(pos)),
                      'stage': 0,
                      'min': 0,
                      'item_name': 'position',
                      'interval': self._timer.current_interval(),
                      'max': self.job_count}
        self.parent.set_stage_info(stage_info)
        self._timer.reset()
        return plate, pos, hdf_files

class MultiProcessingMixin(object):

    def __init__(self, *args, **kw):
        super(MultiProcessingMixin, self).__init__()

    def setup(self, ncpu=None):
        # do I want do use all available cpus by default?
        if ncpu is None:
            ncpu = cpu_count()

        self.ncpu = ncpu
        self.log_receiver = LoggingReceiver(port=0)
        port = self.log_receiver.server_address[1]
        self.pool = Pool(self.ncpu, initializer=initialyze_process,
                         initargs=(port,))
        self.parent.process_log_window.init_process_list( \
            [str(p.pid) for p in self.pool._pool])
        self.parent.process_log_window.show()

        SocketServer.ThreadingTCPServer.allow_reuse_address = True

        for p in self.pool._pool:
            logger = logging.getLogger(str(p.pid))
            handler = NicePidHandler(self.parent.process_log_window)
            handler.setFormatter(logging.Formatter( \
                    '%(asctime)s %(name)-24s %(levelname)-6s %(message)s'))
            logger.addHandler(handler)

        self.log_receiver.handler.log_window = self.parent.process_log_window

        self.log_receiver_thread = threading.Thread( \
            target=self.log_receiver.serve_forever)
        self.log_receiver_thread.start()
        self.process_callback = ProcessCallback(self)

    def finish(self):
        self.log_receiver.shutdown()
        self.log_receiver.server_close()
        self.log_receiver_thread.join()

        if len(self.post_hdf5_link_list) > 0:
            post_hdf5_link_list = reduce(lambda x,y: x + y,
                                         self.post_hdf5_link_list)
            link_hdf5_files(sorted(post_hdf5_link_list))


    def abort(self):
        self._abort = True
        self.pool.terminate()
        self.parent.process_log_window.close()

    def join(self):
        self.pool.close()
        self.pool.join()
        self.post_hdf5_link_list = []
        if not self._abort:
            exceptions = []
            for r in self.job_result:
                if not r.successful():
                    try:
                        r.get()
                    except Exception, e:
                        exceptions.append(e)
                else:
                    plate, pos, hdf_files = r.get()
                    if len(hdf_files) > 0:
                        self.post_hdf5_link_list.append(hdf_files)
            if len(exceptions) > 0:
                error = MultiProcessingError(exceptions)
                raise error
        self.finish()

    @property
    def target(self):
        return AnalyzerCoreHelper

    def submit_jobs(self, job_list):
        self.process_callback.notify_execution(job_list, self.ncpu)
        self.job_result = [self.pool.apply_async(self.target, args,
                                                 callback=self.process_callback)
                           for args in job_list]


class MultiAnalyzerThread(AnalyzerThread, MultiProcessingMixin):

    # is nowhere emitted
    image_ready = QtCore.pyqtSignal(ccore.RGBImage, str, str)

    def __init__(self, parent, settings, imagecontainer, ncpu):
        super(MultiAnalyzerThread, self).__init__(parent, settings,
                                                  imagecontainer)
        self.setup(ncpu)
        self._abort = False

    def set_abort(self, wait=False):
        self._abort = True
        self.abort()
        if wait:
            self.wait()

    def _run(self):
        self._abort = False
        settings_str = self._settings.to_string()

        self._settings.set_section('General')
        self.lstPositions = self._settings.get2('positions')
        if self.lstPositions == '' or not self._settings.get2( \
            'constrain_positions'):
            self.lstPositions = None
        else:
            self.lstPositions = self.lstPositions.split(',')

        job_list = []

        for plate_id in self._imagecontainer.plates:
            self._imagecontainer.set_plate(plate_id)
            meta_data = self._imagecontainer.get_meta_data()
            for pos_id in meta_data.positions:
                if self.lstPositions is None:
                    job_list.append((plate_id, settings_str,
                                     self._imagecontainer, pos_id))
                else:
                    if pos_id in self.lstPositions:
                        job_list.append((plate_id, settings_str,
                                         self._imagecontainer, pos_id))

        self.submit_jobs(job_list)
        self.join()


class NicePidHandler(logging.Handler):

    def __init__(self, log_window, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.log_window = log_window

    def emit(self, record):
        self.log_window.on_msg_received_emit(record, self.format(record))

class LogRecordStreamHandler(SocketServer.BaseRequestHandler):
    'Handler for a streaming logging request'

    def handle(self):
        '''
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format.
        '''
        while 1:
            try:
                chunk = self.request.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.request.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.request.recv(slen - len(chunk))
                obj = self.unPickle(chunk)
                record = logging.makeLogRecord(obj)
                self.handleLogRecord(record)

            except socket.error:
                print 'socket handler abort'
                break


    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)

# XXX - refacortize logging stuff
class LoggingReceiver(SocketServer.ThreadingTCPServer):
    'Simple TCP socket-based logging receiver'

    logname = None

    def __init__(self, host='localhost',
                 port=None,
                 handler=LogRecordStreamHandler):
        self.handler = handler
        if port is None:
            port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
        SocketServer.ThreadingTCPServer.__init__(self, (host, port), handler)
