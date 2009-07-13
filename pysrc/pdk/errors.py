"""
Error handling classes for pdk.

FOG 10/2000
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['pdkError',
           'ConcurrentModificationError',
           'DeviceError',
           'IllegalArgumentError',
           'IllegalStateError',
           'NoneArgumentError',
           'NoneError',
           'NotImplementedMethodError',
           'ObjectClosedError',
           'RemoteError',
           'UnknownRemoteError',
            ]

#------------------------------------------------------------------------------
# standard library imports:
#
import cPickle
import os

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# helper functions:
#

#------------------------------------------------------------------------------
# classes:
#

class pdkError(StandardError):
    """
    Base class for all specialized pdk errors
    """
    pass


class IllegalArgumentError(pdkError):
    """
    Raised if an argument passed to a callable is incorrect
    """
    pass


class NoneArgumentError(pdkError):
    """
    Raised if an argument passed to a callable is C{None} instead of some
    not-C{None} value
    """
    pass


class NoneError(pdkError):
    """
    Raised if an value is C{None} instead of some not-C{None} value
    """
    pass


class IllegalStateError(pdkError):
    """
    Raised if an instance is not in the correct state to perform the
    requested operation (busy, not connected, etc.)
    """
    pass


class ObjectClosedError(IllegalStateError):
    """
    Raised if an object has already been closed when trying to access it
    """
    pass


class DeviceError(pdkError):
    """
    Raised if a controlled device wishes to notify of an error
    caused by itself
    """
    pass


class ConcurrentModificationError(pdkError):
    """
    Raised to indicate that an object that is attempted to be modified
    is already being modified by some other processing thread
    """
    pass


class UnknownRemoteError(pdkError):
    """
    Raised to indicate that some unknown remote exception occurred
    """
    pass


class RemoteError(pdkError):
    """
    Used to shuttle exceptions across process boundaries

    A typical usage scenario would be ::

        from pdk.errors import RemoteError
        try:
            someRemoteCall()
        except RemoteError, oError:
            if isinstance(oError.getRemoteException(), ValueError):
                # handle remote ValueErrors:
                doThis()
            else:
                raise # re-raise with full traceback
    """

    def __init__(self, remote_exception, traceback=None):
        """
        Constructor.

        @param remote_exception: remote exception
        @type remote_exception: exception instance
        @param traceback: formatted remote traceback
        @type traceback: string
        """
        pdkError.__init__(self, str(remote_exception))
        self.__remote_exception = remote_exception
        if traceback is None:
            from pdk.pyutils import get_traceback
            traceback = get_traceback()
        self.__remote_traceback = traceback

    #
    # magic methods:
    #

    def __getstate__(self):
        """
        Called to obtain state information for this remote exception.

        @return: 2-tuple containing the remote traceback (string) and a
          remote exception info 3-tuple. The latter consists of the pickled
          remote exception (string), the remote exeption's class name
          (string), and the error message (string)
        """
        try:
            pickled_exc_string = cPickle.dumps(self.__remote_exception)
        except cPickle.PickleError:
            pickled_exc_string = \
                         cPickle.dumps(UnknownRemoteError(self.args[0]))
        return (self.__remote_traceback, pickled_exc_string)

    def __setstate__(self, state):
        """
        Called to restore the state of this remote exception after
        unpickling.

        @param state: state information
        @type state: 2-tuple as returned by L{__getstate__}
        """
        self.__remote_traceback, pickled_exc_string = state
        self.__remote_exception = cPickle.loads(pickled_exc_string)
        pdkError.__init__(self, str(self.__remote_exception))

    def __reduce__(self):
        """
        """
        return (self.__class__, (None,), self.__getstate__())

    def __str__(self):
        """
        Called to obtain a string representation for this remote exception.
        """
        separator = '%s%s%s' % (os.linesep, '-'*60, os.linesep)
        return pdkError.__str__(self) + '%sRemote %s' % \
               (separator,self.__remote_traceback)

    #
    # public methods:
    #

    def get_remote_traceback(self):
        """
        Returns the formatted remote traceback.

        @return: traceback string
        """
        return self.__remote_traceback

    def get_remote_exception(self):
        """
        Returns the remote exception.

        @return: exception instance
        """
        return self.__remote_exception


class _SmartNotImplementedError(NotImplementedError):
    """
    Base class for smart "NotImplemented..." errors
    """

    def __init__(self, name, cls):
        """
        Constructor.

        @param name: name of the declared entity
        @type name: string
        @param cls: class containing the declaration
        @type cls: arbitrary type object
        """
        NotImplementedError.__init__(self,
                                     self._get_message_string(name, cls))

    #
    # protected methods:
    #

    def _get_message_string(self, name, cls):
        """
        Returns the message string to show with this "not implemented" error.

        @param name: name of the declared virtual
        @type name: string
        @param cls: class the exception occurred in
        @type cls: class object
        @return: formatted error message (string)
        """
        raise NotImplementedMethodError('_get_message_string',
                                        _SmartNotImplementedError)


class NotImplementedMethodError(_SmartNotImplementedError):
    """
    Custom exception to use for not implemented methods
    """

    #
    # protected methods:
    #

    @staticmethod
    def _get_message_string(name, cls):
        return 'classes derived from "%s.%s" need to implement a "%s" ' \
               'method!' % (cls.__module__, cls.__name__, name)


class NotImplementedAttributeErrorBase(_SmartNotImplementedError):
    """
    Base class for not implemented virtual attribute and property errors
    """

    #
    # protected methods:
    #

    @staticmethod
    def _get_declaration_class():
        """
        Returns the class used for declaring the virtual

        @return: virtual declaration class (instance of
          L{pdk.declarations.VirtualDeclaration})
        """
        raise NotImplementedMethodError('_get_declaration_class',
                                        NotImplementedAttributeErrorBase)
