"""
Simple PyAMF mixin-class which should allow a better and more convenient
way to control which class attributes are de- and encoded via PyAMF.

Example1: Only defined attributes will be published::

    >>> class KlassA(AmfMixin):
    >>>
    >>>     AMF = ['test1', 'test2']
    >>>
    >>>     test1 = None
    >>>     test2 = None

Example2: All public attributes (not `_test3`) will be published::

    >>> class KlassB(AmfMixin):
    >>>
    >>>     AMF = None
    >>>
    >>>     test1 = None
    >>>     test2 = None
    >>>     _test3 = None
"""

__docformat__ = "epytext"

__author__ = "Michael Held"
__date__ = "$Date:2008-10-25 01:08:32 +0200 (Sat, 25 Oct 2008) $"
__revision__ = "$Rev:117 $"
__source__ = "$URL::                                                           $"

__all__ = ['AmfMixin',
           ]


#------------------------------------------------------------------------------
# classes:
#

class AmfMixin(object):
    """
    The `AMF` attribute defines all attribute names which should be de- and
    encoded by PyAMF (in general the __getstate__ and __setstate__ methods
    define which attribute will be pickled/serialized).
    If `AMF` is `None` all public attributes will be published, e.g. all
    attributes without a '_' prefix.
    """

    AMF = []

    def __getstate__(self):
        data = {}
        if not self.AMF is None:
            for name in self.AMF:
                data[name] = getattr(self, name)
        else:
            for name, value in self.__dict__.iteritems():
                if name[0] != '_':
                    data[name] = value
        #print self.__class__.__name__, data
        return data

    def __setstate__(self, data):
        for name, value in data.iteritems():
            if name in self.AMF:
                setattr(self, name, value)
