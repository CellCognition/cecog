"""
pattern.py

Some design pattern collected
"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["Singleton", "QSingleton"]

import os
from PyQt5.QtCore import pyqtWrapperType


class Singleton(type):
    """Process save Singleton to get os.fork() working."""

    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(cls, bases, dict)
        cls._instances = {}
        cls._pid = os.getpid()

    def __call__(cls, *args, **kwargs):
        pid = os.getpid()

        if pid not in cls._instances:
            cls._instances[pid] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[pid]


class QSingleton(pyqtWrapperType):
    """PyQt implementation of the singleton pattern to avoid the metaclass conflict"""

    def __init__(cls, name, bases, dict):
        super(QSingleton, cls).__init__(cls, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(QSingleton, cls).__call__(*args, **kwargs)
        return cls._instance
