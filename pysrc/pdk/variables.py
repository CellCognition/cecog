"""
Variable classes.

Variables are values with a type, a default, and possibly a restricted
range. They also can carry documentation and know how to convert a literal
into a valid variable value.

This code incorporates ideas taken from Graphite, which was originally written
by Joseph and Michelle Strout in 1999.

Usage: ::

    >>> from pdk.variables import CharVariable,StringVariable, \
                                  BooleanVariable,FloatVariable, \
                                  IntVariable,ListVariable, \
                                  DateTime,DateTimeVariable, \
                                  VALID,INVALID,PARTIAL,as_bool, \
                                  get_date_format,set_date_format
    >>> fv = FloatVariable(1., min_value=0., max_value=2., info=('test','float'))
    >>> fv.validate(2.)
    2.0
    >>> try:
    ...     fv.validate(2.1)
    ... except ValueError:
    ...     pass
    >>> fv.get_default_value()
    1.0
    >>> print fv.get_info_string()
    Description:
    test
    Value(s):
    float
    >>> fv.as_type('1.0')
    1.0
    >>> fv.check_literal('.') == PARTIAL   # partially valid literal for a float
    True
    >>> fv.check_literal('.5') == VALID    # valid literal for a float
    True
    >>> fv.check_literal('.5a') == INVALID # invalid literal for a float
    True
    >>> fv.convert_from_literal('1.0')
    1.0
    >>> fv.convert_to_literal(2.)
    '2.0'
    >>> sv = StringVariable('aa', min_length=2, max_length=5, mask='a+$')
    >>> try:
    ...     sv.validate('a')
    ... except ValueError,msg:
    ...     print msg
    length of string 'a' out of range [2...5] for StringVariable
    >>> try:
    ...     sv.validate('ab')
    ... except ValueError,msg:
    ...     print msg
    string 'ab' does not match mask 'a+$' of StringVariable
    >>> # variable group:
    >>> vg = fv | sv
    >>> vg.validate(1.0) #
    1.0
    >>> vg.validate('aa')
    'aa'
    >>> cv = CharVariable('', allow_na=True)
    >>> try:
    ...     cv.validate('aa')
    ... except ValueError,msg:
    ...     print msg
    unable to convert to Char: 'aa'
    >>> bv = BooleanVariable('True')
    >>> bv.validate(0)
    False
    >>> as_bool('true')
    True
    >>> try:
    ...     as_bool('2')
    ... except ValueError:
    ...     pass
    >>> lv = ListVariable(None, min_length=1, max_length=3, elementVariable=fv)
    >>> lv.validate([2.,'2.']) # automatic conversion to float
    [2.0, 2.0]
    >>> try:
    ...    lv.validate([2.,'a'])
    ... except ValueError,msg:
    ...    print msg
    unable to convert to Float: a
    >>> try:
    ...    lv.validate([2.,2.,2.,2.])
    ... except ValueError,msg:
    ...    print msg
    sequence too long (must contain at most 3 elements) for ListVariable
    >>> set_date_format('%d %b %Y %H:%M') # set a new default date format
    >>> # convert from DateTime, display in special format:
    >>> dt = DateTime('21 Apr 2004 08:00')
    >>> dv1 = DateTimeVariable(dt, display_format='%Y.%m.%d %H:%M:%S')
    >>> dv1.convert_to_literal(dt)
    '2004.04.21 08:00:00'
    >>> # convert from string with special format, display in global format:
    >>> dv2 = DateTimeVariable('2004.04.21',
    ...                        conversion_format='%Y.%m.%d')
    >>> dv2.convert_to_literal(dv2.default_value)
    '21 Apr 2004 00:00'

FOG 03.2000,08.2001
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['INVALID',
           'PARTIAL',
           'VALID',
           'ArrayVariable',
           'BooleanVariable',
           'CharVariable',
           'DateTime',
           'DateTimeVariable',
           'DictionaryVariable',
           'EnumVariable',
           'FloatVariable',
           'FunctionVariable',
           'InstanceVariable',
           'IntVariable',
           'ListVariable',
           'MappingVariable',
           'NumberVariable',
           'OptionsVariable',
           'PairVariable',
           'PositionVariable',
           'RectangleVariable',
           'SequenceVariable',
           'StringVariable',
           'TupleVariable',
           'Variable',
           'VariableGroup',
           'as_array',
           'as_array_or_na',
           'as_bool',
           'as_bool_or_na',
           'as_char',
           'as_char_or_na',
           'as_datetime',
           'as_datetime_or_na',
           'as_float',
           'as_float_or_na',
           'as_int',
           'as_int_or_na',
           'as_list',
           'as_pair',
           'as_string',
           'as_string_or_na',
           'as_tuple',
           'get_date_format',
           'get_variable_for_value',
           'set_date_format',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import operator
import re
import string
import sys
import time
import types
from datetime import datetime as _datetime

#------------------------------------------------------------------------------
# extension module imports:
#
from numpy import (asarray,
                   float32,
                   log10,
                   ndarray,
                   power)

#------------------------------------------------------------------------------
# pdk imports:
from pdk.errors import IllegalArgumentError
from pdk.attributemanagers import (get_attribute_values,
                                   set_attribute_values)
from pdk.attributes import Attribute
from pdk.iterator import all_of_type

#------------------------------------------------------------------------------
# constants:
#
MAXINT = sys.maxint
MININT = -sys.maxint - 1
MAXFLOAT = 1e+308
MINFLOAT = -1e308

# FIXME: make this a proper const group
INVALID = 0
VALID = 1
PARTIAL = 2

#------------------------------------------------------------------------------
# helper functions:
#

def get_variable_for_value(value, **options):
    """
    Converts the given value to a pdk variable of the proper class.

    Of course, this conversion only works for the standard Python types (not
    supported are C{unicode} and C{set}!).

    @param value: value to be converted to a pdk variable
    @type value: L{object}
    @param options: keyword arguments to be passed to the selected variable
      constructor
    @type options: variable-length dictionary
    @note: the value conversion attempts to be 'smart' about input strings;
    for instance, a L{value} of "1" will be converted to a L{BooleanVariable}.
    """
    py_type = type(value)
    if issubclass(py_type, types.InstanceType):
        var = InstanceVariable(value, value.__class__, **options)
    else:
        if issubclass(py_type, tuple):
            var_class = TupleVariable
        elif issubclass(py_type, list):
            var_class = ListVariable
        elif issubclass(py_type, dict):
            var_class = DictionaryVariable
        elif issubclass(py_type, types.FunctionType):
            var_class = FunctionVariable
        elif py_type is ndarray:
            var_class = ArrayVariable
        else:
            try:
                as_bool(value)
            except ValueError:
                try:
                    as_datetime(value)
                except ValueError:
                    try:
                        as_int(value)
                    except ValueError:
                        try:
                            as_float(value)
                        except ValueError:
                            if issubclass(py_type, basestring):
                                if len(value) == 1:
                                    var_class = CharVariable
                                else:
                                    var_class = StringVariable
                            else:
                                var_class = Variable
                        else:
                            var_class = FloatVariable
                    else:
                        var_class = IntVariable
                else:
                    var_class = DateTimeVariable
            else:
                var_class = BooleanVariable
        var = var_class(value, **options)
    return var

#------------------------------------------------------------------------------
# variable and property classes:
#

class _Variable(object):
    """
    Abstract base class for all variable classes

    Variables are objects with an associated type, a default value, and
    helping documentation. In addition, they provide methods for converting
    arbitrary given objects into an acceptable value (i.e., a value that has
    the correct type and possibly satsfies other constraints such as a
    restriction in length for strings) and in particular for converting
    a literal (string) representation of a value into the value itself and
    vice versa.

    @cvar CHARS: valid characters in literal representations of the values
      represented by this variable class
    @cvar REGEX: regular expression for matching literal representations
      of the values represented by this variable class
    """

    __attributes__ = [Attribute('allow_na',
                                doc='indicates if C{None} is an allowed '
                                    'value for this variable'),
                      Attribute('info',
                                doc='help information for this variable, '
                                    'provided in two strings - a general '
                                    'description and information about the '
                                    'acceptable variable value(s).'),
                      Attribute('default_value',
                                 doc='default value for this variable. If '
                                     'not explicitly set, this will be '
                                     'set to C{None}.')
                      ]

    CHARS = string.printable
    REGEX = re.compile('^[%s]*$' % CHARS)

    def __init__(self, default_value, info=None, allow_na=False):
        """
        Constructor.

        @param default_value: default value. See 'C{default_value}' attribute
        @type default_value: L{object}
        @param info: helping information for this variable. See
          'C{info}' attribute
        @type info: 2-tuple of strings
        @param allow_na: indicates if C{None} is an allowed value. See
          'C{allow_na}' attribute
        @type allow_na: Boolean
        """
        # Initializations.
        self.info = None
        self.allow_na = None
        # We generally allow C{None} as an initial default (signifies
        # 'undefined').
        self.default_value = None
        self.set_info(info)
        self.set_allow_na(allow_na)
        if not default_value is None:
            self.set_default_value(default_value)
        else:
            self.default_value = None

    #
    # magic methods:
    #

    def __or__(self, other_variable):
        """
        Implements C{object.__or__}.

        @return: variable group (L{VariableGroup} instance) composed of this
          and the other variable
        """
        return VariableGroup(self, other_variable)

    __ror__ = __or__

    def __getstate__(self):
        """
        Called to obtain state information from this variable.

        Calls L{pdk.attributemanagers.get_attribute_values}.

        @return: attribute value map (dictionary mapping attribute name
          strings to attribute values)
        """
        return get_attribute_values(self)

    def __setstate__(self, attribute_values):
        """
        Called to restore the state for this variable from the given
        state information.

        Calls L{pdk.attributemanagers.set_attribute_values}.

        @param attribute_values: attribute value map
        @type attribute_values: dictionary mapping attribute names (strings)
          to attribute values (L{object})
        """
        set_attribute_values(self, attribute_values)

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Tries to convert the given value to the value type of the variable
        class.

        This default implementation does not perform any conversion and
        returns L{value} as is.

        @param value: value to be converted
        @type value: L{object}
        @param allow_na: if set, C{None} is accepted as a value
        @type allow_na: Boolean
        @raise ValueError: if L{value} can not be converted to a value of the
          required type
        @return: value converted to the required type
        """
        if value is None and not allow_na:
            raise ValueError('Unable to convert to the required type: %s'
                             % (value,))
        return value

    @classmethod
    def as_type_or_na(cls, value, **options):
        """
        Like L{as_type}, but always allows NA values.
        """
        options['allow_na'] = True
        return cls.as_type(value, **options)

    def validate_type(self, value):
        """
        Validates the type of the given value by calling L{as_type} with the
        value of the "C{allow_na}" attribute as argument.

        @param value: value the type of which is to be validated
        @type value: L{object}
        @raise ValueError: if L{value}'s type can not be validated
        @return: L{value} converted to the type associcated with this
          variable class
        """
        return self.as_type(value, allow_na=self.allow_na)

    def check_type(self, value):
        """
        Checks if the given value can be converted to the type associated
        with this variable class. Calls L{validate_type} to accomplish this.

        @param value: value to check
        @type value: L{object}
        @return: check result
        @rtype: L{bool}
        """
        try:
            self.validate_type(value)
        except ValueError:
            check_result = False
        else:
            check_result = True
        return check_result

    def validate_value(self, value):
        """
        Validates the given value (which is assumed to be of the type
        associated with this variable class) to an acceptable value for this
        variable instance.

        The default implementation always returns L{value} unchanged.

        @param value: the value to be validated
        @type value: L{object}
        @raise ValueError: if L{value} can not be converted to a valid value
        @return: acceptable value for this variable instance
        """
        return value

    def check_value(self, value):
        """
        Checks if the given value is an acceptable value for this variable
        instance. Calls L{validate_value} to accomplish this.

        @param value: value to check
        @type value: L{object}
        @return: Boolean
        """
        try:
            self.validate_value(value)
        except ValueError:
            check_result = False
        else:
            check_result = True
        return check_result

    def convert_from_literal(self, literal):
        """
        Converts the given literal to a value for this variable.

        The default implementation calls the L{validate_type} method and
        returns its return value.

        @param literal: literal to convert
        @type literal: string
        @return: L{literal} converted to the type associated with this
          variable class
        """
        return self.validate_type(literal)

    def convert_to_literal(self, value, width=None):
        """
        Converts the given value to a literal representation.

        @param value: value to convert to a literal (=string)
        @type value: L{object}
        @param width: width of the resulting literal
        @type width: integer
        @note: no checks are made if L{value} is valid
        @return: L{value} converted to a literal (string)
        """
        if value is None:
            literal = ''
        else:
            if width is None:
                literal = str(value)
            else:
                literal = str(value).rjust(width)
        return literal

    def check_char(self, char):
        """
        Checks if the given character is valid in a literal representation of
        this variable class.

        @param char: character to test
        @type char: string
        @return: Boolean
        """
        return char in self.CHARS

    def check_literal(self, literal):
        """
        Checks whether the given literal is a valid literal representation
        of the values represented by this variable class. Calls the
        C{convert_from_literal} method and the L{validate_value} method on the
        result value. If the former raises an error, the
        L{_handle_literal_nonvalid_type} method is called with L{literal} as
        input; if the latter raises an error, the
        L{_handle_literal_nonvalid_value} method is called with the
        type-validated value returned from L{convert_from_literal} as input.

        @param literal: literal to check
        @type literal: string
        @return: one of the validation constants L{INVALID} (invalid literal),
          L{VALID} (valid literal), or L{PARTIAL} (part of a valid literal)
        """
        if self.REGEX.match(literal):
            try:
                value = self.convert_from_literal(literal)
            except ValueError:
                iResult = self._handle_literal_nonvalid_type(literal) # IGNORE:E1111
            else:
                if value is None:
                    iResult = self.allow_na and VALID or INVALID
                else:
                    try:
                        self.validate_value(value)
                    except ValueError:
                        iResult = self._handle_literal_nonvalid_value(literal, # IGNORE:E1111
                                                                  value)
                    else:
                        iResult = VALID
        else:
            iResult = self._handle_literal_nonvalid_type(literal) # IGNORE:E1111
        return iResult

    def validate(self, value):
        """
        Validates the given value as an accepted value for this variable
        instance by calling L{validate_type} with L{value} as input and
        L{validate_value} with the return value from that call.

        @note: if L{value} is C{None} and the C{allow_na} flag is set,
          L{validate_value} is not called
        @param value: value to validate
        @type value: L{object}
        @return: acceptable value for this variable instance (of the type
          associated with this variable class)
        """
        value = self.validate_type(value)
        if not value is None:
            value = self.validate_value(value)
        return value

    def set_default_value(self, newDefaultValue):
        """
        Write accessor for the "C{default_value}" attribute. Calls
        L{validate} on the given value.

        @param newDefaultValue: new value for the "C{default_value}"
          attribute
        @type newDefaultValue: L{object}
        """
        self.default_value = self.validate(newDefaultValue)

    def get_default_value(self):
        """
        Read accessor for the "C{default_value}" attribute.

        @return: value of the "C{default_value}" attribute (of the type
          associated with this variable class)
        """
        return self.default_value

    def set_allow_na(self, flag):
        """
        Write accessor for the "C{allow_na}" attribute.

        @param flag: new value for the "C{allow_na}" attribute
        @type flag: Boolean
        """
        self.allow_na = flag

    def get_allow_na(self):
        """
        Read accessor for the "C{allow_na}" attribute.

        @return: value of the "C{allow_na}" attribute (Boolean)
        """
        return self.allow_na

    def set_info(self, info):
        """
        Write accessor for the "C{info}" attribute.

        @param info: new value for the "C{info}" attribute. If only
          one string is provided, it is assumed to contain the description
          info string, in which case the value info string is set to the
          class default. If C{None} is given, both the description and the
          value info string are set to the class default
        @type info: 2-tuple of strings, or string, or C{None}
        @raise IllegalArgumentError: if the given value L{info} does not
          have the required type
        """
        if not info is None:
            if isinstance(info, tuple) and len(info) == 2:
                help_description, help_value = info
            else:
                if isinstance(info, basestring):
                    help_description = info
                    help_value = self._get_default_value_string()
                else:
                    raise IllegalArgumentError('Value for the "info" '
                                               'parameter must be a 2-tuple '
                                               'of strings, or a string, or '
                                               'None')
        else:
            help_description = self._get_default_description_string()
            help_value = self._get_default_value_string()
        self.info = help_description, help_value

    def getInfo(self):
        """
        Read accessor for the "C{info}" attribute.

        @return: value of the "C{info}" attribute (2-tuple)
        """
        return self.info

    def get_info_string(self):
        """
        Returns a string describing the variable and its acceptable values.

        @return: information string (string)
        """
        return "%s (%s)" % self.info

    def get_description_info(self):
        """
        Returns the description part of the "C{info}" attribute.

        @return: variable description (string)
        """
        return self.info[0]

    def get_value_info(self):
        """
        Returns the value information part of the "C{info}" attribute.

        @return: variable value information (string)
        """
        return self.info[1]

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Returns a default value for the description information part of the
        "C{info}" attribute.

        @return: description information (string)
        """
        raise NotImplementedError('Abstract method.')

    def _get_default_value_string(self):
        """
        Returns a default value for the value information part of the
        "C{info}" attribute.

        @return: value information (string)
        """
        raise NotImplementedError('Abstract method.')

    def _handle_literal_nonvalid_type(self, literal): # pylint: disable-msg=W0613
        """
        Handles an exception caused by the given literal not being of the
        required variable type.

        Implementations of this method may handle special cases where the
        L{convert_from_literal} failed with L{literal} as input and return one
        of the three validation constants.

        @param literal: literal to convert
        @type literal: string
        @return: one of the validation constants L{INVALID} (invalid literal),
          L{VALID} (valid literal), or L{PARTIAL} (part of a valid literal)
        """
        return INVALID

    def _handle_literal_nonvalid_value(self, literal, value): # pylint: disable-msg=W0613
        """
        Handles an exception caused by the given literal not having a valid
        value.

        Implementations of this method may handle special cases where the
        L{validate_value} method failed with the literal L{literal} as input
        and return one of the three validation constants.

        @param literal: literal to convert
        @type literal: string
        @param value: value the literal was type-converted to
        @type value: instance of the class associcated with this variable
        @return: one of the validation constants L{INVALID} (invalid literal),
          L{VALID} (valid literal), or L{PARTIAL} (part of a valid literal)
        """
        return PARTIAL


class Variable(_Variable):
    """
    Variable holding an arbitrary value
    """

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Returns a default value for the description information part of the
        "C{info}" attribute.

        @return: description information (string)
        """
        return 'arbitrary value'

    def _get_default_value_string(self):
        """
        Returns a default value for the value information part of the
        "C{info}" attribute.

        @return: value information (string)
        """
        return 'not specified'


