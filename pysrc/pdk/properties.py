"""
Property classes.

pdk properties are variables (in the sense defined in the L{pdk.variables}
module) used as instance attributes. The classes in this module only make
sense in conjunction with the property manager classes in
the L{pdk.propertymanagers} module, which also provide more documentation.

This code incorporates ideas taken from Graphite, which was originally written
by Joseph and Michelle Strout in 1999.

FOG 08.2001
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['ArrayProperty',
           'BooleanProperty',
           'CharProperty',
           'DateTimeProperty',
           'DictionaryProperty',
           'EnumProperty',
           'FloatProperty',
           'FunctionProperty',
           'InstanceProperty',
           'IntProperty',
           'ListProperty',
           'MappingProperty',
           'NumberProperty',
           'PositionProperty',
           'PropertyGroup',
           'Property',
           'RectangleProperty',
           'SequenceProperty',
           'StringProperty',
           'StaticProperty',
           'TupleProperty',
           'VirtualProperty',
           'isProperty',
           'NotImplementedPropertyError',
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
from pdk.attributes import Attribute
from pdk.attributemanagers import AttributeController
from pdk.declarations import VirtualDeclaration
from pdk.variables import (ArrayVariable,
                           BooleanVariable,
                           CharVariable,
                           DateTimeVariable,
                           EnumVariable,
                           FloatVariable,
                           FunctionVariable,
                           InstanceVariable,
                           IntVariable,
                           MappingVariable,
                           NumberVariable,
                           PositionVariable,
                           RectangleVariable,
                           SequenceVariable,
                           StringVariable,
                           TupleVariable,
                           Variable,
                           VariableGroup)
from pdk.errors import NotImplementedAttributeErrorBase

#------------------------------------------------------------------------------
# constants:
#
X,Y,Z = range(3)

#------------------------------------------------------------------------------
# helper functions:
#

#------------------------------------------------------------------------------
# classes:
#

class _Property(AttributeController):
    """
    Base class for all property types

    Properties are pdk variables (see the L{pdk.variables} module) that are
    used as instance attributes. This class only serves as a container for
    the specific attributes that determine the behavior of a property, which
    is implemented in the L{pdk.propertymanagers.PropertyManager} class.
    """

    __attributes__ = \
         [Attribute('delCallback',
                    default_value=None,
                    doc='callable that is triggered when a property is '
                        'about to be deleted'),
          Attribute('getCallback',
                    default_value=None,
                    doc='callable that is called to return the property '
                        'value (for dynamic properties)'),
          Attribute('isAutoInit',
                    default_value=True,
                    doc='if this is set, the property manager will '
                        'set the value of this property during '
                        'initialization (either to the value passed to the '
                        'constructor or to the default value, if no value '
                        'was passed)'),
          Attribute('is_mandatory',
                    default_value=False,
                    doc='if this is set, a value for this property has to '
                        'be provided at initialization time'),
          Attribute('is_not_none',
                    default_value=False,
                    doc='if this is set, this attribute can only be set to '
                        'a not-C{None} value'
                    ),
          Attribute('isReadOnly',
                     default_value=False,
                     doc='if this is set, the property manager will not '
                         'allow changes in the value of this property after '
                         'it has been set to its initial value'),
          Attribute('setPreCallback',
                    default_value=None,
                    doc='callable that acts as a filter for the value '
                        'of a property *before* the (possibly modified) '
                        'value is set in the instance. Use this to '
                        'implement dynamical dependencies of a property '
                        'on other properties or arbitrary variables)'),
          Attribute('setPostCallback',
                    default_value=None,
                    doc='callable that will be called with the new value '
                        'of a property *after* a change has taken place. '
                        'Use this to trigger actions depending on runtime '
                        'values of a property'),
          Attribute('doc',
                    default_value=None,
                    doc='doc-string'),
          ]

    def __init__(self, *args, **options):
        """
        constructor. Removes all attributes declared by the L{_Property}
        class from the L{options} dictionary.

        @param args: positional arguments to be passed to the base
          constructor
        @type args: variable-length tuple
        @param options: keyword arguments to be passed to the base
          constructor (minus options that are declared as attributes of
          the L{_Property} class)
        @type options: variable-length dictionary
        """
        for oAttribute in _Property.__attributes__:
            tDoSet = True
            try:
                oAttributeValue = options[oAttribute]
                del options[oAttribute]
            except KeyError:
                try:
                    oAttributeValue = oAttribute.default_value   # IGNORE:E1101
                except AttributeError:
                    tDoSet = False
            if tDoSet:
                setattr(self, oAttribute.name, oAttributeValue) # IGNORE:E1101

        options['allow_na'] = not self.is_not_none                 # IGNORE:E1101

        super(_Property, self).__init__(*args, **options)

    #
    # magic methods:
    #

    def __or__(self, other):
        """
        implements C{object.__or__}.__class__

        @return: L{PropertyGroup} instance built from this property and the
          property given in L{other}.        """
        return PropertyGroup(self, other)

    __ror__ = __or__


def isProperty(oObject):
    """
    checks if the given object is an instance of L{_Property}.

    @param oObject: object to check
    @type oObject: arbitrary object
    """
    return isinstance(oObject, _Property)


class Property(_Property, Variable):
    """
    Implements a generic property that can hold any value
    """

    __attributes__ = []

    def validate(self, value):
        """
        overrides L{pdk.variables.Variable.validate}.
        """
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Implements L{Variable._get_default_description_string}.
        """
        return 'an arbitrary property value'

    def _get_default_valueString(self):
        """
        Implements L{Variable._get_default_valueString}.
        """
        return 'any value'


