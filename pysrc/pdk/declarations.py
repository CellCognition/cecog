"""
Declaration classes.

FOG 03.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['VirtualDeclaration',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.pyutils import get_bases

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class VirtualDeclaration(property):
    """
    Specialized L{property} that raises a special L{NotImplementedError}
    when accessed.

    Use this to declare entities that you require to be defined in derived
    classes or instances.
    """

    def __init__(self, name):
        """
        Constructor.

        @param name: name of the declared entity
        @type name: string
        """
        property.__init__(self)
        self.__name = name

    #
    # magic methods:
    #

    def __get__(self, instance, cls):
        """
        Overrides C{property.__get__}.

        @raise NotImplementedError: if the declared entity was accessed from
          within an instance name space (class-level access is allowed!).
          The actual class of the raised exception is determined by the
          L{_get_error_class} (virtual) method
        """
        if not instance is None:
            # Look up the base class where the declaration was made:
            base = None
            for base in get_bases(cls, reverse=False):
                try:
                    found = isinstance(base.__dict__[self.__name],
                                       self.__class__)
                except KeyError:
                    continue
                else:
                    if found:
                        break
            raise self._get_error_class()(self.__name, base)
        return self

    #
    # protected methods:
    #

    def _get_error_class(self):
        """
        Return the class of the error to raise if the declared virtual is
        accessed. To be implemented in derived classes.

        @return: error class (subclass of L{NotImplementedError})
        """
        raise NotImplementedError('Abstract method.')


#------------------------------------------------------------------------------
# functions:
#
