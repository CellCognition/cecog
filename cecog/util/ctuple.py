"""
ctuple.py

Subclass of tuple with custom string representation.
"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


from collections import OrderedDict

class CTuple(tuple):
    """Subclass of tuple with custom string representation.

    CTuple overwrites also __add__, __mul__, __rmul__ to not return a standard tuple.
    """

    def __add__(self, *args, **kw):
        return CTuple(super(CTuple, self).__add__(*args, **kw))

    def __mul__(self, *args, **kw):
        return CTuple(super(CTuple, self).__mul__(*args, **kw))

    def __rmul__(self, *args, **kw):
        return CTuple(super(CTuple, self).__rmul__(*args, **kw))

    def __str__(self):
        return "-".join(self)


class COrderedDict(OrderedDict):

    def values(self):
        return CTuple(list(super(COrderedDict, self).values()))
