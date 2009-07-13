"""
Code for managing instance attributes.

Managed attributes are declared either as pdk-specific C{__attributes} or
as C{__slots__}.

Example: managing attributes as C{__attributes__}

    >>> from pdk.attributes import Attribute
    >>> from pdk.attributemanagers import AttributeManager
    >>> class X(AttributeManager):
    ...     __attributes__ = [Attribute("w"),
    ...                       Attribute("x",default_value=-1), # default value
    ...                       Attribute("y",is_write_once=True),# set only once
    ...                       "_X__p"                         # not managed
    ...                       ]
    ...     def __init__(self, **options):
    ...         self.__p = -1
    >>> class Y(X):
    ...     __attributes__ = [Attribute("w",is_not_none=True),   # override!
    ...                       Attribute("z",is_mandatory=True), # must be set
    ...                       "v",                             # simple
    ...                       ]
    >>> myY = Y(x=1, y=2, z=3)
    >>> myY.x
    1
    >>> myY.y
    2
    >>> try:
    ...     myY.y = 3
    ... except AttributeError:
    ...     pass
    >>> try:
    ...     myY.v
    ... except AttributeError:
    ...     pass

FOG 03.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['AttributeController',
           'AttributeDeclarationCollector',
           'AttributeController',
           'AttributeInitializer',
           'AttributeManager',
           'MetaAttributeDeclarationCollector',
           'SlotController',
           'SlotController',
           'SlotDeclarationCollector',
           'SlotInitializer',
           'SlotManager',
           'get_attributes',
           'get_attribute_values',
           'get_public_attributes',
           'get_public_attribute_values',
           'get_public_slots',
           'get_public_slot_values',
           'get_slots',
           'get_slot_values',
           'set_attribute_values',
           'set_slot_values',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
from copy import (copy,
                  deepcopy)

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.attributes import (Attribute,
                            Slot)
from pdk.declarationcollectors import (DeclarationCollector,
                                       MetaDeclarationCollector,
                                       get_declarations,
                                       is_public)

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class MetaAttributeDeclarationCollector(MetaDeclarationCollector):
    """
    Meta class for attribute collectors

    Collects attribute declarations, which are instances of the class
    specified by the (virtual) L{get_attribute_declaration_class} method and
    held by the container specified by the (virtual)
    L{getAttributeDeclarationContainer} method.

    @note: only properly declared, "non-magic" (i.e., names not starting
      and ending with two underscores) attributes are managed
    """

    #
    # public methods:
    #

    def get_managed_attributes(mcs):
        """
        Returns the container holding the managed attributes for this class.

        Calls
        L{pdk.declarationcollectors.MetaDeclarationCollector.get_declarations}.

        @return: list of attribute instances
        """
        return mcs.get_declarations()

    def get_managed_attribute_names(mcs):
        """
        Returns the names of the managed attribute names for this class.

        @return: list of attribute name strings
        """
        return [attr.name for attr in mcs.get_managed_attributes()]


class _AttributeDeclarationCollector(DeclarationCollector):

    __attributes__ = []

    @classmethod
    def get_declaration_class(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_class}.

        Calls L{get_attribute_declaration_class}.
        """
        return cls.get_attribute_declaration_class()

    @classmethod
    def get_declaration_container_name(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_container_name}.

        Calls L{get_attribute_declaration_container_name}.
        """
        return cls.get_attribute_declaration_container_name()

    @classmethod
    def get_attribute_declaration_class(cls):
        """
        Returns the class object to use for attribute declarations gathered
        by this collector.

        @return: attribute declarator class (class object)
        """
        # can't use NotImplementedMethodError here because this class method
        # is called during instantiation of the class by the meta class, at
        # which time the class itself is not yet available.
        raise NotImplementedError('classes deriving from '
                                  '_AttributeDeclarationCollector need to '
                                  'implement a get_attribute_declaration_class'
                                  'method!')

    @classmethod
    def get_attribute_declaration_container_name(cls):
        """
        Returns the name of the class attribute referring to the conainer
        that will hold the attribute declarations to gather by this
        collector.

        @return: attribute declaration container attribute name (string)
        """
        # can't use NotImplementedMethodError here because this class method
        # is called during instantiation of the class by the meta class, at
        # which time the class itself is not yet available.
        raise NotImplementedError('classes deriving from '
                                  '_AttributeDeclarationCollector need to '
                                  'implement a '
                                  'get_attribute_declaration_container_name '
                                  'method!')


class AttributeDeclarationCollector(_AttributeDeclarationCollector):
    """
    Concrete declaration collector class for declarations held in
    C{__attributes__} containers
    """

    __metaclass__ = MetaAttributeDeclarationCollector

    __attributes__ = []

    @classmethod
    def get_attribute_declaration_class(cls):
        """
        Implements L{_AttributeDeclarationCollector.getAttributeClass}.
        """
        return Attribute

    @classmethod
    def get_attribute_declaration_container_name(cls):
        """
        Implements L{_AttributeDeclarationCollector.getAttributeClass}.
        """
        return '__attributes__'


class SlotDeclarationCollector(_AttributeDeclarationCollector):
    """
    Concrete declaration collector class for declarations held
    in C{__slots__} containers
    """

    __metaclass__ = MetaAttributeDeclarationCollector

    __slots__ = []

    @classmethod
    def get_attribute_declaration_class(cls):
        """
        Implements
        L{_AttributeDeclarationCollector.get_attribute_declaration_class}.
        """
        return Slot

    @classmethod
    def get_attribute_declaration_container_name(cls):
        """
        Implements
        L{_AttributeDeclarationCollector.get_attribute_declaration_container_name}.
        """
        return '__slots__'


class _AttributeControllerMixin(object):
    """
    Mixin class for instance attribute access control

    Works in cooperation with the L{DeclarationCollector} and protects the
    instance from creating undeclared attributes. Also, provides default
    handlers for copying, deepcopying, and pickling/unpickling that restore
    all managed attributes.

    Public managed attributes (i.e., attributes that do not start with an
    underscore) can be declared to (cf. the L{_Attribute} class)
      - be mandatory (i.e., a value has to be passed at instantiation; use
        this to emulate positional arguments)
      - be write-once (i.e., the attribute value is only allowed to be set
        once to a not-C{None} value)
      - be not-None (i.e., the attribute can only be set to a not-None value)
      - have a default value (use this to emulate the defaults you would
        normally assign to keyword variables in a custom constructor)
    """

    __slots__ = []

    #
    # magic methods:
    #

    def __setattr__(self, attribute_name, attribute_value):
        """
        Called when an attribute is set on this attribute controller.

        Implements the various restrictions on declared attributes.
        """
        # FIXME: lift restriction to public attributes
        if is_public(attribute_name):
            try:
                attributes = self.__class__.get_managed_attributes()
            except AttributeError:
                # .__new__() has not been called yet - revert to the
                # base class __setattr__:
                pass
            else:
                try:
                    attribute = \
                             attributes[attributes.index(attribute_name)]
                except ValueError:
                    raise AttributeError("'%s' object has no attribute '%s'"
                                         % (self.__class__.__name__,
                                            attribute_name))
                else:
                    if attribute.is_not_none and attribute_value is None:
                        raise AttributeError('trying to set the not-None '
                                             'attribute "%s" in instance '
                                             '"%s" to None.' %
                                             (attribute_name, self))
                    if attribute.is_write_once \
                           and hasattr(self, attribute_name) \
                           and not getattr(self, attribute_name) is None:
                        # note: setting a None-valued write-once attribute to
                        # a not-None value is permitted!
                        raise AttributeError('trying to set an initialized '
                                             'write-once attribute "%s" in '
                                             'instance "%s" to a not-None '
                                             'value.' % (attribute_name,
                                                         self))
        super(_AttributeControllerMixin, self).__setattr__(attribute_name,
                                                      attribute_value)

    def __setstate__(self, state):
        """
        Called to restore the state of this attribute controller during
        unpickling from the given state dictionary.

        @param state: maps managed attribute names to their values
        @type state: dictionary
        """
        for attr_name, attr_value in state['attributes'].iteritems():
            setattr(self, attr_name, attr_value)
        del state['attributes']
        # this is for "cooperative unpickling":
        try:
            super(_AttributeControllerMixin, self).__setstate__(state)
        except AttributeError:
            pass

    def __copy__(self):
        """
        Called to obtain a copy of this instance.

        Restricts the copy protocol to include only managed attributes.
        """
        return self._copy(copy)

    def __deepcopy__(self, memo):
        """
        Called to obtain a deep copy of this instance.

        Restricts the deep copy protocol to include only managed attributes.
        """
        return self._copy(deepcopy, memo=memo)

    #
    # public methods:
    #

    def set_attribute(self, attribute_name, attribute_value):
        """
        Alias for L{__setattr__}.
        """
        self.__setattr__(attribute_name, attribute_value)

    def set_attributes(self, **attributes):
        """
        Calls L{__setattr__} for each attribute name/value pairs
        in the given dictionary.

        @param attributes: attribute name/value pairs
        @type attributes: variable-length dictionary mapping attribute names
          (strings) to their values (arbitrary objects)
        """
        for attr_name, attr_value in attributes.iteritems():
            self.__setattr__(attr_name, attr_value)

    #
    # protected methods:
    #

    def _copy(self, copy_function, **options):
        """
        Implements copying of this instance.

        @param copy_function: function to use for copying the state dictionary
          (either C{copy} or C{deepcopy})
        @type copy_function: function
        """
        attr_value_map = self.__getstate__()
        instance = self.__new__(self.__class__)
        instance.__setstate__(copy_function(attr_value_map, **options))
        return instance


class AttributeController(AttributeDeclarationCollector,
                          _AttributeControllerMixin):
    """
    Mixin class for controlling instance attributes declared as
    C{__attributes__}
    """

    __attributes__ = []

    def __getstate__(self):
        """
        Called to obtain the state of this attribute controller.

        Extracts all managed attributes from this instance and stores them
        under the key 'C{attributes}' in a state dictionary.

        @return: state dictionary of managed attribute names and values
        """
        # this is for "cooperative pickling":
        try:
            state_map = super(AttributeController, self).__getstate__()
        except AttributeError:
            state_map = {}
        state_map['attributes'] = get_attribute_values(self)
        return state_map


class SlotController(SlotDeclarationCollector, _AttributeControllerMixin):
    """
    Mixin class for controlling instance attributes declared as
    C{__slots__}
    """

    __slots__ = []

    def __getstate__(self):
        """
        Called to obtain the state of this attribute controller.

        Extracts all managed slots from this instance and stores them under
        the key 'C{attributes}' in a dictionary.

        @return: dictionary of managed slot names and values
        """
        # this is for "cooperative pickling":
        try:
            state_map = super(SlotController, self).__getstate__()
        except AttributeError:
            state_map = {}
        state_map['attributes'] = get_slot_values(self)
        return state_map


class _AttributeInitializerMixin(object):
    """
    Base class for mixins for automatic initialization of managed attributes

    Works in collaboration with the L{DeclarationCollector} and automatically
    initializes all attributes for which a keyword of the same name is passed
    to the constructor. This can also be used together with the
    L{_AttributeControllerMixin} (see the L{AttributeManager} and
    L{SlotManager} classes).

    @note: only keyword arguments will be processed automatically during
      instantiation - positional arguments will *not* be touched
    @note: L{_AttributeInitializerMixin} (and classes derived thereof) should
      always be at the base of an inheritance tree, or else not all
      attribute declarations will be handled correctly
    """

    def __new__(cls, *args, **options):
        """
        Extends C{object.__new__}. Creates a new instance and sets all
        managed attributes in its namespace.

        @note: no error is raised when L{options} contains variable names that
          are not declared as attributes.
        """
        # iterate over the attributes:
        managed_attrs = cls.get_managed_attributes()
        attr_map = {}
        for managed_attr in managed_attrs:
            managed_attr_name = managed_attr.name
            # check if the attribute was passed as a keyword argument:
            try:
                attr_value = options[managed_attr_name]
            except KeyError:
                # check if a default value was declared for this attribute:
                try:
                    attr_value = managed_attr.default_value
                except AttributeError:
                    # ... no value was given for this attribute
                    if managed_attr.is_mandatory:
                        raise ValueError('need initialization value for '
                                         'mandatory attribute "%s"' %
                                         managed_attr.name)
                    continue
            attr_map[managed_attr_name] = attr_value
        # create the instance:
        instance = \
             super(_AttributeInitializerMixin, cls).__new__(cls,
                                                            *args, **options)
        # set the attribute attributes:
        for managed_attr_name, attr_value in attr_map.iteritems():
            setattr(instance, managed_attr_name, attr_value)
        return instance

    def __init__(self, **options):
        """
        Default constructor.
        """
        super(_AttributeInitializerMixin, self).__init__(**options)

    #
    # protected methods:
    #

    def _copy(self, copy_function, **options):
        """
        Overrides L{_AttributeControllerMixin._copy}.
        """
        attr_value_map = self.__getstate__()['attributes']
        return self.__new__(self.__class__,
                            **copy_function(attr_value_map, **options))


class AttributeInitializer(_AttributeInitializerMixin):
    """
    Mixins for automatic initialization of managed instance attributes
    """

    __attributes__ = []


class SlotInitializer(_AttributeInitializerMixin):
    """
    Mixin for automatic initialization of managed instance slots
    """

    __slots__ = []


class AttributeManager(AttributeInitializer, AttributeController):
    """
    Attribute manager, combining the services of L{AttributeInitializer}
    and L{AttributeController}
    """

    __attributes__ = []


class SlotManager(SlotInitializer, SlotController):
    """
    Slot manager, combining the services of L{SlotInitializer} and
    L{SlotController}
    """

    __slots__ = []

#------------------------------------------------------------------------------
# functions:
#

def _get_attribute_names(cls, container_name, declaration_class):
    """
    Returns the declared attribute names for the given class and
    declaration container name.

    @param cls: class do get the declarations for
    @type cls: type
    @param containerName: declaration container name
    @type containerName: string
    @return: list of attribute names
    @param declaratorClass: class of the attribute declarator
    @type declaratorClass: class object
    """
    if issubclass(cls, AttributeDeclarationCollector) and \
           container_name == cls.get_attribute_declaration_container_name():
        attr_names = cls.get_managed_attribute_names()
    else:
        # FIXME: drop support for plain strings as attribute declarations
        attr_names = \
           [isinstance(attr_or_name, declaration_class) and attr_or_name.name
            or attr_or_name
            for attr_or_name in get_declarations(cls, container_name)]
    return attr_names


def _get_attribute_values(instance, attribute_names):
    """
    Returns the declared attribute values for the given object instance and
    attribute names.

    @param instance: object to get the attribute values from
    @type instance: object instance
    @param attribute_names: attribute names
    @type attribute_names: sequence of strings
    @return: list of attribute value objects
    """
    return dict([(name, getattr(instance, name))
                 for name in attribute_names if hasattr(instance, name)])


def _set_attribute_values(instance, attribute_values, attribute_names):
    """
    Sets the values of declared attribute in the given object instance and
    attribute names.

    @param instance: object to set the attribute values of
    @type instance: object instance
    @param attribute_values: attribute value map
    @type attribute_values: dictionary
    @param attribute_names: attribute names
    @type attribute_names: sequence type
    @raise AttributeError: if any of the keys in {attribute_values} is not
      in L{attribute_names}
    """
    # make sure that all values to be set correspond to attributes *before* you
    # start setting anything:
    if [key for key in attribute_values if not key in attribute_names ]:
        raise AttributeError('%s has no attribute "%s"' % (instance, key))
    for attr_name, attr_value in attribute_values.iteritems():
        setattr(instance, attr_name, attr_value)


def get_attributes(cls):
    """
    Returns a list of attributes declared via C{__attributes__} containers
    for the given class.

    @note: the attribute *names* (C{str} instances!) are returned.
    @param cls: class to query managed attributes of
    @type cls: arbitrary type object
    @return: list of attribute names (strings)
    """
    return _get_attribute_names(cls, '__attributes__', Attribute)


def get_slots(cls):
    """
    Returns a list of slots declared via C{__slots__} containers
    for the given class.

    @note: the slot *names* (C{str} instances!) are returned.
    @param cls: class to query managed slots of
    @type cls: arbitrary type object
    @return: list of slot names (strings)
    """
    return _get_attribute_names(cls, '__slots__', Slot)


def get_public_attributes(cls):
    """
    Calls L{get_attributes} and filters the resulting list through
    L{is_public} so that only public attributes are returned.

    @param cls: class to query managed public attributes of
    @type cls: arbitrary type object
    @return: list of attribute names (strings)
    """
    return [attr for attr in get_attributes(cls) if is_public(attr)]


def get_public_slots(cls):
    """
    Calls L{get_slots} and filters the resulting list through
    L{is_public} so that only public slots are returned.

    @param cls: class to query managed public slots of
    @type cls: arbitrary type object
    @return: list of slot names (strings)
    """
    return [attr for attr in get_slots(cls) if is_public(attr)]


def get_attribute_values(instance):
    """
    returns a mapping of managed attribute names to their values for the given
    instance.

    @param instance: instance to query
    @type instance: arbitrary object
    @return: managed attribute value dictionary (strings to arbitrary objects)
    """
    return _get_attribute_values(instance, get_attributes(instance.__class__))


def get_slot_values(instance):
    """
    returns a mapping of managed slot names to their values for the given
    instance.

    @param instance: instance to query
    @type instance: arbitrary object
    @return: managed slot value dictionary (strings to arbitrary objects)
    """
    return _get_attribute_values(instance, get_slots(instance.__class__))


def get_public_attribute_values(instance):
    """
    Returns a mapping of public managed attribute names to their values for
    the given instance.

    @param instance: instance to query
    @type instance: arbitrary object
    @return: public managed attribute value dictionary (strings to arbitrary
      objects)
    """
    return _get_attribute_values(instance,
                               get_public_attributes(instance.__class__))


def get_public_slot_values(instance):
    """
    Returns a mapping of public managed slot names to their values for the
    given instance.

    @param instance: instance to query
    @type instance: arbitrary object
    @return: public managed slot value dictionary (strings to arbitrary
      objects)
    """
    return _get_attribute_values(instance,
                               get_public_slots(instance.__class__))


def set_attribute_values(instance, attribute_values):
    """
    Sets managed attributes in the given instance from the given attribute
    value map.

    @param instance: instance to set managed attributes in
    @type instance: arbitrary object
    @param attribute_values: maps managed attribute names to their values
    @type attribute_values: dictionary
    """
    _set_attribute_values(instance, attribute_values,
                        get_attributes(instance.__class__))


def set_slot_values(instance, slotValues):
    """
    Sets managed slots in the given instance from the given slot value map.

    @param instance: instance to set managed slot in
    @type instance: arbitrary object
    @param slotValues: maps managed slot names to their values
    @type slotValues: dictionary
    """
    _set_attribute_values(instance, slotValues, get_slots(instance.__class__))
