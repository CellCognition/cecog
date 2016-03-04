"""
hdf.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('Ch5File', )

from cellh5 import CH5FileWriter


class Ch5File(CH5FileWriter):

    def __init__(self, *args, **kw):
        super(Ch5File, self).__init__(*args, **kw)