class DateTimeProperty(_Property, DateTimeVariable):
    """
    Implements a date/time property
    """

    __attributes__ = []


class StringProperty(_Property, StringVariable):
    """
    Implements a string property
    """

    __attributes__ = []


class NumberProperty(_Property, NumberVariable):
    """
    Implements a number property
    """

    __attributes__ = []


class CharProperty(_Property, CharVariable):
    """
    Implements a char property
    """

    __attributes__ = []


class IntProperty(_Property, IntVariable):
    """
    Implements an integer property
    """

    __attributes__ = []


class FloatProperty(_Property, FloatVariable):
    """
    Implements an float property
    """

    __attributes__ = []


class BooleanProperty(_Property, BooleanVariable):
    """
    Implements a boolean property
    """

    __attributes__ = []


class EnumProperty(_Property, EnumVariable):
    """
    Implements an enumeration property
    """

    __attributes__ = []


class SequenceProperty(_Property, SequenceVariable):
    """
    Implements a sequence property
    """

    __attributes__ = []


ListProperty = SequenceProperty


class TupleProperty(_Property, TupleVariable):
    """
    Implements a tuple property
    """

    __attributes__ = []


class MappingProperty(_Property, MappingVariable):
    """
    Implements a mapping property
    """

    __attributes__ = []


DictionaryProperty = MappingProperty


class ArrayProperty(_Property, ArrayVariable):
    """
    Implements an array property
    """

    __attributes__ = []


class FunctionProperty(_Property, FunctionVariable):
    """
    Implements a function property
    """

    __attributes__ = []


class InstanceProperty(_Property, InstanceVariable):
    """
    Implements a instance property
    """

    __attributes__ = []


class RectangleProperty(_Property, RectangleVariable):
    """
    Implements a rectangle property
    """

    __attributes__ = []


class PositionProperty(_Property, PositionVariable):
    """
    Implements a position property
    """

    __attributes__ = []


class StaticProperty(property):
    """
    Specialization of the builtin C{property} that calls the get/set/del
    accessors without passing the object instance as first argument
    """

    def __get__(self, instance, objtype=None):
        """
        Overrides C{property.__get__}.
        """
        if self.fget is None:
            raise AttributeError("Can not read attribute")
        return self.fget()

    def __set__(self, instance, value):
        """
        Overrides {property.__set__}.
        """
        if self.fset is None:
            raise AttributeError('Can not set attribute')
        self.fset(value)

    def __delete__(self, instance):
        """
        Overrides C{property.__delete__}.
        """
        if self.fdel is None:
            raise AttributeError('Can not delete attribute')
        self.fdel()


class VirtualProperty(VirtualDeclaration):
    """
    Defines a virtual property.

    See L{pdk.declarations.VirtualDeclaration}.
    """

    #
    # protected methods:
    #

    def _get_error_class(self):
        """
        Implements L{pdk.declarations.VirtualDeclaration._get_error_class}.
        """
        return NotImplementedPropertyError


class PropertyGroup(_Property, VariableGroup):
    """
    Implements "or" operations on properties
    """

    __attributes__ = []


class NotImplementedPropertyError(NotImplementedAttributeErrorBase):
    """
    Class for not implemented virtual property access errors

    See the L{pdk.properties.VirtualProperty} class for details.
    """

    #
    # protected methods:
    #

    @staticmethod
    def _getMessageString(name, cls):
        """
        Implements L{_SmartNotImplementedError._getMessageString}.
        """
        return 'classes derived from "%s.%s" need to define a "%s" ' \
               'property!' % (cls.__module__, cls.__name__, name)

    @staticmethod
    def _getDeclarationClass():
        """
        Implements L{NotImplementedAttributeErrorBase._getDeclarationClass}.
        """
        return VirtualProperty
