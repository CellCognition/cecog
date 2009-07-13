"""
Code for attribute containers.

FOG 03.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['Attribute',
           'Slot',
           'VirtualAttribute',
           'NotImplementedAttributeError',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import os

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.declarations import VirtualDeclaration
from pdk.errors import NotImplementedAttributeErrorBase

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class VirtualAttribute(VirtualDeclaration):
    """
    Defines a virtual attribute.

    See L{pdk.declarations.VirtualDeclaration}.
    """

    #
    # protected methods:
    #

    def _get_error_class(self):
        return NotImplementedAttributeError


class _Attribute(str):
    """
    Simple container for attribute definitions

    See the L{_AttributeControllerMixin} class for explanations of
    the various attribute options.
    """

    def __new__(cls, name,
                is_write_once=False, is_not_none=False, is_mandatory=False,
                doc=None, **options):
        """
        Overrides C{object.__new__}

        @param name: attribute name
        @type name: string
        @param is_write_once: set this to indicate that this attribute can
          only be set once
        @type is_write_once: Boolean
        @param is_not_none: set this to indicate that this attribute can not
          be set to a not-C{None} value
        @type is_not_none: Boolean
        @param is_mandatory: set this to indicate that a value has to be
          passed for this attribute at initialization time
        @type is_mandatory: Boolean
        @param doc: documentation about this attribute
        @type doc: string
        @keyword default_value: default value for this attribute. We cannot
          declare this as a keyword parameter with a default value here,
          since we may not want to have any default value at all
        @type default_value: arbitrary object
        """
        self = str.__new__(cls, name)
        self.name = name
        self.is_write_once = is_write_once
        self.is_not_none = is_not_none
        self.is_mandatory = is_mandatory
        self.doc = doc
        if 'default_value' in options:
            self.default_value = options['default_value']
        return self

    #
    # magic methods:
    #

    def __getnewargs__(self):
        """
        Called to obtain the constructor arguments of this managed attribute
        during unpickling.
        """
        return (self.name,) # pylint: disable-msg=E1101

    def __repr__(self):
        """
        Called to obtain a string expression for this attribute.
        """
        sep = os.linesep + ' ' * (len(self.__class__.__name__) + 1)
        repr_string = '%s(%s)' % \
                        (self.__class__.__name__,
                         sep.join(['%s=%%(%s)s' % (name, name)
                                   for name in self.__dict__.keys()]))
        return repr_string % self.__dict__


class Attribute(_Attribute):
    """
    Container for the pdk-specific C{__attributes__} attribute declarations
    """
    pass


class Slot(_Attribute):
    """
    Container for C{__slots__} attribute declarations
    """
    pass


class NotImplementedAttributeError(NotImplementedAttributeErrorBase):
    """
    Class for not implemented virtual attribute access errors

    See the L{pdk.attributes.VirtualAttribute} class for details.
    """

    #
    # protected methods:
    #

    @staticmethod
    def _get_message_string(name, cls):
        """
        Implements L{_SmartNotImplementedError._get_message_string}.
        """
        return 'classes derived from "%s.%s" need to define a "%s" ' \
               'attribute!' % (cls.__module__, cls.__name__, name)

    @staticmethod
    def _get_declaration_class():
        """
        Implements L{NotImplementedAttributeErrorBase._get_declaration_class}.
        """
        return VirtualAttribute

#------------------------------------------------------------------------------
# functions:
#

