"""
regexp.py

Collection of regular expression for filenames in one source file
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import re

# <analysisdir>/statistics/events/features_*.*
re_events =  re.compile('(.*?_{1,3})?P(?P<position>.*?)_{1,3}T(?P<time>\d+)'
                        '_{1,3}?O(?P<object>\d+)_{1,3}?B(?P<branch>\d+)_{1,3}?'
                        'C(?P<channel>.+?)_{1,3}?R(?P<region>.+?)'
                        '\.[a-zA-Z0-9]{1,3}?')