class CharVariable(_Variable):
    """
    Char variable.
    """

    __attributes__ = []

    REGEX = re.compile('[%s]?' % _Variable.CHARS)

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Overrides L{Variable.as_type}.
        """
        is_ok = True
        if isinstance(value, basestring):
            is_ok = len(value) == 1 or (len(value) == 0 and allow_na)
            if is_ok:
                result_value = value
        else:
            try:
                result_value = ord(value)
            except:
                if allow_na and value is None: # legitimate catch-all pylint: disable-msg=W0702
                    result_value = value
                else:
                    is_ok = False
        if not is_ok:
            raise ValueError('Unable to convert to character value: %s' %
                             str(value))
        return result_value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        return 'character value'

    def _get_default_value_string(self):
        return 'single character'

    def _handle_literal_nonvalid_value(self, literal, value):
        return PARTIAL

as_char = CharVariable.as_type
as_char_or_na = CharVariable.as_type_or_na


class StringVariable(_Variable):
    """
    String variable
    """

    __attributes__ = [Attribute('min_length',
                                doc='minimum length for the string held by '
                                    'this string variable'),
                      Attribute('mask',
                                doc='regular expression matching all '
                                    'acceptable values of this string '
                                    'variable'),
                      Attribute('max_length',
                                doc='maximum length for the string held by '
                                    'this string variable'),
                      ]

    def __init__(self, default_value,
                 min_length=None, max_length=None, mask=None, **options):
        """
        Extends L{Variable.__init__}. Additional keywords arguments:

        @param min_length: minimum string length. See "C{min_length}" attribute
        @type min_length: integer
        @param mask: matching regular expression. See "C{mask}" attribute
        @type mask: regular expression instance or string
        @param max_length: maximum string length. See "C{max_length}" attribute
        @type max_length: integer
        """
        self.mask = None
        self.min_length = None
        self.max_length = None
        self.set_mask(mask)
        self.set_max_length(max_length)
        self.set_min_length(min_length)
        super(StringVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_min_length(self, min_length):
        """
        Write accessor for the "C{min_length}" attribute

        @param min_length: new minimum length
        @type min_length: integer
        """
        self.min_length = min_length

    def get_min_length(self):
        """
        Read accessor for the "C{min_length}" attribute

        @return: value of the "C{min_length}" attribute (integer)
        """
        return self.min_length

    def set_max_length(self, max_length):
        """
        Write accessor for the "C{max_length}" attribute

        @param max_length: new maximum length
        @type max_length: integer
        """
        self.max_length = max_length

    def get_max_length(self):
        """
        Read accessor for the "C{max_length}" attribute.

        @return: value of the "C{max_length}" attribute (integer)
        """
        return self.max_length

    def set_range(self, min_length, max_length):
        """
        Sets the minimum and maximum allowed length to the given range.

        @param min_length: minimum allowed length; sets the "C{min_length}"
          attribute
        @type min_length: integer
        @param max_length: maximum allowed length; sets the "C{max_length}"
          attribute
        @type max_length: integer
        """
        self.set_max_length(max_length)
        self.set_min_length(min_length)

    def get_range(self):
        """
        Returns the current minimum and maximum allowed length.

        @return: value of the "C{min_length}" and "C{max_length}" attributes
          (2-tuple)
        """
        return self.min_length, self.max_length

    def set_mask(self, mask):
        """
        Write accessor for the "C{mask}" attribute.

        @param mask: new mask
        @type mask: regular expression instance or string
        """
        if isinstance(mask, basestring):
            mask = re.compile(mask)
        self.mask = mask

    def get_mask(self):
        """
        Read accessor for the "C{mask}" attribute

        @return: value of the "C{mask}" attribute (regular expression
          instance or string)
        """
        return self.mask

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Overrides L{Variable.as_type}.
        """
        if not value is None:
            if not isinstance(value, basestring):
                try:
                    result = str(value)
                except UnicodeEncodeError:
                    result = unicode(value)
            else:
                result = value
        else:
            if allow_na:
                result = None
            else:
                raise ValueError('Unable to convert to string value (%s)' %
                                 value)
        return result

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        min_len = self.min_length
        max_len = self.max_length
        if not self.mask is None and not self.mask.match(value):
            raise ValueError('String "%s" does not match mask "%s" '
                             % (value, self.mask.pattern))
        if (not min_len is None and len(value) < min_len) or \
           (not max_len is None and len(value) > max_len):
            raise ValueError('Length of string "%s" out of range [%s..%s]'
                             % (value, min_len, max_len))
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Implements L{Variable._get_default_description_string}.
        """
        return 'string value'

    def _get_default_value_string(self):
        """
        Implements L{Variable._get_default_value_string}.
        """
        if self.min_length is None:
            if self.max_length is None:
                val_string = 'arbitrary length'
            else:
                val_string = 'at most %d characters' % self.max_length
        else:
            if self.max_length is None:
                val_string = 'at least %d characters' % self.min_length
            else:
                val_string = 'at least %d and at most %d ' \
                             % (self.min_length, self.max_length)
        if not self.mask is None:
            val_string += ', matching the mask "%s"' \
                          % (self.mask if isinstance(self.mask, basestring)
                             else self.mask.pattern)
        return val_string

    def _handle_literal_nonvalid_type(self, literal):
        """
        Implements L{Variable._handle_literal_nonvalid_type}.
        """
        if literal is None:
            result = PARTIAL
        else:
            result = VALID
        return result

as_string = StringVariable.as_type
as_string_or_na = StringVariable.as_type_or_na


class DateTime(_datetime):
    """
    Date/time type that knows how to display itself

    @cvar DATE_FORMAT: default format for date time strings. Use the
      L{set_date_format} method to change this for future L{DateTime}
      instances
    """

    DATE_FORMAT = r'%b %d %Y %H:%M:%S'

    def __new__(cls, value='now', format=None):
        """
        Called to obtain a new instance of this class.

        @param value: date/time value. The string 'C{now}' is translated into
          the current time
        @type value: string (converted with C{time.strptime}), float
          (converted with C{datetime.fromtimestamp} function),
          C{datetime.datetime} instance, or tuple (using the standard
          C{datetime.datetime} constructor
        @param format: format to use for conversion from a string. Stored in
          the 'C{format}' attribute
        @type format: string
        """
        if format is None:
            format = cls.DATE_FORMAT
        if isinstance(value, tuple):
            instance = super(DateTime, cls).__new__(cls, *value) # pylint: disable-msg=W0142
        else:
            if value == 'now':
                base_instance = _datetime.now()
            elif isinstance(value, _datetime):
                base_instance = value
            elif isinstance(value, basestring):
                ticks = time.mktime(time.strptime(value, format))
                base_instance = _datetime.fromtimestamp(ticks)
            elif isinstance(value, float):
                base_instance = _datetime.fromtimestamp(value)
            elif isinstance(value, tuple):
                base_instance = _datetime(*value) # pylint: disable-msg=W0142
            else:
                raise IllegalArgumentError('Unable to convert "%s" into a '
                                           'date/time variable!' % (value,))
            # pylint inexplicably inferrs a type of str for base_instance
            # pylint: disable-msg=E1103
            instance = super(DateTime, cls).__new__(cls,
                                                    base_instance.year,
                                                    base_instance.month,
                                                    base_instance.day,
                                                    base_instance.hour,
                                                    base_instance.minute,
                                                    base_instance.second,
                                                    base_instance.microsecond,
                                                    base_instance.tzinfo)
            # pylint: enable-msg=E1103
        instance.format = format
        return instance

    #
    # magic methods:
    #

    def __str__(self):
        """
        Called to obtain a string representation for this date time object.
        """
        return self.strftime()

    def __getstate__(self):
        """
        Called to obtain the state of this datetime object.

        @return: state information (9-tuple)
        """
        return (self.year, self.month, self.day, self.hour, self.minute,
                self.second, self.microsecond, self.tzinfo, self.format)

    def __setstate__(self, info):
        """
        Called to set the state of this datetime object.

        @param info: state information
        @type info: 9-tuple
        """
        self.replace(year=info[0], month=info[1], day=info[2], hour=info[3],
                     minute=info[4], second=info[5], microsecond=info[6],
                     tzinfo=info[7])
        self.format = info[8] # pylint: disable-msg=W0201

    #
    # public methods:
    #

    @staticmethod
    def set_date_format(format):
        """
        Changes the default date time format for all following L{DateTime}
        instances (sets the L{DateTime.DATE_FORMAT} class attribute).

        @param format: date formatting string
        @type format: string
        """
        DateTime.DATE_FORMAT = format

    @staticmethod
    def get_date_format():
        """
        Returns the current (class) default date time format.

        @return: time format (string)
        """
        return DateTime.DATE_FORMAT

    def strftime(self, format=None):
        """
        Extends L{datetime.datetime.strftime}.

        @param format: format for conversion from a string
        @type format: string
        @return: formatted date time (string)
        """
        if format is None:
            format = self.format
        return super(DateTime, self).strftime(format)

    def ticks(self):
        """
        Returns the seconds since the epoch for this date time value.

        @return: time value in seconds (float)
        """
        return time.mktime(self.timetuple())

set_date_format = DateTime.set_date_format
get_date_format = DateTime.get_date_format


class DateTimeVariable(_Variable):
    """
    Date/time variable
    """

    __attributes__ = [Attribute('conversion_format',
                                doc='format for conversion from a string'),
                      Attribute('display_format',
                                doc='format for conversion to a string'),
                      ]

    CHARS = r'-.:/() ' + string.digits + string.ascii_letters
    REGEX = re.compile('[%s]*' % CHARS)

    def __init__(self, default_value,
                 conversion_format=None, display_format=None, **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param conversion_format: I{from} string conversion format; see
          "C{conversion_format}" attribute
        @type conversion_format: string
        @param display_format: I{to} string conversion format; see
          "C{display_format}" attribute
        @type display_format: string
        """
        self.conversion_format = None
        self.display_format = None
        self.set_conversion_format(conversion_format)
        self.set_display_format(display_format)
        super(DateTimeVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_conversion_format(self, format_string):
        """
        Write accessor for the "C{conversion_format}" attribute.

        @param format_string: new conversion format. If C{None} is given, the
          default class date format string as returned by L{get_date_format}
          is used
        @type format_string: string
        """
        self.conversion_format = not format_string is None and format_string \
                                or get_date_format()

    def getConversionFormat(self):
        """
        Read accessor for the "C{conversion_format}" attribute.

        @return: value of the "C{conversion_format}" attribute (string)
        """
        return self.conversion_format

    def set_display_format(self, format_string):
        """
        Write accessor for the "C{display_format}" attribute.

        @param format_string: new display format. If C{None} is given, the
          default class date format string as returned by L{get_date_format}
          is used
        @type format_string: string
        """
        self.display_format = not format_string is None and format_string \
                             or get_date_format()

    def getDisplayFormat(self):
        """
        Read accessor for the "C{display_format}" attribute.

        @return: value of the "C{display_format}" attribute (string)
        """
        return self.display_format

    @staticmethod
    def as_type(value, # intentional signature change pylint: disable-msg=W0221
                allow_na=False, format_string=None):
        """
        Overrides L{Variable.as_type}. Additional keyword arguments:

        @param format_string: format for conversion from a string
        @type format_string: string
        @note: for allowed types for L{value} see the L{DateTime} constructor.
        """
        if isinstance(value, DateTime):
            result_value = value
        else:
            if format_string is None:
                format_string = get_date_format()
            try:
                result_value = DateTime(value, format_string)
            except:
                if allow_na and value in (None,''): # catch-all pylint: disable-msg=W0702
                    result_value = None
                else:
                    raise ValueError('Unable to convert to formatted '
                                     'date time value (value: %s, '
                                     'format string: %s)' %
                                     (value, format_string))
        return result_value

    def convert_from_literal(self, literal):
        """
        Overrides L{Variable.convert_from_literal}.
        """
        return self.as_type(literal,
                           format_string=self.conversion_format,
                           allow_na=self.allow_na)

    def convert_to_literal(self, value, width=None):
        """
        Overrides L{Variable.convert_to_literal}.
        """
        try:
            result_literal = value.strftime(self.display_format)
        except AttributeError:
            result_literal = \
                 super(DateTimeVariable, self).convert_to_literal(value, width)
        return result_literal

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        return self.as_type(value,
                           format_string=self.conversion_format,
                           allow_na=self.allow_na)

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Implements L{Variable._get_default_description_string}.
        """
        return 'date/time value'

    def _get_default_value_string(self):
        """
        Implements L{Variable._get_default_value_string}.
        """
        return 'string in the format "%s"' % self.conversion_format

    def _handle_literal_nonvalid_type(self, literal):
        """
        Implements L{Variable._handle_literal_nonvalid_type}.
        """
        return (literal == '' and self.allow_na and VALID) or PARTIAL

as_datetime = DateTimeVariable.as_type
as_datetime_or_na = DateTimeVariable.as_type_or_na


class NumberVariable(_Variable):
    """
    Number variable
    """

    __attributes__ = [Attribute('max_value',
                                doc='maximum variable value for this '
                                    'variable'),
                      Attribute('min_value',
                                doc='minimum variable value for this '
                                    'variable'),
                      ]

    CHARS = string.digits
    REGEX = re.compile('^[0-9]*$')

    def __init__(self, default_value,
                 min_value=None, max_value=None, **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param max_value: maximum value. See "C{min_value"}" attribute
        @type max_value: number type
        @param min_value: minimum value. See "C{max_value}" attribute
        @type min_value: number type
        """
        self.max_value = None
        self.min_value = None
        self.set_max_value(max_value)
        self.set_min_value(min_value)
        super(NumberVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_min_value(self, min_value):
        """
        Write accessor for the "C{min_value}" attribute.

        @param min_value: new minimum value
        @type min_value: number type
        """
        self.min_value = min_value

    def get_min_value(self):
        """
        Read accessor for the "C{min_value}" attribute.

        @return: value of the "C{min_value}" attribute
        """
        return self.min_value

    def set_max_value(self, max_value):
        """
        Write accessor for the "C{max_value}" attribute.

        @param max_value: new maximum value
        @type max_value: number type
        """
        self.max_value = max_value

    def get_max_value(self):
        """
        Read accessor for the "C{max_value}" attribute.

        @return: value of the "C{max_value}" attribute
        """
        return self.max_value

    def set_range(self, min_value, max_value):
        """
        Sets the minimum and maximum value to the given range.

        @param min_value: minimum allowed value; sets the "C{min_value}"
          attribute
        @type min_value: integer
        @param max_value: maximum allowed value; sets the "C{max_value}"
          attribute
        @type max_value: integer
        """
        self.set_max_value(max_value)
        self.set_min_value(min_value)

    def get_range(self):
        """
        Returns the current range of allowed minimum and maximum values.

        @return: value of the "C{min_value}' and "C{max_value}" attributes
          (2-tuple)
        """
        return self.min_value, self.max_value

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        min_val = self.min_value
        max_val = self.max_value
        if (not min_val is None and value < min_val) or \
           (not max_val is None and value > max_val):
            raise ValueError('Value %s out of range [%s..%s]' %
                             (value, min_val, max_val))
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Implements L{Variable._get_default_description_string}.
        """
        return '%s value'

    def _get_default_value_string(self):
        """
        Implements L{Variable._get_default_value_string}.
        """
        if self.min_value is None:
            if self.max_value is None:
                val_string = 'unrestricted range'
            else:
                val_string = 'smaller than or equal to %d' % \
                         self.max_value
        else:
            if self.max_value is None:
                val_string = 'larger than or equal to %d' % \
                         self.min_value
            else:
                val_string = 'larger than or equal to %s ' \
                         'and smaller than or equal to %s.' \
                         % (self.min_value, self.max_value)
        return val_string

    def _handle_literal_nonvalid_type(self, literal):
        """
        Implements L{Variable._handle_literal_nonvalid_type}.
        """
        if literal == '':
            if not self.allow_na:
                result = PARTIAL
            else:
                result = VALID
        elif literal == '-' and self.max_value < 0 or \
               literal == '+' and self.min_value > 0:
            result = PARTIAL
        else:
            result = INVALID
        return result


class IntVariable(NumberVariable):
    """
    Integer variable

    @note: this class subsumes the two Python types C{int} and C{long}
      (i.e., if a value/literal is too big for a plain C{int}, it is
      automatically converted to a C{long}).
    """

    __attributes__ = []

    CHARS = string.digits + '+-'
    REGEX = re.compile(r'^[-+]?\d*$')

    def __init__(self, default_value,
                 min_value=None, max_value=None, **options):
        """
        Overrides L{NumberVariable.__init__}.
        """
        if min_value is None:
            min_value = MININT
        else:
            min_value = int(min_value)
        if max_value is None:
            max_value = MAXINT
        else:
            max_value = int(max_value)
        super(IntVariable, self).__init__(default_value, min_value=min_value,
                                          max_value=max_value, **options)

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Overrides L{Variable.as_type}.
        """
        try:
            result = int(value)
        except:
            try: # catch-all pylint: disable-msg=W0702
                result = long(value)
            except:
                if allow_na and value in ('', None): # catch-all pylint: disable-msg=W0702
                    result = None
                else:
                    raise ValueError('Unable to convert to integer: %s' % value)
        return result

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{NumberVariable._get_default_description_string}.
        """
        return NumberVariable._get_default_description_string(self) % 'integer'

as_int = IntVariable.as_type
as_int_or_na = IntVariable.as_type_or_na


class FloatVariable(NumberVariable):
    """
    Float variable
    """

    __attributes__ = []

    CHARS = string.digits + 'eE+-.'
    REGEX = re.compile(r'^[-+]?(\d*|\d+\.\d*|\.\d*)(e[-+]?\d{1,3})?$')

    def __init__(self, default_value,
                 min_value=MINFLOAT, max_value=MAXFLOAT, **options):
        """
        Extends L{NumberVariable.__init__}.
        """
        if min_value is None:
            min_value = MINFLOAT
        else:
            min_value = float(min_value)
        if max_value is None:
            max_value = MAXFLOAT
        else:
            max_value = float(max_value)
        super(FloatVariable, self).__init__(default_value, min_value=min_value,
                                            max_value=max_value, **options)

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Overrides L{Variable.as_type}.
        """
        try:
            result = float(value)
        except:
            if allow_na and value in ('', None): # catch-all pylint: disable-msg=W0702
                result = None
            else:
                raise ValueError('Unable to convert to float: %s' % value)
        return result

    def convert_to_literal(self, value, # intentional signature change pylint: disable-msg=W0221
                           width=None, precision=3, exp=False):
        """
        Overrides L{Variable.convert_to_literal}. Additional keyword arguments:

        @param precision: number of digits to round to
        @type precision: Integer
        @param exp: format in exponential notation
        @type exp: Boolean
        """
        if value is None:
            literal = ''
        else:
            if width is None:
                literal = str(round(value, precision))
            else:
                has_sign = value < 0
                if not exp:
                    if value < -1 or value > 1:
                        width = int(log10(abs(value))) + 1
                    else:
                        width = 1
                    digit_count = min(precision, width - width - 1 - has_sign)
                    # Switch to e-notation for negative values.
                    if digit_count >= 0:
                        return str(round(value, digit_count)).rjust(width)
                # From here on, we are formatting e-notation.
                if has_sign:
                    sign_char = '-'
                else:
                    sign_char = ''
                if 0 < value < 1:
                    exp_val = int(log10(abs(value))) - 1
                    exp_has_sign = True
                elif value != 0:
                    exp_val = int(log10(abs(value)))
                    exp_has_sign = False
                else:
                    exp_val = 0
                    exp_has_sign = False
                exp_string = str(exp_val)
                # The __builtin__ C{round} cuts off zeros at the end, so we
                # might have to pad with spaces.
                digit_count = \
                        min(precision,
                            width - len(exp_string)-3-has_sign-exp_has_sign)
                mant = round(abs(value) / power(10., exp_val), digit_count)
                mant_string = str(mant).ljust(digit_count)
                literal = (sign_char+mant_string+'e'+exp_string).rjust(width)
        return literal

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{NumberVariable._get_default_description_string}.
        """
        return NumberVariable._get_default_description_string(self) % 'float'

    def _handle_literal_nonvalid_type(self, literal):
        """
        Extends L{NumberVariable._handle_literal_nonvalid_type}.
        """
        state = \
           super(FloatVariable, self)._handle_literal_nonvalid_type(literal)
        if state == INVALID and len(literal) > 0:
            if literal[-1] == '.' and literal.count('.') == 1 \
               or literal[-1] == 'e' and literal.count('e') == 1 \
               or (len(literal) > 1 and literal[-2:] in ('e-', 'e+')):
                state = PARTIAL
        return state

as_float = FloatVariable.as_type
as_float_or_na = FloatVariable.as_type_or_na


class BooleanVariable(_Variable):
    """
    Boolean variable

    Accepted values for a Boolean value are 0,1 (integers) and
    C{True},C{False} (Booleans). Accepted literals are
    "true","false","yes","no" (all case-insensitive) and "0","1".
    All valid input is converted to  C{False} or C{True}.

    @note: this is more restrictive than the standard Python interpretation
      of a Boolean (as implemented in the C{bool()} builtin).
    """

    __attributes__ = [Attribute('false_strings',
                                doc='list of allowed FALSE strings for this '
                                    'Boolean variable'),
                      Attribute('true_strings',
                                doc='list of allowed TRUE strings for this '
                                    'Boolean variable'),
                      ]


    # Default accepted literals for C{True} and C[False} values.
    __TRUE_STRINGS = ['Y','T','YES','TRUE','1']
    __FALSE_STRINGS = ['N','F','NO','FALSE','0']

    def __init__(self, default_value,
                 true_strings=None, false_strings=None, **options):
        """
        Extends L{Variable.__init__}.
        """
        self.true_strings = None
        self.false_strings = None
        if true_strings is None:
            true_strings = BooleanVariable.__TRUE_STRINGS
        if false_strings is None:
            false_strings = BooleanVariable.__FALSE_STRINGS
        self.set_true_strings(true_strings)
        self.set_false_strings(false_strings)
        super(BooleanVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False, # intentional signature change pylint: disable-msg=W0221
                true_strings=None, false_strings=None):
        """
        Overrides L{Variable.as_type}.
        """
        if true_strings is None:
            true_strings = BooleanVariable.__TRUE_STRINGS
        if false_strings is None:
            false_strings = BooleanVariable.__FALSE_STRINGS
        is_ok = True
        if isinstance(value, bool):
            if value in (False,True):
                result = value
            else:
                is_ok = False
        elif isinstance(value, (int, long, float)):
            if value in (0,1,True,False):
                result = (False,True)[value]
            else:
                is_ok = False
        elif isinstance(value, basestring):
            if value.upper() in true_strings:
                result = True
            elif value.upper() in false_strings:
                result = False
            else:
                is_ok = False
        else:
            is_ok = False
        if not is_ok:
            if allow_na and value is None:
                result = value
            else:
                raise ValueError('Unable to convert to Boolean: %s' % value)
        return result

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        return self.as_type(value, true_strings=self.true_strings,
                            false_strings=self.false_strings)

    def set_true_strings(self, true_strings):
        """
        Write accessor for the "C{true_strings}" attribute.

        @param true_strings: new allowed TRUE value strings
        @type true_strings: sequence of strings
        """
        self.true_strings = true_strings

    def get_true_strings(self):
        """
        Read accessor for the "C{true_strings}" attribute.

        @return: value of the "C{true_strings}" attribute
        """
        return self.true_strings

    def set_false_strings(self, false_strings):
        """
        Write accessor for the "C{false_strings}" attribute.

        @param false_strings: new allowed FALSE value strings
        @type false_strings: sequence of strings
        """
        self.false_strings = false_strings

    def get_false_strings(self):
        """
        Read accessor for the "C{false_strings}" attribute.

        @return: value of the "C{false_strings}" attribute
        """
        return self.false_strings

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'Boolean value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'Accepted literals are %s for "True" and ' \
               '%s for "False" (case-insensitive)' % \
               (', '.join(BooleanVariable.__TRUE_STRINGS),
                ', '.join(BooleanVariable.__FALSE_STRINGS))

    def _handle_literal_nonvalid_type(self, literal):
        """
        Implements L{Variable._handle_literal_nonvalid_type}.
        """
        if literal.upper() in \
                [lit[:len(literal)]
                 for lit in BooleanVariable.__TRUE_STRINGS +
                            BooleanVariable.__FALSE_STRINGS]:
            result = PARTIAL
        else:
            result = INVALID
        return result

as_bool = BooleanVariable.as_type
as_bool_or_na = BooleanVariable.as_type_or_na


class EnumVariable(_Variable):
    """
    Enumeration variable

    An enumeration variable holds one of a finite set of static values.
    """

    __attributes__ = [Attribute('values',
                                doc='list of allowed values for this '
                                    'enumeration variable'),
                      Attribute('value_infos',
                                doc='list of info strings for the allowed '
                                    'values of this enumeration variable, '
                                    'or None, if no value information is '
                                    'available'),
                      ]

    def __init__(self, default_value, values, value_infos=None,
                 **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param values: allowed values. See "C{values}" attribute
        @type values: list of L{object}s
        @param value_infos: value information strings. See "C{value_infos}"
          attribute
        @type value_infos: list of strings or C{None}
        """
        self.values = None
        self.value_infos = None
        self.set_values(values)
        self.set_value_infos(value_infos)
        super(EnumVariable,self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_values(self, values):
        """
        Write accessor for the "C{values}" attribute.

        @param values: new sequence of values
        @type values: list of L{object}s
        """
        self.values = values

    def get_values(self):
        """
        Read accessor for the "C{values}" attribute.

        @return: value of the "C{values}" attribute (list of L{object})
        """
        return self.values

    def set_value_infos(self, value_infos):
        """
        Write accessor for the "C{value_infos}" attribute.

        @param value_infos: new sequence of value informations
        @type value_infos: list
        """
        self.value_infos = value_infos

    def get_value_infos(self):
        """
        Read accessor for the "C{value_infos}" attribute.

        @return: value of the "C{value_infos}" attribute (list of strings)
        """
        return self.value_infos

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        if not value in self.values:
            raise ValueError('%s not an acceptable value. Allowed values: '
                             '%s' %  (value, self.values))
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'enumeration value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        if self.value_infos is None:
            val_string = 'allowed values are %s' % \
                         ', '.join([str(val) for val in self.values])
        else:
            val_string = 'allowed values: ' + \
                     ' or '.join(["%s: %s" % (str(val), val_string_info)
                                  for (val, val_string_info)
                                  in zip(self.values, self.value_infos)])
        return val_string


class SequenceVariable(_Variable):
    """
    Sequence variable
    """

    __attributes__ = [Attribute('element_variable',
                                doc='variable to use for validation of '
                                    'sequence elements, or None, if no '
                                    'validation is desired'),
                      Attribute('input_separator',
                                doc='separator string to use when parsing '
                                    'string input'),
                      Attribute('max_length',
                               doc='maximum length for this sequence '
                                   'variable'),
                      Attribute('min_length',
                                doc='minimum length for ths sequence '
                                    'variable'),
                      ]

    def __init__(self, default_value, element_variable=None,
                 min_length=None, max_length=None, input_separator=None,
                 **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param max_length: maximum sequence length; see "C{max_length}"
          attribute
        @type max_length: integer
        @param min_length: minimum sequence length; see "C{min_length}"
          attribute
        @type min_length: integer
        @param element_variable: variable to use for element validation.
          See "C{element_variable}" attribute
        @type element_variable: L{Variable} instance or C{None}
        @param input_separator: separator for parsing string input; see
          "C{input_separator}" attribute
        @type input_separator: string
        """
        self.element_variable = None
        self.input_separator = None
        self.max_length = None
        self.min_length = None
        self.set_element_variable(element_variable)
        self.set_max_length(max_length)
        self.set_min_length(min_length)
        self.set_input_separator(input_separator)
        super(SequenceVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_element_variable(self, element_variable):
        """
        Write accessor for the "C{element_variable}" attribute.

        @param element_variable: new element variable to use
        @type element_variable: L{Variable} instance or C{None}
        """
        self.element_variable = element_variable

    def get_element_variable(self):
        """
        Read accessor for the "C{element_variable}" attribute

        @return: value of the "C{element_variable}" attribute (L{Variable}
          instance or C{None})
        """
        return self.element_variable

    def set_max_length(self, max_length):
        """
        Write accessor for the "C{max_length}" attribute

        @param max_length: new maxinmum sequence length
        @type max_length: integer
        """
        self.max_length = max_length

    def get_max_length(self):
        """
        Read accessor for the "C{max_length}" attribute.

        @return: value of the "C{max_length}" attribute (integer)
        """
        return self.max_length

    def set_min_length(self, min_length):
        """
        Write accessor for the "C{min_length}" attribute

        @param min_length: new mininmum sequence length
        @type min_length: integer
        """
        self.min_length = min_length

    def get_min_length(self):
        """
        Read accessor for the "C{min_length}" attribute.

        @return: value of the "C{min_length}" attribute (integer)
        """
        return self.min_length

    def set_input_separator(self, input_separator):
        """
        Write accessor for the "C{input_separator}" attribute

        @param input_separator: new mininmum sequence length
        @type input_separator: integer
        """
        self.input_separator = input_separator

    def get_input_separator(self):
        """
        Read accessor for the "C{input_separator}" attribute.

        @return: value of the "C{input_separator}" attribute (integer)
        """
        return self.input_separator

    @staticmethod
    def as_type(value, allow_na=False, # intentional signature change pylint: disable-msg=W0221
                input_separator=None):
        """
        Overrides L{Variable.as_type}.
        """
        if isinstance(value, basestring):
            result = value.split(input_separator)
        else:
            try:
                result = list(value)
            except (ValueError, TypeError):
                if allow_na and value is None:
                    result = None
                else:
                    result = [value]
        return result

    def validate_type(self, values):
        """
        Overrides L{SequenceVariable.validate_type}.
        """
        values = self.as_type(values, allow_na=self.allow_na,
                                input_separator=self.input_separator)
        if not self.element_variable is None:
            # We have to perform another copy here because derived
            # classes might be immutable sequences (e.g., TupleVariable).
            validated_types = \
                [self.element_variable.validate_type(val) for val in values]
        else:
            validated_types = values
        return validated_types

    def validate_value(self, values):
        """
        Overrides L{SequenceVariable.validate_value}.
        """
        if not self.min_length is None and len(values) < self.min_length:
            raise ValueError('Sequence too short (must contain at least %d '
                             'elements)' % self.min_length)
        elif not self.max_length is None and len(values) > self.max_length:
            raise ValueError('Sequence too long (must contain at most %d '
                             'elements)' % self.max_length)
        else:
            if not self.element_variable is None:
                # check all items in the list, if they are typed:
                validated_values = \
                         [self.element_variable.validate_value(ele)
                          for ele in values]
            else:
                validated_values = values
            return validated_values

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'sequence value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        min_length = self.min_length
        max_length = self.max_length
        elem_variable_string = 'arbitrary elements' \
                             if self.element_variable is None \
                             else self.element_variable.get_description_info()
        if not min_length is None:
            if max_length == min_length:
                result = '%d %s' \
                            % (min_length, elem_variable_string)
            elif not max_length is None:
                result = '%d to %d %s' \
                            % (min_length, max_length, elem_variable_string)
            else:
                result = 'at least %d elements of %s' \
                            % (min_length, elem_variable_string)
        elif not max_length is None:
            result = 'at most %d elements of %s' \
                        % (max_length, elem_variable_string)
        else:
            result = 'any number of %s' % elem_variable_string
        return result

    def _handle_literal_nonvalid_type(self, literal):
        """
        Extends L{Variable._handle_literal_nonvalid_type}.
        """
        if literal[-len(self.input_separator):] == self.input_separator:
            result = PARTIAL
        else:
            result = INVALID
        return result


class ListVariable(SequenceVariable):
    """
    List variable
    """

    __attributes__ = []

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'list value'

as_list = ListVariable.as_type


class TupleVariable(SequenceVariable):
    """
    Tuple variable
    """

    __attributes__ = []

    #
    # public methods:
    #

    @staticmethod
    def as_type(value, allow_na=False, input_separator=None):
        """
        Extends L{SequenceVariable.as_type}.
        """
        return tuple(SequenceVariable.as_type(value,
                                             allow_na=allow_na,
                                             input_separator=input_separator))

    def validate_value(self, values):
        """
        Extends L{SequenceVariable.validate_value}.
        """
        values = SequenceVariable.validate_value(self, list(values))
        return tuple(values)

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'tuple value'

as_tuple = TupleVariable.as_type


class PairVariable(_Variable):
    """
    Specialized variable that holds 2-element sequences.

    Supports initialization from a string containing a colon.
    """

    __attributes__ = [Attribute('first_element_variable',
                                doc='variable to use for validation of the'
                                    'first element in this pair variable, '
                                    'or None, if no type checking is '
                                    'desired'),
                      Attribute('second_element_variable',
                                doc='variable to use for validation of the'
                                    'second element in this pair variable, '
                                    'or None, if no type checking is '
                                    'desired'),
                      ]

    def __init__(self, default_value, first_element_variable=None,
                 second_element_variable=None, **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param first_element_variable: variable to use for validation of the
          first element. See "C{first_element_variable}" attribute
        @type first_element_variable: L{Variable} instance or C{None}
        @param second_element_variable: variable to use for validation of the
          second element. See "C{second_element_variable}" attribute
        @type second_element_variable: L{Variable} instance or C{None}
        """
        self.first_element_variable = None
        self.second_element_variable = None
        self.set_first_element_variable(first_element_variable)
        self.set_second_element_variable(second_element_variable)
        super(PairVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_first_element_variable(self, element_variable):
        """
        Write accessor for the "C{first_element_variable}" attribute.

        @param element_variable: new element variable to use
        @type element_variable: L{Variable} instance or C{None}
        """
        self.first_element_variable = element_variable

    def get_first_element_variable(self):
        """
        Read accessor for the "C{first_element_variable}" attribute

        @return: value of the "C{first_element_variable}" attribute
          (L{Variable} instance or C{None})
        """
        return self.first_element_variable

    def set_second_element_variable(self, element_variable):
        """
        Write accessor for the "C{second_element_variable}" attribute.

        @param element_variable: new element variable to use
        @type element_variable: L{Variable} instance or C{None}
        """
        self.second_element_variable = element_variable

    def get_second_element_variable(self):
        """
        Read accessor for the "C{second_element_variable}" attribute

        @return: value of the "C{second_element_variable}" attribute
          (L{Variable} instance or C{None})
        """
        return self.second_element_variable

    @staticmethod
    def as_type(value, allow_na=False):
        """
        Overrides L{Variable.as_type}.
        """
        if allow_na and value is None:
            value = None
        else:
            if isinstance(value, basestring):
                value = list(value.split(':'))
            else:
                value = list(value)
            if len(value) != 2:
                raise ValueError('Pair variable values must be sequences '
                                 'containing two elements or a string '
                                 'containing a single colon')
        return value

    def validate_type(self, values):
        """
        Overrides L{Variable.validate_type}.
        """
        values = self.as_type(values, allow_na=self.allow_na)
        if not values is None:
            if not self.first_element_variable is None:
                values[0] = \
                      self.first_element_variable.validate_type(values[0])
            if not self.second_element_variable is None:
                values[1] = \
                     self.second_element_variable.validate_type(values[1])
        return values

    def validate_value(self, values):
        """
        Overrides L{Variable.validate_value}.
        """
        if not self.first_element_variable is None and not values[0] is None:
            values[0] = \
                    self.first_element_variable.validate_value(values[0])
        if not self.second_element_variable is None and not values[1] is None:
            values[1] = \
                   self.second_element_variable.validate_value(values[1])
        return values

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'pair value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return '%s as first and %s as second element' % \
               (self.first_element_variable.get_description_info(),
                self.second_element_variable.get_description_info())

as_pair = PairVariable.as_type


class MappingVariable(_Variable):
    """
    Mapping variable

    @note: relies on operator.isMappingType to determine the validity
      of a candidate value.
    """

    __attributes__ = [Attribute('key_type',
                                doc='type for the keys in all values of this '
                                     'mapping variable, or None, if no '
                                     'type checking is desired'),
                      Attribute('value_type',
                                doc='type for the values in all values of '
                                    'this mapping variable, or None, if no '
                                    'type checking is desired'),
                      ]

    def __init__(self, default_value, key_type=None, value_type=None,
                 **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param key_type: mapping key type. See the "C{key_type}" attribute
        @type key_type: L{type}
        @param value_type: mapping value type. See the "C{value_type}"
          attribute
        @type value_type: L{type}
        """
        self.key_type = None
        self.value_type = None
        self.set_key_type(key_type)
        self.set_value_type(value_type)
        super(MappingVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_key_type(self, key_type):
        """
        Write accessor for the "C{key_type}" attribute

        @param key_type: new key type
        @type key_type: integer
        """
        self.key_type = key_type

    def get_key_type(self):
        """
        Read accessor for the "C{key_type}" attribute.

        @return: value of the "C{key_type}" attribute (L{type})
        """
        return self.key_type

    def set_value_type(self, value_type):
        """
        Write accessor for the "C{value_type}" attribute

        @param value_type: value type
        @type value_type: integer
        """
        self.value_type = value_type

    def get_value_type(self):
        """
        Read accessor for the "C{value_type}" attribute.

        @return: value of the "C{value_type}" attribute (L{type})
        """
        return self.value_type

    def validate(self, value):
        """
        Overrides L{Variable.validate}.
        """
        if operator.isMappingType(value):
            is_ok = True
            for typ, test_objects in [(self.key_type, value.keys()),
                                        (self.value_type, value.values())]:
                if not typ is None:
                    is_ok = is_ok and all_of_type(typ, test_objects)
                if not is_ok:
                    break
        else:
            is_ok = False
        if not is_ok:
            raise ValueError('Unable to convert to a mapping (%s)' % value)
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'mapping value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        key = self.key_type is None and 'arbitrary type' or str(self.key_type)
        value_string = self.value_type is None and 'arbitrary type' \
                       or str(self.value_type)
        return 'mapping %s to %s' % (key, value_string)

DictionaryVariable = MappingVariable


class OptionsVariable(_Variable):
    """
    Special dictionary variable holding a fixed set of string key to typed
    value mappings.

    Supports initialization from a string, where option name:value pairs are
    separated by commas and the option name is separated from its value by
    an equal sign.
    """

    __attributes__ = [Attribute('option_definitions',
                                doc='option name to value variable mapping'),
                      ]

    def __init__(self, default_value, option_definitions, **options):
        """
        Extends L{Variable.__init__}. Additional arguments:

        @param option_definitions: contains the option names and option value
          variables for each of the held options
        @type option_definitions: dictionary mapping strings to L{Variable}
          instances
        """
        self.option_definitions = option_definitions
        super(OptionsVariable, self).__init__(default_value, **options)

    #
    # public:
    #

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        if self.allow_na and value is None:
            option_map = None
        else:
            if isinstance(value, dict):
                option_map = value
            elif isinstance(value, basestring):
                if value == '':
                    option_map = {}
                else:
                    # split pairs by comma, option names and values by colon:
                    pairs = [pair_str.split(':')
                             for pair_str in value.split(',')]
                    if any([pair for pair in pairs if len(pair) == 1]):
                        raise ValueError('Option name and option value in '
                                         'option strings must be separated '
                                         'by a colon')
                    # compose a dictionary with default values:
                    option_map = \
                      dict([(opt_name, opt_def.get_default_value())
                            for (opt_name, opt_def) in
                                            self.option_definitions.items()])
                    # update the defaults:
                    for (option, val_string) in pairs:
                        if not option in option_map:
                            raise ValueError('Invalid option name "%s" in '
                                             'option string encountered' %
                                             option)
                        opt_def = self.option_definitions[option]
                        option_map[option] = opt_def.validate_type(val_string)
            else:
                raise ValueError('Options variables must be a dictionary or '
                                 'a string containing option name:value '
                                 'pairs separated by commas')
        return option_map

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        if not value is None:
            for opt_name, opt_value in value.iteritems():
                value[opt_name] = \
                  self.option_definitions[opt_name].validate_value(opt_value)
        return value

    #
    # protected metehods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'options value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'options: ' \
               + '; '.join(['%s:%s' % (name, var.get_value_info())
                            for (name, var) in
                            self.option_definitions.items()])


class ArrayVariable(_Variable):
    """
    Array variable
    """

    __attributes__ = [Attribute('type_code',
                                doc='the NumPy type code for the values of '
                                    'this array variable'),
                      ]

    def __init__(self, default_value,
                 type_code=float32, **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param type_code: C{NumPy} type code. See "C{type_code}" attribute
        @type type_code: string
        """
        self.type_code = None
        self.set_type_code(type_code)
        super(ArrayVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_type_code(self, type_code):
        """
        Write accessor for the "C{type_code}" attribute.

        @param type_code: new typecode value
        @type type_code: string
        """
        self.type_code = type_code

    def get_type_code(self):
        """
        Read accessor for the "C{type_code}" attribute.

        @return: value of the "C{type_code}" attribute (string)
        """
        return self.type_code

    @staticmethod
    def as_type(value, allow_na=False, # intentional signature change pylint: disable-msg=W0221
                type_code=float32):
        """
        Overrides L{Variable.as_type}.
        """
        if value is None:
            if allow_na:
                result = None
            else:
                raise ValueError('Unable to convert to array value (%s)' %
                                 (value,))
        else:
            try:
                result = asarray(value, type_code)
            except ValueError:
                raise ValueError('Unable to convert to array value (%s)' %
                                 (value,))
        return result

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        return self.as_type(value,
                           allow_na=self.allow_na, type_code=self.type_code)

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'array value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'element type code %s' % self.type_code

# just for consistency:
as_array = ArrayVariable.as_type
as_array_or_na = ArrayVariable.as_type_or_na


class FunctionVariable(_Variable):
    """
    Function variable
    """

    __attributes__ = []

    #
    # public methods:
    #

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        if not (value is None or callable(value)):
            raise ValueError('Unable to convert to function value (%s)' %
                             value)
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'function value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'callable object'


class InstanceVariable(_Variable):
    """
    Instance variable

    Acceptable values are a class, instances of a class (or of derived
    classes), C{None}
    """

    __attributes__ = [Attribute('instance_class',
                                doc='class of the instance held by this '
                                    'instance variable'),
                      ]

    def __init__(self, default_value, instance_class, **options):
        """
        Extends L{Variable.__init__}. Additional keyword arguments:

        @param instance_class: held instance's class. See the L{instance_class}
          attribute
        @type instance_class: L{type}
        """
        self.instance_class = None
        self.set_instance_class(instance_class)
        super(InstanceVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_instance_class(self, instance_class):
        """
        Write accessor for the "C{instance_class}" attribute.

        @param instance_class: new instance class
        @type instance_class: class object
        """
        self.instance_class = instance_class

    def get_instance_class(self):
        """
        Read accessor for the "C{instance_class}" attribute.

        @return: value of the "C{instance_class}" attribute
        """
        return self.instance_class

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        if value is None:
            if not self.allow_na:
                raise ValueError('Unable to convert to an instance value '
                                 '(%s)' % (value,))
            result = None
        else:
            if isinstance(value, self.instance_class):
                result = value
            else:
                try:
                    result = self.instance_class(value)
                except:
                    raise ValueError('Unable to convert to an instance '
                                     'value (%s)' %
                                     (value,))
        return result

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'instance value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'instance of %s' % self.instance_class.__name__


class RectangleVariable(_Variable):
    """
    Rectangle variable

    Acceptable values for rectangle variables are either a 2-sequence of
    numbers ::

                          (<width>,<height>)

    with the position tacitly set to (0,0), or a 4-sequence of numbers ::

                   (<left pos. x>,<top pos. y>,<width>,<height>)

    Both width and height can be restricted to specific value ranges.

    @note: the numbers will be kept in whatever form they are passed in
      (floats or integers)
    """

    __attributes__ = [Attribute('max_height',
                                doc='maximum height of the rectangle held '
                                    'by this variable'),
                      Attribute('max_width',
                                doc='maximum width of the rectangle held '
                                    'by this variable'),
                      Attribute('min_height',
                                doc='minimum height of the rectangle held '
                                    'by this variable'),
                      Attribute('min_width',
                                doc='minimum width of the rectangle held '
                                    'by this variable'),
                      ]

    def __init__(self, default_value,
                 min_width=0, max_width=None, min_height=0, max_height=None,
                 **options):
        """
        Extends L{Variable.__init__}. Additional keyword parameters:

        @param max_height: maximum rectangle height. See "C{max_height}"
          attribute
        @type max_height: number (integer or float)
        @param max_width: maximum rectangle width. See "C{max_width}"
          attribute
        @type max_width: number (integer or float)
        @param min_height: minimum rectangle height. See "C{min_height}"
          attribute
        @type min_height: number (integer or float)
        @param min_width: minimum rectangle width. See "C{min_width}" attribute
        @type min_width: number (integer or float)
        """
        self.max_height = None
        self.min_height = None
        self.max_width = None
        self.min_width = None
        self.set_maximum_height(max_height)
        self.set_maximum_width(max_width)
        self.set_minimum_height(min_height)
        self.set_minimum_width(min_width)
        super(RectangleVariable, self).__init__(default_value, **options)

    #
    # public methods:
    #

    def set_maximum_height(self, max_height):
        """
        Write accessor for the "C{max_height}" attribute.

        @param max_height: new maximum height
        @type max_height: number (integer or float)
        """
        self.max_height = max_height

    def get_maximum_height(self):
        """
        Read accessor for the "C{max_height}" attribute.

        @return: value of the "C{max_height}" attribute
        """
        return self.max_height

    def set_maximum_width(self, max_width):
        """
        Write accessor for the "C{max_width}" attribute.

        @param max_width: new maximum width
        @type max_width: number (integer or float)
        """
        self.max_width = max_width

    def get_maximum_width(self):
        """
        Read accessor for the "C{max_width}" attribute.

        @return: value of the "C{max_width}" attribute
        """
        return self.max_width

    def set_minimum_height(self, min_height):
        """
        Write accessor for the "C{min_height}" attribute.

        @param min_height: new minimum height
        @type min_height: number (integer or float)
        """
        self.min_height = min_height

    def get_minimum_height(self):
        """
        Read accessor for the "C{min_height}" attribute.

        @return: value of the "C{min_height}" attribute
        """
        return self.min_height

    def set_minimum_width(self, min_width):
        """
        Write accessor for the "C{min_width}" attribute.

        @param min_width: new minimum width
        @type min_width: number (integer or float)
        """
        self.min_width = min_width

    def get_minimum_width(self):
        """
        Read accessor for the "C{min_width}" attribute.

        @return: value of the "C{min_width}" attribute
        """
        return self.min_width

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        try:
            new_width, new_height = value[2:]
        except:
            try: # legitimate catch-all pylint: disable-msg=W0702
                new_width, new_height = value
                value = (0, 0, new_width, new_height)
            except:
                raise ValueError('Unable to convert "%s" to a rectangle '
                                 'value' % (value,))
        return value

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        error_messages = []
        new_width, new_height = value[2:]
        if not self.max_width is None or not self.min_width is None:
            width_is_ok = (not self.min_width is None and
                          self.min_width <= new_width or True) and \
                          (not self.max_width is None and
                          new_width <= self.max_width or True)
            if not width_is_ok:
                error_messages.append('value for width (%s) out of range' %
                                      new_width)
        else:
            width_is_ok = True
        if not self.max_height is None:
            height_is_ok = (not self.min_height is None and
                           self.min_height <= new_height or True) and \
                           (not self.max_height is None and
                           new_height <= self.max_height or True)
            if not height_is_ok:
                error_messages.append('value for height (%s) out of range' %
                                      new_height)
        else:
            height_is_ok = True
        if not width_is_ok or not height_is_ok:
            range_string = 'width: %s < w < %s, height: %s < h < %s' % \
                           (self.min_width, self.max_width,
                            self.min_height, self.max_height)
            raise ValueError('%s out of range (%s)' %
                             (' and '.join(error_messages), range_string))
        return value

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'rectangle value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'width: %s < w < %s, height: %s < h < %s' \
                     % (self.min_width,
                        'inf' if self.max_width is None else self.max_width,
                        self.min_height,
                        'inf' if self.max_height is None else self.max_height)


class PositionVariable(_Variable):
    """
    Position in 2D- or 3D-space

    Acceptable values for position variables are 2- or 3-tuples of numbers.

    Each coordinate can be restricted to specific value ranges.
    """

    __attributes__ = [Attribute('max_x',
                                doc='maximum X coordinate'),
                      Attribute('max_y',
                                doc='maximum Y coordinate'),
                      Attribute('max_z',
                                doc='maximum Z coordinate'),
                      Attribute('min_x',
                                doc='minimum X coordinate'),
                      Attribute('min_y',
                                doc='minimum Y coordinate'),
                      Attribute('min_z',
                                doc='minimum Z coordinate'),
                       ]

    def __init__(self, default_value, min_x=None, max_x=None, min_y=None,
                 max_y=None, min_z=None, max_z=None, **options):
        """
        Extends Variable.__init__. Additional keyword parameters:

        @param max_x: maximum X coordinate. See "C{max_x}" attribute
        @type max_x: number (float or integer) or C{None}
        @param max_y: maximum Y coordinate. See "C{max_y}" attribute
        @type max_y: number (float or integer) or C{None}
        @param max_z: maximum Z coordinate. See "C{max_z}" attribute
        @type max_z: number (float or integer) or C{None}
        @param min_x: minimum X coordinate. See "C{min_x}" attribute
        @type min_x: number (float or integer) or C{None}
        @param min_y: minimum Y coordinate. See "C{min_y}" attribute
        @type min_y: number (float or integer) or C{None}
        @param min_z: minimum Z coordinate. See "C{min_z}" attribute
        @type min_z: number (float or integer) or C{None}
        """
        self.min_x = None
        self.max_x = None
        self.min_y = None
        self.max_y = None
        self.min_z = None
        self.max_z = None
        super(PositionVariable, self).__init__(default_value, **options)
        self.set_limits((min_x, max_x, min_y, max_y, min_z, max_z))

    #
    # public methods:
    #

    def set_minimum_x(self, min_x):
        """
        Write accessor for the "C{min_x}" attribute

        @param min_x: new minimum X coordinate
        @type min_x: number (float or integer) or C{None}
        """
        self.min_x = min_x

    def get_minimum_x(self):
        """
        Read accessor for the "C{min_x}" attribute

        @return: value of the "C{min_x}" attribute
        """
        return self.min_x

    def set_maximum_x(self, max_x):
        """
        Write accessor for the "C{max_x}" attribute

        @param max_x: new maximum X coordinate
        @type max_x: number (float or integer) or C{None}
        """
        self.max_x = max_x

    def get_maximum_x(self):
        """
        Read accessor for the "C{max_x}" attribute

        @return: value of the "C{max_x}" attribute
        """
        return self.max_x

    def set_minimum_y(self, min_y):
        """
        Write accessor for the "C{min_y}" attribute

        @param min_y: new minimum Y coordinate
        @type min_y: number (float or integer) or C{None}
        """
        self.min_y = min_y

    def get_minimum_y(self):
        """
        Read accessor for the "C{min_y}" attribute

        @return: value of the "C{min_y}" attribute
        """
        return self.min_y

    def set_maximum_y(self, max_y):
        """
        Write accessor for the "C{max_y}" attribute

        @param max_y: new maximum Y coordinate
        @type max_y: number (float or integer) or C{None}
        """
        self.max_y = max_y

    def get_maximum_y(self):
        """
        Read accessor for the "C{max_y}" attribute

        @return: value of the "C{max_y}" attribute
        """
        return self.max_y

    def set_minimum_z(self, min_z):
        """
        Write accessor for the "C{min_z}" attribute

        @param min_z: new minimum Z coordinate
        @type min_z: number (float or integer) or C{None}
        """
        self.min_z = min_z

    def get_minimum_z(self):
        """
        Read accessor for the "C{min_z}" attribute

        @return: value of the "C{min_z}" attribute
        """
        return self.min_z

    def set_maximum_z(self, max_z):
        """
        Write accessor for the "C{max_z}" attribute

        @param max_z: new maximum Z coordinate
        @type max_z: number (float or integer) or C{None}
        """
        self.max_z = max_z

    def get_maximum_z(self):
        """
        Read accessor for the "C{max_z}" attribute

        @return: value of the "C{max_z}" attribute
        """
        return self.max_z

    def get_limits(self):
        """
        Returns the values for all coordinate restriction attributes.

        @return: 6-tuple, elements are numbers (float or integer) or C{None}
        """
        return (self.min_x, self.max_x, self.min_y,
                self.max_y, self.min_z, self.max_z)

    def set_limits(self, (min_x, max_x, min_y, max_y, min_z, max_z)):
        """
        Sets the values for all coordinate restriction attributes.

        See L{__init__} for parameter descriptions.
        """
        self.set_minimum_x(min_x)
        self.set_maximum_x(max_x)
        self.set_minimum_y(min_y)
        self.set_maximum_y(max_y)
        self.set_minimum_z(min_z)
        self.set_maximum_z(max_z)

    #
    # overwritten methods:
    #

    def validate_type(self, value):
        """
        Overrides L{Variable.validate_type}.
        """
        try:
            x_coord, y_coord, z_coord = value
        except:
            try: # legitimate catch-all pylint: disable-msg=W0702
                x_coord, y_coord = value
                z_coord = None
            except:
                raise ValueError('Unable to convert %s to a position value' %
                                 (value,))
        return x_coord, y_coord, z_coord

    def validate_value(self, value):
        """
        Overrides L{Variable.validate_value}.
        """
        x_coord, y_coord, z_coord = value
        if not self.min_x is None:
            min_x_is_ok = x_coord >= self.min_x
        else:
            min_x_is_ok = True
        if not self.max_x is None:
            max_x_is_ok = x_coord <= self.max_x
        else:
            max_x_is_ok = True
        if not self.min_y is None:
            min_y_is_ok = y_coord >= self.min_y
        else:
            min_y_is_ok = True
        if not self.max_y is None:
            max_y_is_ok = y_coord <= self.max_y
        else:
            max_y_is_ok = True
        if not z_coord is None: # We may not have a Z coordinate.
            if not self.min_z is None:
                min_z_is_ok = z_coord >= self.min_z
            else:
                min_z_is_ok = True
            if not self.max_z is None:
                max_z_is_ok = z_coord <= self.max_z
            else:
                max_z_is_ok = True
        else:
            min_z_is_ok = max_z_is_ok = True
        error_messages = []
        if not min_x_is_ok or not max_x_is_ok:
            error_messages.append('x coordinate (%s) out of bounds (%s,%s)'
                                    % (x_coord, self.min_x, self.max_x))
        if not min_y_is_ok or not max_y_is_ok:
            error_messages.append('y coordinate (%s) out of bounds (%s,%s)'
                                    % (y_coord, self.min_y, self.max_y))
        if not min_z_is_ok or not max_z_is_ok:
            error_messages.append('z coordinate (%s) out of bounds (%s,%s)'
                                    % (z_coord, self.min_z, self.max_z))
        if error_messages:
            raise ValueError('Invalid position value (%s)' %
                             ';'.join(error_messages))
        return asarray(value)

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'position value'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return 'positon. x: %s < x < %s; %s < y < %s; %s < z < %s' % \
               ('-inf' if self.min_x is None else self.min_x,
                'inf' if self.max_x is None else self.max_x,
                '-inf' if self.min_y is None else self.min_y,
                'inf' if self.max_y is None else self.max_y,
                '-inf' if self.min_z is None else self.min_z,
                'inf' if self.max_z is None else self.max_z)


class VariableGroup(_Variable):
    """
    OR operations on variables

    Use this to express that a value may be of more than one type.

    Usage: ::

        >>> from pdk.variables import IntVariable,VariableGroup
        >>> v1 = IntVariable(0, min_value=0, max_value=15, \
                             info='an integer in [0..15]')
        >>> v2 = IntVariable(16, min_value=16, max_value=32, \
                             info='an integer in [16..32]')
        >>> group = v1 | v2
        >>> group.validate(1)
        1
        >>> group.validate('32') # auto-convert '32' to integer value
        32
        >>> try:
        ...     group.validate(33) # invalid for both variables
        ... except ValueError:
        ...     pass
        >>>

    """

    def __init__(self, *variables):
        """
        Extends L{Variable.__init__}.
        """
        super(VariableGroup, self).__init__(None)
        variables = []
        for variable in variables:
            if issubclass(variable.__class__, VariableGroup):
                variables.extend(variable.getVariableInstances())
            elif issubclass(variable.__class__, _Variable):
                variables.append(variable)
            else:
                raise ValueError('Invalid input for VariableGroup '
                                 '(type of offending variable: %s)' %
                                 type(variable))
        self.__variables = tuple(variables)

    #
    # public methods:
    #

    def validate(self, value):
        """
        Overrides L{Variable.validate}.
        """
        error_strings = []
        is_valid = False
        for variable in self.__variables:
            try:
                value = variable.validate(value)
            except ValueError, error:
                error_strings.append(str(error))
            else:
                is_valid = True
                break
        if not is_valid:
            raise ValueError(' AND '.join(error_strings))
        return value

    def get_variables(self):
        """
        Returns the variables in this group.

        @return: tuple of L{Variable} instances
        """
        return self.__variables

    #
    # protected methods:
    #

    def _get_default_description_string(self):
        """
        Extends L{Variable._get_default_description_string}.
        """
        return 'group variable'

    def _get_default_value_string(self):
        """
        Extends L{Variable._get_default_value_string}.
        """
        return ' OR '.join([variable.get_value_info()
                            for variable in self.__variables])
