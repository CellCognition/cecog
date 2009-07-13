"""
Phenes are inherited attributes visible to the outside.

FOG 05.2008
"""

__docformat__ = "epytext"
__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['Any',
           'Boolean',
           'DateTime',
           'Dict',
           'Enum',
           'Float',
           'Instance',
           'Int',
           'IsMandatoryPheneValueError',
           'IsNotNonePheneValueError',
           'IsWriteOncePheneValueError',
           'List',
           'Phene',
           'PhenoType',
           'String',
           'Tuple',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import types
from copy import deepcopy

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.declarationcollectors import get_declarations
from pdk.pyutils import (get_bases,
                         get_traceback)
from pdk.variables import (BooleanVariable,
                           DateTimeVariable,
                           DictionaryVariable,
                           EnumVariable,
                           FloatVariable,
                           InstanceVariable,
                           IntVariable,
                           ListVariable,
                           StringVariable,
                           TupleVariable,
                           Variable,
                           )
from pdk.ordereddict import OrderedDict

#------------------------------------------------------------------------------
# constants:
#
class _NotSet: # pylint: disable-msg=W0232
    pass
_NOT_SET = _NotSet()

#------------------------------------------------------------------------------
# helper functions:
#

def get_pheno_type_phenes(cls):
    """
    Returns a map containing all phenes of the given (L{PhenoType}) class.

    @param cls: class to query
    @type cls: L{PhenoType}
    @return: phene name (L{str}) to L{Phene} instance map
    @rtype: L{dict}
    """
    phene_map = OrderedDict()
    for base in get_bases(cls) + [cls]:
        for name, value in base.__dict__.iteritems():
            if isinstance(value, Phene):
                phene_map[name] = value
    phene_map.sort(key = lambda name: phene_map[name].rank, reverse=True)
    return phene_map


def has_pheno_type_phene(cls, name):
    """
    Checks if the given class has a L{Phene} of the given name.

    @param cls: class to check
    @type cls: L{PhenoType}
    @param name: name to check
    @type name: L{str}
    @return: check result
    @rtype: L{bool}
    """
    return name in cls.__dict__ and isinstance(cls.__dict__[name], Phene)


def get_pheno_type_phene(cls, name):
    """
    Returns the phene of the given name for the given class (typically,
    a L{PhenoType} subclass).

    @param cls: class to query
    @type cls: L{PhenoType}
    @raise KeyError: if L{cls} does not have a phene of the given L{name}
    @return: requested phene
    @rtype: L{Phene}
    """
    return cls.__dict__[name]


def get_pheno_type_phene_names(cls):
    """
    Returns all phene names for the given (L{PhenoType}) class.

    @param cls: class to query
    @type cls: L{PhenoType}
    @return: sequence of phene names (L{str})
    @rtype: L{list}
    """
    return get_pheno_type_phenes(cls).keys()

#------------------------------------------------------------------------------
# classes:
#

class IsMandatoryPheneValueError(ValueError):
    pass


class IsNotNonePheneValueError(ValueError):
    pass


class IsWriteOncePheneValueError(ValueError):
    pass


class Phene(property):
    """
    A phene is an inherited, externally visible attribute.

    Phenes
     * have a value type which makes it possible to constrain the set
       of possible values you can assign to the phene;
     * are always associated with a L{PhenoType}, where they are declared
       statically (in the class namespace);
     * can control their initialization and other behavior in various ways
       through a number of constructor options (see L{__init__}).

    @cvar _VARIABLE_CLASS: this is needed in derived classes to specify
      the associated variable class which will do the value validation
    @cvar __bIsImmutable: provides a static default value for the flag
      indicating if a L{Phene} instance has been made immutable
    """

    _VARIABLE_CLASS = None
    is_immutable = False

    def __init__(self,
                 default_value=None, doc=None, tooltip=None, label=None,
                 rank=-1,
                 get_callback=None, set_callback=None, del_callback=None,
                 is_auto_initialized=True, is_mandatory=False,
                 is_not_none=False, is_persistent=False, is_write_once=False,
                 **variable_options):
        """
        Constructor.

        @param default_value: default value to use for this phene
        @type default_value: arbitrary object
        @param doc: doc string for this phene
        @type doc: L{str}
        @param get_callback: callable to call to get the phene's value. Not
          implemented yet.
        @type get_callback: callable or L{str}
        @param set_callback: callable to call to set the phene's value. Not
          implemented yet.
        @type set_callback: callable or L{str}
        @param del_callback: callable to call to delete the phene's value. Not
          implemented yet.
        @type del_callback: callable or L{str}
        @param is_auto_initialized: flag indicating if this phene should be
          initialized automatically.
        @type is_auto_initialized: L{bool}
        @param is_mandatory: flag indicating if a value is I{required} for
          this phene during instantiation.
        @type is_mandatory: L{bool}
        @param is_not_none: flag indicating if the value of this phene may
          not be set to a C{None} value.
        @type is_not_none: L{bool}
        @param is_persistent: flag indicating if this phene should be included
          when its associated object is pickled.
        @type is_persistent: L{bool}
        @param is_write_once: flag indicating if the value of this phene may
          only be set I{once}.
        @type is_write_once: L{bool}
        @param variable_options: options passed to the variable instance
          associated with this phene which controls the set of valid values.
        @type variable_options: variable-length L{dict}
        """
        property.__init__(self)
        self.__variable = \
                self.__class__._VARIABLE_CLASS(default_value, # pylint: disable-msg=E1102
                                               allow_na=not is_not_none,
                                               **variable_options)
        self.doc = doc
        self.rank = rank
        self.tooltip = tooltip
        self.label = label
        self.get_callback = get_callback
        self.set_callback = set_callback
        self.del_callback = del_callback
        self.is_auto_initialized = is_auto_initialized
        self.is_mandatory = is_mandatory
        self.is_not_none = is_not_none
        self.is_persistent = is_persistent
        self.is_write_once = is_write_once
        #
        self.__value = _NOT_SET
        self.__variable_option_names = \
          set([decl.name
               for decl in get_declarations(self.__class__._VARIABLE_CLASS,
                                            '__attributes__')])

    #
    # magic methods:
    #

    def __get__(self, instance, dummy):
        if not instance is None: # instance access.
            if not self.get_callback is None:
                value = self.__variable.validate(
                            self.__call_callback(self.get_callback, instance))
            else:
                value = self.__value
        else:
            value = self
        return value

    def __set__(self, instance, value):
        valid_value = self.__variable.validate(value)
        if not self.set_callback is None:
            self.__call_callback(self.set_callback, instance, valid_value)
        if self.get_callback is None:
            self.__value = valid_value

    def __delete__(self, instance):
        if not self.del_callback is None:
            self.__call_callback(self.del_callback, instance)
        self.__value = _NOT_SET

    def __getattr__(self, attr):
        if attr in self.__variable_option_names:
            return getattr(self.__variable, attr)
        raise AttributeError(attr)

    def __setattr__(self, attr, value):
        # Check for write protection.
        if self.is_immutable:
            raise AttributeError('can not set "%s" attribute on '
                                 'write-protected Phene object!' % attr)
        else:
            super(Phene, self).__setattr__(attr, value)

    #
    # public methods:
    #

    def make_immutable(self):
        """
        Write-protects this phene.
        """
        # Enable write protection.
        self.is_immutable = True

    #
    # private methods:
    #

    def __call_callback(self, callback, instance, *args):
        # Execute a callback. `callback` should be either a callable
        # (functions are called with ``self`` as first argument) or a
        # string giving the name of a method of L{instance}.
        if callable(callback):
            if isinstance(callback, types.FunctionType):
                result = callback(instance, *args)
            else:
                result = callback(*args)
        else:
            try:
                result = getattr(instance, callback)(*args)
            except:
                raise ValueError('calling the callback '
                                 '"%s" with args "%s" failed. '
                                 '\nTraceback of the error causing the '
                                 'failure:\n %s' %
                                 (callback, args, get_traceback()))
        return result


class PhenoType(object):
    """
    A phenotype has a collection of L{Phenes} which determine its external
    appearance.

    Phenes are declared statically in the class namespace.

    Setting public attributes other than the ones declared through phenes
    is not permitted; however, protected and private attributes are fine.
    """

    def __new__(cls, *args, **options):
        instance = super(PhenoType, cls).__new__(cls, *args, **options)
        for name, phene in get_pheno_type_phenes(cls).iteritems():
#            copied_phene = deepcopy(phene)
#            instance.__dict__[name] = copied_phene
            setattr(cls, name, phene) #  copied_phene)
        return instance

    def __init__(self, **options):
        for name in get_pheno_type_phene_names(self.__class__):
            phene = getattr(self.__class__, name)
            if phene.is_auto_initialized:
                phene_value = options.pop(name, _NOT_SET)
                if phene_value is _NOT_SET and not phene.is_mandatory:
                    # use the default, unless a value is required:
                    phene_value = phene.default_value
            else:
                phene_value = _NOT_SET
            if phene_value is _NOT_SET and phene.is_mandatory:
                raise IsMandatoryPheneValueError(
                                'need to provide a value for the "%s" phene'
                                % name)
            else:
                if phene_value is None and phene.is_not_none:
                    raise IsNotNonePheneValueError(
                                'need to provide a not-None value for the '
                                '"%s" phene' % name)
                setattr(self, name, phene_value)
        if not len(options) == 0:
            raise TypeError('unexpected keyword arguments: %s' %
                            options.keys())

    #
    # magic methods:
    #

    def __getstate__(self):
        state_map = {}
        for name in get_pheno_type_phene_names(self.__class__):
            phene = getattr(self.__class__, name)
            if phene.is_persistent:
                state_map[name] = getattr(self, name)
        return state_map

    def __setstate__(self, state_map):
        phene_names = get_pheno_type_phene_names(self.__class__)
        for name, value in state_map.iteritems():
            if not name in phene_names:
                raise ValueError('invalid state data for non-existing '
                                 'phene "%s"' % name)
            if not getattr(self.__class__, name).is_persistent:
                raise ValueError('invalid state data for non-persistent '
                                 'phene "%s"' % name)
            setattr(self, name, value)

    def __reduce__(self):
        return (self.__class__, (), self.__getstate__())

    def __setattr__(self, name, value):
        if has_pheno_type_phene(self.__class__, name):
            phene = get_pheno_type_phene(self.__class__, name)
            if phene.is_write_once:
                if hasattr(self, name):
                    raise IsWriteOncePheneValueError(
                           'the "%s" attribute can only be set once!'
                            % name)
                else:
                    phene.is_immutable = True
            super(PhenoType, self).__setattr__(name, value)
        elif name.startswith('_'):
            super(PhenoType, self).__setattr__(name, value)
        else:
            raise AttributeError('can not set public attributes in '
                                 'PhenoType instances')

    def __getattribute__(self, name):
        value = super(PhenoType, self).__getattribute__(name)
        if value is _NOT_SET:
            raise AttributeError('"%s" phene not set in %s instance'
                                 %(name, self.__class__.__name__))
        return value

    #
    # public methods:
    #

    def get_phene_names(self):
        return get_pheno_type_phene_names(self.__class__)

    def get_phenes(self):
        return get_pheno_type_phenes(self.__class__)

    def get_phene_by_name(self, name):
        return get_pheno_type_phene(self.__class__, name)


class Any(Phene):
    _VARIABLE_CLASS = Variable


class String(Phene):
    _VARIABLE_CLASS = StringVariable


class Int(Phene):
    _VARIABLE_CLASS = IntVariable


class Float(Phene):
    _VARIABLE_CLASS = FloatVariable


class Boolean(Phene):
    _VARIABLE_CLASS = BooleanVariable


class Tuple(Phene):
    _VARIABLE_CLASS = TupleVariable


class List(Phene):
    _VARIABLE_CLASS = ListVariable


class Dict(Phene):
    _VARIABLE_CLASS = DictionaryVariable


class DateTime(Phene):
    _VARIABLE_CLASS = DateTimeVariable


class Enum(Phene):
    _VARIABLE_CLASS = EnumVariable


class Instance(Phene):
    _VARIABLE_CLASS = InstanceVariable
