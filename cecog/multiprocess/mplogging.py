"""
mplogging.py
"""
from __future__ import absolute_import
from __future__ import print_function

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Michael Held'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


import os
import six.moves.cPickle
import struct
import socket
import logging
import logging.handlers
import six.moves.socketserver


def initialyze_process(port):
    logger = logging.getLogger(str(os.getpid()))
    logger.setLevel(logging.NOTSET)
    socketHandler = logging.handlers.SocketHandler('localhost', port)
    socketHandler.setLevel(logging.NOTSET)
    logger.addHandler(socketHandler)
    logger.info('logger init')


class LogRecordStreamHandler(six.moves.socketserver.BaseRequestHandler):
    """Handler for a streaming logging request"""

    def handle(self):
        """Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format.
        """
        while True:
            try:
                chunk = self.request.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.request.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.request.recv(slen - len(chunk))
                obj = six.moves.cPickle.loads(chunk)
                record = logging.makeLogRecord(obj)
                self.handleLogRecord(record)

            except socket.error:
                print('socket handler abort')
                break

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


class LoggingReceiver(six.moves.socketserver.ThreadingTCPServer):
    """Simple TCP socket-based logging receiver"""

    logname = None

    def __init__(self, host='localhost',
                 port=None,
                 handler=LogRecordStreamHandler):
        self.handler = handler
        if port is None:
            port = logging.handlers.DEFAULT_TCP_LOGGING_PORT
        six.moves.socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
