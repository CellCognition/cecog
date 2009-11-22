"""
Property management classes.

properties are variables (in the sense defined in the L{pdk.variables} module)
that are used as instance attributes. They are particularly useful for
validating user input in interactive sessions (see the L{pdk.properties}
module.)

The main property manager class L{pdk.propertymanagers.PropertyManager}
 - uses the L{pdk.declarationcollectors.DeclarationCollector} to collect the
   property declarations in a class (and its base classes) and then
   initializes all properties with their default value (constructor)
 - controls property value changes (C{configure} method)
 - prints out help on selected or on all properties (C{help} method)
 - provides methods for property queries (C{getProperty} and
   C{getProperties} methods) and dynamic declaration of new properties
   (C{addProperty} method)

A good use case are device drivers, as it is demonstrated in the example code
in this module. Another useful application are the classes in
the L{pdk.gui.widgets.monitors} module, which provide a set of widgets
that monitor the value of a property in a bi-directional fashion (i.e., the
widget value changes when the property changes and vice versa).

This code incorporates ideas taken from Graphite, which was originally written
written by Joseph and Michelle Strout in 1999.

Example: use property classes to track attributes of external devices

    >>> from pdk.propertymanagers import PropertyManager
    >>> from pdk.properties import FloatProperty
    >>> # this is just a dummy class that could be substituted for a real
    >>> # device class, in which the .get() and .set() methods would call
    >>> # low level device driver routines that do the real work:
    >>> class DummyFeverThermometerDevice:
    ...     def __init__(self):
    ...         self.__temperature = 38.5
    ...     def set(self, value):
    ...         self.__temperature = value
    ...     def get(self):
    ...         return self.__temperature
    >>> # this class serves as a frontend to the device we want to interact
    >>> # with:
    >>> class FeverThermometer(PropertyManager):
    ...     __attributes__ = ["_FeverThermometer__device"]
    ...     PROPERTIES = \
                dict(temperature=
    ...               FloatProperty(None,
    ...                             info="the temperature measured by "
    ...                                  "the fever thermometer",
    ...                             min_value=35,
    ...                             max_value=42,
    ...                             getCallback="getTemperature",
    ...                             setPreCallback="validateTemperature",
    ...                             setPostCallback="setTemperature",
    ...                             )
    ...              )
    ...     def __init__(self, **options):
    ...         super(FeverThermometer, self).__init__(**options)
    ...         # set up your device driver here:
    ...         self.__device = DummyFeverThermometerDevice()
    ...     def getTemperature(self):
    ...         return self.__device.get()
    ...     def validateTemperature(self, value):
    ...         if isinstance(value, basestring):
    ...             if value[-1] == "C":
    ...                 fResult = float(value[:-1])
    ...             elif value[-1] == "F":
    ...                 fResult = (int(value[:-1]) - 32) * (1/1.8)
    ...             else:
    ...                 raise ValueError("invalid input for temperature "
    ...                                  "property '%s'" % value)
    ...         else:
    ...             fResult = value
    ...         return fResult
    ...     def setTemperature(self, value):
    ...         self.__device.set(value)
    >>> t = FeverThermometer()
    >>> # initial (default) value:
    >>> t.temperature
    38.5
    >>> # set to a valid value (40):
    >>> t.temperature = 40
    >>> t.temperature
    40.0
    >>> # set to an invalid value (44) triggers a value error; the value is
    >>> # unchanged:
    >>> try:
    ...     t.temperature = 44
    ... except ValueError:
    ...     pass
    >>> t.temperature
    40.0
    >>> # set to a valid string value ("37C") which is converted to a float:
    >>> t.temperature = "37C"
    >>> t.temperature
    37.0
    >>> # set to valid string value in degree Fahrenheit ("100F"), which is
    >>> # converted to a float in degree Celsius:
    >>> t.temperature = "100F"
    >>> round(t.temperature, 2) == 37.78
    True

FOG 08.2001,10.2002
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"


__all__ = ['ComponentPropertyManager',
           'MetaPropertyDeclarationCollector',
           'PropertyManager',
           'ReportingPropertyManager',
           'dir',
           'help',
           'registerSlotConfigure',
           'unregisterSlotConfigure'
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import sys, \
       types, \
       weakref
from copy import deepcopy

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.attributemanagers import (get_attributes,
                                   get_attribute_values,
                                   set_attribute_values)
from pdk.errors import IllegalArgumentError
from pdk.declarationcollectors import (DeclarationCollector,
                                       MetaDeclarationCollector)
#from pdk.messaging import (Signal,
#                           sendSignalObject)
from pdk.properties import (Property,
                            isProperty)
from pdk.pyutils import get_traceback

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# helper functions:
#

def dir(arg=None):
    """
    Augments the standard C{dir} function to return a list of properties for
    the given L{PropertyManager} instance.

    @param arg: object to query
    @type arg: arbitrary object
    """
    if not arg is None and isinstance(arg, PropertyManager):
        lstNames = arg.PROPERTIES.keys()
    else:
        if arg is None:
            lstNames = globals().values()
        else:
            lstNames = sys.modules['__builtin__'].dir(arg)
    return lstNames


def help(arg, propertyName=None):
    """
    Returns documentation for the given object.

    @param arg: object to query
    @type arg: arbitrary object
    @param propertyName: optional name of the property to query
    @type propertyName: string
    @return: help message (string)
    """
    if isinstance(arg, PropertyManager):
        strHelp = arg.help(propertyName)
    else:
        strHelp = sys.modules['__builtin__'].help(arg)
    return strHelp


#------------------------------------------------------------------------------
# classes:
#

#
# manager classes:
#

class ManagedPropertyDescriptor(property):
    """
    Custom descriptor for managed properties
    """

    def __init__(self, name):
        """
        Extends L{property.__init__}.
        """
        self.__name = name

    #
    # magic methods:
    #

    def __get__(self, instance, cls):
        """
        Overrides C{property.__get__}. Queries the given instance for the
        managed property value.

        @return: value of this managed property (arbitrary object)
        @note: if C{None} is passed in as L{instance}, the class property
          default value is returned
        """
        # FIXME: we are calling a *protected* method here - nasty!
        if not instance is None:
            oValue = instance._getPropertyValue(self.__name)
        else:
            oValue = cls.PROPERTIES[self.__name].get_default_value()
        return oValue

    def __set__(self, instance, value):
        """
        Overrides C{property.__set__}. Sets the managed property value on the
        given instance.
        """
        # FIXME: we are calling a *protected* method here - nasty!
        return instance._setPropertyValue(self.__name, value)

    def __delete__(self, instance):
        """
        Overrides C{property.__delete__}. Deletes the mangaged property value
        from the given instance.
        """
        # FIXME: we are calling a *protected* method here - nasty!
        instance._delPropertyValue(self.__name)


class MetaPropertyDeclarationCollector(MetaDeclarationCollector):
    """
    Specialized meta class collecting property declarations
    """

#    #
#    # public methods:
#    #
#
#    def get_declaration_class(mcs):
#        """
#        Implements
#        L{pdk.declarations.MetaDeclarationCollector.get_declaration_class}.
#        """
#        return Property
#
#    def get_declaration_container_name(mcs):
#        """
#        Implements
#        L{pdk.declarations.MetaDeclarationCollector.get_declaration_container_name}.
#        """
#        return 'PROPERTIES'
    #
    # protected methods:
    #

    def _validate_declaration(mcs, decl):
        """
        Overrides L{MetaDeclarationCollector._validate_declaration}. Ensures
        that the given declaration is a L{Property} instance.
        """
        if not isProperty(decl):
            oProperty = Property(decl)
        else:
            oProperty = decl
        return oProperty


class PropertyManager(DeclarationCollector):
    """
    Manages properties in objects

    Classes derived from L{PropertyManager} may declare
    properties in a "PROPERTIES" dictionary. During instantiation, all base
    classes are traversed and all their property definitions are added to
    the definitions of the derived class.

    Names of managed properties are *all lowercase* to distinguish them from
    local instance variables as well as from special keywords needed for
    implementing the property behavior (which are I{all uppercase}).

    Properties are implemented as restricted attributes using a specialized
    descriptor (see L{pdk.propertymanagers.ManagedPropertyDescriptor}).
    The constructor takes arbitrary initial values for the defined properties
    and L{configure} method allows for simultaneous runtime configuration of
    multiple properties.

    As described in more detail in the L{pdk.properties} module, each
    property can define callbacks to be triggered upon various actions
    (e.g., a get callback when a property is accessed).

    @cvar PROPERTIES: container dictionary for the property declarations
    @note: only declared properties are allowed as attributes of
      L{PropertyManager} instances
    @note: new properties can be added at runtime with the L{addProperty}
      and L{addClassProperty} methods
    @note: calling the .L{configure} method for a read-only attribute of
      non-None value will raise an error
    @note: if the callbacks for a property rely on the constructor
      having finished its work, set the C{isAutoInit} flag for this
      property to C{False} and then call L{configure} or L{setToDefaultValue}
      explicitly
    @note: dynamically adding/modifying properties to/of a base class
      will B{not} be reflected in derived classes, as each class
      collects the properties from all bases only once from the static class
      namespace
    @note: property definitions in base classes can be overridden by
      defining a property with the same name in a derived class. Base classes
      are taversed in the Python-specific left-to-right manner
    """

    __metaclass__ = MetaPropertyDeclarationCollector

    __attributes__ = ['_PropertyManager__dctProperties',
                      '_PropertyManager__dctPropertyValues',
                      ]

    PROPERTIES = {}

    def __init__(self, **initProperties):
        """
        Constructor.

        @param initProperties: keyword arguments for property initialization
        @type initProperties: variable-length dictionary
        @raise ValueError: if any key in L{initProperties} refers to an
          undefined property
        """
        # obtain a copy of the class-level property dictionary:
        self.__dctProperties = deepcopy(self.__class__.PROPERTIES)

        # initialize the property value dictionary:
        self.__dctPropertyValues = {}

        # initialize properties from the data provided in `initPropertyD`:
        for strPropertyName in self.__dctProperties.iterkeys():
            try:
                oInitValue = initProperties[strPropertyName]
            except KeyError:
                self.__initializeProperty(strPropertyName)
            else:
                self.__initializeProperty(strPropertyName, oInitValue)
                del initProperties[strPropertyName]

        if len(initProperties) > 0:
            raise ValueError('trying to initialize undefined properties (%s)'
                             % initProperties.keys())

        super(PropertyManager, self).__init__(self)

    #
    # magic methods:
    #

    def __str__(self):
        """
        Overrides L{__builtin__.object.__str__}.
        """
        lstReprLines = []
        lstPropertyNames = self.__dctProperties.keys()
        lstPropertyNames.sort()
        for propertyName in lstPropertyNames:
            try:
                lstReprLines.append("%s=%s" % (propertyName,
                                               getattr(self, propertyName)))
            except AttributeError: # property was deleted for this instance
                pass
        strPad = ' ' * (len(self.__class__.__name__)+1)
        return "%s(%s)" % (self.__class__.__name__,
                           ('\n%s' % strPad).join(lstReprLines))

    def __repr__(self):
        """
        Called to obtain a string representation of this property manager.
        """
        return self.__str__()

    def __getstate__(self):
        """
        Called to obtain the state of this property manager. Calls
        L{pdk.attributemanagers.get_attribute_values}.

        @return: state dictionary
        """
#        print '__getstate__ of PropertyManager called!', self.__class__
        return get_attribute_values(self)

    def __setstate__(self, state):
        """
        Called to restore the state of this property manager. Calls
        L{pdk.attributemanagers.set_attribute_values}.

        @param state: state information
        @type state: dictionary
        """
#        print ('__setstate__ of PropertyManager called!',
#               self.__class__,
#               attribute_valueD)
        set_attribute_values(self, state)

    def __setattr__(self, attribute_name, attribute_value):
        """
        Cverrides C{object.__setattr__} to protect the instance namespace.

        @raise AttributeError: if an attempt is made to set an attribute that
          is not one of the declared attributes for this class or one of the
          declared managed property names
        """
        if not attribute_name in get_attributes(self.__class__) \
               and not attribute_name in self.__dctProperties.keys():
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, attribute_name))
        else:
            super(PropertyManager, self).__setattr__(attribute_name,
                                                     attribute_value)

    #
    # public methods:
    #

    @classmethod
    def get_declaration_class(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_class}.
        """
        return Property

    @classmethod
    def get_declaration_container_name(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_container_name}.
        """
        return 'PROPERTIES'

    def configure(self, **properties):
        """
        Sets values for (multiple) properties.

        @param properties: keyword arguments setting new property values
        @type properties: variable-length dictionary
        """
        for strPropertyName, oPropertyValue in properties.items():
            self._setPropertyValue(strPropertyName, oPropertyValue,
                                   CHECKFORREADONLY=True)

    def configurePrivate(self, **properties):
        """
        Like L{configure}, but by-passes the read-only check.
        """
        for strPropertyName, oPropertyValue in properties.items():
            self._setPropertyValue(strPropertyName, oPropertyValue)

    def configureNoCallbacks(self, **properties):
        """
        Like L{configure}, but does not execute any callbacks.
        """
        for strPropertyName,oPropertyValue in properties.items():
            self._setPropertyValue(strPropertyName, oPropertyValue,
                                   PROCESSCALLBACKS=False)

    def default(self, propertyName):
        """
        Returns the default value for the given property name.

        @param propertyName: name of the property to query
        @type propertyName: string
        @return: default property value (arbitrary object)
        """
        try:
            oProperty = self.__dctProperties[propertyName]
            return oProperty.get_default_value()
        except KeyError:
            raise AttributeError('"%s" is not a property of %s' %
                                 (propertyName, self.__class__.__name__))

    def help(self, propertyName=None):
        """
        Returns the help string for the given property name.

        @param propertyName: name of the property to query. If this is not
          given, help for I{all} properties is generated
        @type propertyName: string or C{None}
        @raise AttributeError: if a L{propertyName} is given that is not a
          declared property of this property manager
        @return: help message (string)
        """
        if propertyName is None:
            strHelp = 'properties:\n'
            for strPropertyName in self.__dctProperties.keys():
                oProperty = self.__dctProperties[strPropertyName]
                strDescr, strVal = oProperty.getInfo()
                strHelp = "%s   %s (%s): %s\n" % (strHelp,
                                                  strPropertyName,
                                                  strDescr,
                                                  strVal)
        else:
            try:
                oProperty = self.__dctProperties[propertyName]
            except KeyError:
                raise AttributeError('"%s" is not a property of %s' %
                                     (propertyName,self.__class__.__name__))
            else:
                strDescr, strVal = oProperty.getInfo()
                strHelp = "%s (%s): %s" % (propertyName,
                                           strDescr,
                                           strVal)
        return strHelp

    def updateProperties(self, newProperties):
        """
        Updates the properties of this instance with the given new property
        settings.

        @param newProperties: maps property names to new property values
        @type newProperties: dictionary
        @raise KeyError: if L{newProperties} contains an undeclared property
          name
        @raise ValueError: if any value in L{newProperties} is not a
          L{pdk.properties.Property} instance
        """
        dctProperties = self.__dctProperties
        for strPropertyName,oProperty in newProperties.iteritems():
            if not strPropertyName in dctProperties:
                raise KeyError('undefined property "%s"' % strPropertyName)
            if not isProperty(oProperty):
                raise ValueError('invalid property "%s"' % oProperty)
        self.__dctProperties.update(newProperties)

    def getProperties(self, copy=True):
        """
        Returns (a copy of) all managed properties.

        @param copy: if set, the property declarations will be copied
        @type copy: Boolean
        @return: dictionary mapping property names to L{property} instances
        """
        if copy:
            dctProperties = self.__dctProperties.copy()
        else:
            dctProperties = self.__dctProperties
        return dctProperties

    def getProperty(self, propertyName):
        """
        Returns the property for the given property name.

        @param propertyName: name of the property to return
        @type propertyName: string
        @return: L{property} instance
        """
        return self.__dctProperties[propertyName]

    def getPropertyNames(self):
        """
        Returns the names of all managed properties.

        @return: list of managed property names
        """
        return self.__dctProperties.keys()

    def getPropertyValues(self):
        """
        Returns the values of all managed properties.

        @return: list of managed property values
        """
        return self.__dctPropertyValues.values()

    def getPropertyMapping(self, copy=True):
        """
        Returns (a copy of) the mapping of property names to property values.

        @param copy: if set, the property mapping will be copied
        @type copy: Boolean
        @return: dictionary mapping property names to property values
        """
        if copy:
            dctPropertyValues = self.__dctPropertyValues.copy()
        else:
            dctPropertyValues = self.__dctPropertyValues
        return dctPropertyValues

    def hasProperty(self, propertyName):
        """
        Checks if the given property name is a managed property.

        @param propertyName: name of the property to query
        @type propertyName: string
        @return: Boolean
        """
        return propertyName in self.__dctProperties

    def hasPropertyName(self, propertyName):
        """
        Alias for L{hasProperty}.
        """
        return self.hasProperty(propertyName)

    def addProperty(self, propertyName, propertyInstance):
        """
        Adds the given property as a managed property with the
        given name.

        @param propertyName: name of the new property
        @type propertyName: string
        @param propertyInstance: property to manage
        @type propertyInstance: L{pdk.properties.Property} instance
        """
        self.__dctProperties[propertyName] = propertyInstance
        # initialize with the default value:
        self.__initializeProperty(propertyName,
                                  propertyInstance.get_default_value())

    def removeProperty(self, propertyName):
        """
        Removes the managed property with the given name.

        @param propertyName: name of the managed property to remove
        @type propertyName: string
        """
        del self.__dctProperties[propertyName]
        del self.__dctPropertyValues[propertyName]

    def set_default_values(self, **properties):
        """
        Sets new default values for managed properties from the given map.

        @param properties: keyword arguments providing new default values
          for managed property names
        @type properties: variable-length dictionary
        @note: if a property is currently set to its I{old} default value,
          it will be set automatically to its I{new} default value.
        """
        for strPropertyName,oNewDefaultValue in properties.items():
            oProperty = self.getProperty(strPropertyName)
            oldDefaultValue = oProperty.get_default_value()
            oProperty.set_default_value(oNewDefaultValue)
            if getattr(self, strPropertyName) == oldDefaultValue:
                self._setPropertyValue(strPropertyName, oNewDefaultValue)

    def setReadOnly(self, *propertyNames):
        """
        Sets the given managed properties as read-only.

        @param propertyNames: names of the managed properties to set read-only
        @type propertyNames: variable-length tuple
        """
        for strPropertyName in propertyNames:
            oProperty = self.getProperty(strPropertyName)
            oProperty.isReadOnly = True

    def setToDefaultValue(self, *propertyNames):
        """
        Sets the given managed properties to their default value.

        @param propertyNames: names of the managed properties to set to their
          default value
        @type propertyNames: variable-length tuple
        """
        for strPropertyName in propertyNames:
            oProperty = self.getProperty(strPropertyName)
            self._setPropertyValue(strPropertyName, oProperty.get_default_value())

    @classmethod
    def getClassProperty(cls, propertyName):
        """
        Returns the class-level property for the given property name.

        @param propertyName: name of the class property to return
        @type propertyName: string
        @return: a L{pdk.properties.Property} instance
        """
        return cls.PROPERTIES[propertyName]

    @classmethod
    def addClassProperty(cls, propertyName, propertyInstance):
        """
        Adds the given property as a class-level managed property with the
        given name.

        @param propertyName: name of the new property
        @type propertyName: string
        @param propertyInstance: property to manage
        @type propertyInstance: L{pdk.properties.Property} instance
        """
        cls.PROPERTIES[propertyName] = propertyInstance

    @classmethod
    def setClassDefaultValues(cls, **properties):
        """
        Sets new default values for class-level managed properties from the
        given map.

        @param properties: keyword arguments providing new default values
          for managed property names
        @type properties: variable-length dictionary
        """
        for strPropertyName, oNewDefaultValue in properties.items():
            oClassProperty = cls.getClassProperty(strPropertyName)
            oClassProperty.set_default_value(oNewDefaultValue)

    #
    # protected methods:
    #

    def _setPropertyValue(self, propertyName, propertyValue,
                          CHECKFORREADONLY=True, PROCESSCALLBACKS=True):
        """
        Sets the specified managed property to the given new value.

        @param propertyName: name of the managed property to set
        @type propertyName: string
        @param propertyValue: new property value
        @type propertyValue: arbitrary object
        @param CHECKFORREADONLY: if set, the new value will only be set if
          the property does not have the "isReadOnly" flag set
        @type CHECKFORREADONLY: Boolean
        @param PROCESSCALLBACKS: if set, all not-C{None} property callbacks
          will be executed
        @type PROCESSCALLBACKS: Boolean
        """
        try:
            oProperty = self.__dctProperties[propertyName]
        except:
            raise AttributeError('trying to set an undefined property "%s" '
                                 'in an instance of class "%s"' %
                                 (propertyName, self.__class__.__name__))

        # now, check for read-only properties
        # No error is raised when trying to modify a read-only property, if
        # a) the CHECKREADONLY flag is set to False (since this is the default,
        #    direct local assignments  as in foo.bar = foobar always work);
        # b) the current value is None (i.e., a ro-attribute can be
        #    initialized to None and then changed once to a non-None value).
        if CHECKFORREADONLY and oProperty.isReadOnly and \
           not self._getPropertyValue(propertyName) is None:
            raise ValueError('property "%s" for instance of class "%s" is '
                             'set readonly!' %
                             (propertyName, self.__class__.__name__))

##        if not getCallback is None and setPostCallback is None:
##            raise ValueError('cannot assign a value to a property that '
##                             'defines a get callback, but no post-set '
##                             'callback!')

        # check whether it is okay to assign to this property. If a pre-set
        # callback is defined, it returns a possibly modified value:
        # value:
        if PROCESSCALLBACKS and not oProperty.setPreCallback is None:
            propertyValue = self.__callCallback(oProperty.setPreCallback,
                                                propertyValue)
        try:
            propertyValue = oProperty.validate(propertyValue)
        except ValueError:
            if propertyValue is None and not oProperty.is_not_none:
                pass
            else:
                raise

        # process the set-post callback, if any:
        if PROCESSCALLBACKS and not oProperty.setPostCallback is None:
            self.__callCallback(oProperty.setPostCallback, propertyValue)

        # finally, store the value, if no get callback is defined:
        if oProperty.getCallback is None:
            self.__dctPropertyValues[propertyName] = propertyValue

    def _getPropertyValue(self, propertyName):
        """
        Returns the current value for the specified managed property.

        @param propertyName: name of the managed property to query
        @type propertyName: string
        @raise AttributeError: if there is no managed property of the given
          name or if the property has not been initialized yet
        @return: property value (arbitrary object)
        """
        try:
            oProperty = self.__dctProperties[propertyName]
        except:
            raise AttributeError('instance of class "%s" has no property "%s".'
                                 % (self.__class__.__name__, propertyName))

        if not oProperty.getCallback is None:
            oPropertyValue = self.__callCallback(oProperty.getCallback)
        else:
            try:
                oPropertyValue = self.__dctPropertyValues[propertyName]
            except KeyError:
                raise AttributeError('property "%s" has not been initialized '
                                     'yet!' % propertyName)
        return oPropertyValue

    def _delPropertyValue(self, propertyName):
        """
        Deletes the value for the specified managed property.

        @param propertyName: name of the managed property to delete the value
          for
        @type propertyName: string
        @raise AttributeError: if there is no managed property of the given
          name or if the property has not been initialized yet
        @raise ValueError: if the specified managed property defines a get
          callback, but no delete callback
        """
        try:
            oProperty = self.__dctProperties[propertyName]
        except:
            raise AttributeError('instance of class "%s" has no property "%s".'
                                 % (self.__class__.__name__, propertyName))

        if oProperty.delCallback is None:
            if not oProperty.getCallback is None:
                raise ValueError('cannot delete the value of a property that '
                                 'defines a get callback, but no delete '
                                 'callback!')
            try:
                del self.__dctPropertyValues[propertyName]
            except KeyError:
                raise AttributeError('property "%s" has not been initialized '
                                     'yet!' % propertyName)

        else:
            self.__callCallback(oProperty.delCallback)

    #
    # private methods:
    #

    def __initializeProperty(self, propertyName, *tplInitValue):
        # if the instance does not already have an attribute of the given
        # property name, create a new property descriptor and make it a class
        # attribute:
        if hasattr(self, propertyName):
            raise ValueError('instance already has an attribute "%s"' %
                             propertyName)
        oDescriptor = ManagedPropertyDescriptor(propertyName)
        setattr(self.__class__, propertyName, oDescriptor)

        # initialize the new property from the property instance.
        # The init value tuple may contain a single argument, the
        # initialization value for the property (which might be ``None``,
        # which is why we can't use that as a default value). Note that
        # initialization is suppressed if the "isAutoInit" flag is not set for
        # this property:
        try:
            oInitValue, = tplInitValue
            tDoInitialize = True
        except ValueError:
            # no initial value was passed, so we check
            #   a) if a property value is mandatory and
            #   b) if we should initialize from the default value
            oProperty = self.__dctProperties[propertyName]
            if oProperty.is_mandatory:
                raise ValueError('property "%s" needs an initialization value!'
                                 % propertyName)
            tDoInitialize = oProperty.isAutoInit
            if tDoInitialize:
                oInitValue = oProperty.get_default_value()

        if tDoInitialize:
            # set the initial value of the property:
            if not oInitValue is None:
                try:
                    self._setPropertyValue(propertyName,
                                           oInitValue,
                                           CHECKFORREADONLY=False)
                except ValueError:
                    raise ValueError('invalid initialization value for '
                                     'property "%s" (%s)' %
                                     (propertyName, oInitValue))
            else:
                self.__dctPropertyValues[propertyName] = None

    def __callCallback(self, oCallback, *args):
        # execute a callback. `oCallback` should be either a callable (functions
        # are called with ``self`` as first argument) or a string giving the
        # name of a method of ``self``:
        if callable(oCallback):
            if isinstance(oCallback, types.FunctionType):
                oResult = oCallback(self, *args)
            else:
                oResult = oCallback(*args)
        else:
            try:
                oResult = getattr(self, oCallback)(*args)
            except:
                raise ValueError('calling the callback '
                                 '"%s" with args "%s" failed. '
                                 '\nTraceback of the error causing the '
                                 'failure:\n %s' %
                                 (oCallback, args, get_traceback()))
        return oResult


class ComponentPropertyManager(PropertyManager):
    """
    Adds handling of components to the basic L{PropertyManager} class

    A component is an object that is accessible as an attribute of
    the container object. Component properties are accessed with this
    notation: ::
        <component name>_<property name>

    @note: you must not initialize component properties in the constructor
      call; rather, set up the components I{after} the instance has been
      created by calling the L{addComponent} method, and then call
      L{configure} to initialize the components
    """

    __attributes__ = ['_ComponentPropertyManager__dctComponents',
                      '_ComponentPropertyManager__dctComponentGroups'
                      ]

    def __init__(self, **initProperties):
        """
        Extends L{PropertyManager.__init__}.

        @raise ValueError: if an attempt is made to configure a component
          property in the given initialization property dictionary
        """
        for strPropertyName, oPropertyValue in initProperties.items():
            if "_" in strPropertyName and not strPropertyName[0] == '_':
                raise ValueError('cannot configure components in constructor '
                                 'call. Please configure components '
                                 'explicitly by calling .configure()')
        super(ComponentPropertyManager, self).__init__(**initProperties)
        self.__dctComponents = {}
        self.__dctComponentGroups = {}

    #
    # magic methods:
    #

    def __getstate__(self):
        """
        Extends L{PropertyManager.__getstate__}.
        """
        tplState = super(ComponentPropertyManager, self).__getstate__()
        return (self.__dctComponents,self.__dctComponentGroups) + tplState

    def __setstate__(self, args):
        """
        Extends L{PropertyManager.__setstate__}.
        """
        self.__dctComponents = args[0]
        self.__dctComponentGroups = args[1]
        super(ComponentPropertyManager, self).__setstate__(args[2:])

    #
    # public methods:
    #

    def addComponent(self, name, group, component):
        """
        Adds the given component to the given group under the given name.

        @param name: name of the component
        @type name: string
        @param group: group to add this component to
        @type group: string
        @param component: component to add
        @type component: arbitrary object
        """
        if name is None:
            strComponentName = self.__getNewComponentName(group)
        elif not name[:len(group)] == group:
            strComponentName = "%s%s" % (group,name)
        else:
            strComponentName = name

        # add a dynamic property so we can access components with getattr:
        setattr(self.__class__,
                strComponentName,
                property(lambda self,strName=strComponentName:
                         self.getComponent(strName)))

        # store the data for this component:
        self.__dctComponents[strComponentName] = component
        self.__dctComponentGroups.setdefault(group, []).append(component)

    def getComponent(self, name, group=None):
        """
        Returns the component of the given name (and group)

        @param name: name of the component to return
        @type name: string
        @param group: group of the component to return (defaults to C{None})
        @type group: string
        @return: component (arbitrary object)
        """
        if not group is None:
            name = "%s%s" % (group,name)
        return self.__dctComponents[name]

    def getComponentGroup(self, group):
        """
        Returns the specified component group.

        @param group: component group to return
        @type group: string
        @return: a list of components or an empty list, if no group of the
          specified name exists
        """
        try:
            result = self.__dctComponentGroups[group]
        except KeyError:
            result = []
        return result

    def configure(self, **properties):
        """
        Extends L{PropertyManager.configure}.
        """
        for strPropertyName, oPropertyValue in properties.items():
            if "_" in strPropertyName and not strPropertyName[0] == '_':
                intPos = strPropertyName.find("_")
                oComponent = getattr(self, strPropertyName[:intPos])
                oComponent.configure(**dict([(strPropertyName[intPos+1:],
                                              oPropertyValue)]))
                del properties[strPropertyName]
        if properties:
            super(ComponentPropertyManager, self).configure(**properties)

    #
    # private methods:
    #

    def __getNewComponentName(self, strGroup):
        try:
            intCount = len(self.__dctComponentGroups[strGroup]) + 1
        except KeyError:
            intCount = 1
        return "%s%d" % (strGroup, intCount)


class ReportingPropertyManager(PropertyManager):
    """
    Adds signalling and XML registry updating to the
    L{PropertyManager} class

    This is implemented by extending the
    L{PropertyManager.configure} method to also
    emit a signal and/or register a property value change.

    @note: whith this implementation, neither setting the initialization
      values for the properties (in the constructor) nor setting them
      directly (as in C{foo.bar = foobar}) does trigger a signal or
      register a change
    @note: by default, a L{pdk.messaging.Signal} instance is created with
      a lambda returning the current value of the property as send function.
      To override this, manually call the .L{initializeSignal} method with
      the signal object/send function combination of your choice
      (see the C{initializeWidget} method of
      L{pdk.gui.statemanagers._WidgetStateManager} for an example).
    """

    __attributes__ = ['_ReportingPropertyManager__dctPropertySignals',
                      '_ReportingPropertyManager__oRegistry',
                      '_ReportingPropertyManager__strObjectId',
                      '_ReportingPropertyManager__tIsRegistrationEnabled',
                      '_ReportingPropertyManager__tIsSignallingEnabled',
                      ]

    def __init__(self, objectIdString,
                 enableSignalling=False, xmlRegistry=None):
        """
        Constructor.

        @param objectIdString: unique (within the application) object ID
            representing the object the properties of which are being
            managed
        @type objectIdString: string
        @param enableSignalling: specifies whether property changes should
            trigger a corresponding signal to be sent in this object or
            not
        @type enableSignalling: Boolean
        @param xmlRegistry: application registry accessor, or C{None}, if no
          registration is desired
        @type xmlRegistry: L{pdk.applicationregistry.AppRegistryKeyAccessor}
          instance
        @note: read-only properties are not stored in the registry
        """
        PropertyManager.__init__(self)
        # if signalling of changes is enabled, associate a signal with each
        # property:
        self.__tIsSignallingEnabled = enableSignalling
        if enableSignalling:
            self.__strObjectId = objectIdString
            self.__dctPropertySignals = {}
        # if registration is enabled, store the given registry:
        self.__tIsRegistrationEnabled = not xmlRegistry is None
        if self.__tIsRegistrationEnabled:
            self.__oRegistry = xmlRegistry

    #
    # magic methods:
    #

    def __getstate__(self):
        """
        Extends L{PropertyManager.__getstate__}.
        """
        tplArgs = super(ReportingPropertyManager, self).__getstate__() + \
                  (self.__tIsSignallingEnabled, self.__tIsRegistrationEnabled)
        if self.__tIsSignallingEnabled:
            tplArgs += (self.__strObjectId, self.__dctPropertySignals)
        if self.__tIsRegistrationEnabled:
            tplArgs += (self.__oRegistry,)
        return tplArgs

    def __setstate__(self, args):
        """
        Extends L{PropertyManager.__setstate__}.
        """
        super(ReportingPropertyManager, self).__setstate__(args[:2])
        self.__tIsSignallingEnabled, self.__tIsRegistrationEnabled = args[2:4]
        if self.__tIsSignallingEnabled:
            self.__strObjectId, self.__dctPropertySignals = args[4:6]
        if self.__tIsRegistrationEnabled:
            self.__oRegistry = args[-1]

    #
    # public methods:
    #

    def configure(self, **properties):
        """
        Extends L{PropertyManager.configure}.
        """
        oBaseMethod = super(ReportingPropertyManager, self).configure
        self.__configure(oBaseMethod, False, False, properties)

    def configureNoSignal(self, **properties):
        """
        Like L{configure}, but suppresses sending a signal even if signalling
        is enabled.
        """
        oBaseMethod = super(ReportingPropertyManager, self).configure
        self.__configure(oBaseMethod, True, False, properties)

    def configureDoRegister(self, **properties):
        """
        Like L{configure}, but registers the new value even if registration
        is disabled.
        """
        oBaseMethod = super(ReportingPropertyManager, self).configure
        self.__configure(oBaseMethod, False, True, properties)

    def configureNoSignalDoRegister(self, **properties):
        """
        Like L{configure}, but suppresses sending a signal I{and} registers
        the new value even if signalling is enabled and registration is
        disabled.
        """
        oBaseMethod = super(ReportingPropertyManager, self).configure
        self.__configure(oBaseMethod, True, True, properties)

    def configurePrivate(self, **properties):
        """
        Extends L{PropertyManager.configurePrivate}.
        """
        oBaseMethod = super(ReportingPropertyManager, self).configurePrivate
        self.__configure(oBaseMethod, False, False, properties)

    def configureNoCallbacks(self, **properties):
        """
        Extends L{PropertyManager.configureNoCallbacks}.
        """
        oBaseMethod = \
                  super(ReportingPropertyManager, self).configureNoCallbacks
        # we never emit a signal/register a change when callbacks are
        # being suppressed:
        self.__configure(oBaseMethod, True, True, properties)

    def getId(self):
        """
        Returns the object ID string associated with this reporting property
        manager.

        @return: object ID string or C{None}, if signalling is not enabled
        """
        if self.__tIsSignallingEnabled:
            oResult = self.__strObjectId
        else:
            oResult = None
        return oResult

    def getRegistryKey(self):
        """
        Returns the registry node key of this property manager.

        @return: registry node key (string) or C{None}, if registration
          is disabled
        """
        if self.__tIsRegistrationEnabled:
            oResult = self.__oRegistry.getRegistryKey()
        else:
            oResult = None
        return oResult

    def getRegistry(self):
        """
        Returns the application registry of this property manager.

        @return: L{pdk.applicationregistry.AppRegistry} instance or
          C{None}, if registration is disabled
        """
        return self.__tIsRegistrationEnabled and self.__oRegistry or None

    def configureFromRegistry(self):
        """
        Retrieves all persistent information for this property manager and
        calls the L{configurePrivate} method with it.

        @note: this has only an effect if registration was enabled during
          initialization
        """
        if self.__tIsRegistrationEnabled:
            dctProperties = self.getPropertiesFromRegistry()
            self.configurePrivate(**dctProperties)

    def getPropertiesFromRegistry(self):
        """
        Returns all stored property values for this property manager from
        the application registry.

        @return: dictionary mapping property names to their values or C{None},
          if registration is disabled
        @note: this has only an effect if registration was enabled during
          initialization
        @note: the "id" attribute is removed from the dictionary returned
          from the XML registry
        """
        if self.__tIsRegistrationEnabled:
            dctProperties = self.__oRegistry.get_attributes()
            try:
                del dctProperties['id']
            except KeyError:
                pass
        else:
            oProperties = None
        return oProperties

    def getPropertyFromRegistry(self, propertyName):
        """
        Retrieves and returns the value of the specified property from the
        XML registry.

        @param propertyName: name of the property to retrieve from the
          application registry
        @type propertyName: string
        @return: stored property value (arbitrary object)
        """
        return self.__oRegistry.getValue(propertyName)

    def storePropertiesToRegistry(self):
        """
        Stores the values for all managed properties to the application
        registry.

        @note: this has only an effect if registration was enabled during
          initialization
        """
        if self.__tIsRegistrationEnabled:
            dctProperties = {}
            for strPropertyName in self.getPropertyNames():
                # we exclude read only properties from registration:
                oProperty = self.getProperty(strPropertyName)
                if not oProperty.isReadOnly:
                    oPropertyValue = getattr(self, strPropertyName)
                    # only store if it's not the default:
                    if oPropertyValue != oProperty.get_default_value():
                        dctProperties[strPropertyName] = \
                                            getattr(self, strPropertyName)
            # we should really call L{egisterChange} on each property here,
            # but this is sooo much faster...:
            self.__oRegistry.updateAttributes(dctProperties)

    def storePropertyToRegistry(self, propertyName):
        """
        Stores the current value of the specified property to the XML
        registry.

        @param propertyName: name of the property to store
        @type propertyName: string
        @note: this has only an effect if registration was enabled during
          initialization
        """
        if self.__tIsRegistrationEnabled:
            oPropertyValue = getattr(self, propertyName)
            self.registerChange(propertyName, oPropertyValue)

    def signalChange(self, propertyName, propertyValue):
        """
        Signals a change of the specified property to the given new value.

        @param propertyName: name of the property that changed
        @type propertyName: string
        @param propertyValue: new property value
        @type propertyValue: arbitrary object
        @note: this has only an effect if signalling was enabled during
          initialization
        """
        if self.__tIsSignallingEnabled:
            self.configure(NOREGISTRATION=True,
                           **{propertyName:propertyValue})

    def registerChange(self, propertyName, propertyValue):
        """
        Registers a change of the specified property to the given value.

        @param propertyName: name of the property that changed
        @type propertyName: string
        @param propertyValue: new property value
        @type propertyValue: arbitrary object
        @note: this has only an effect if registration was enabled during
          initialization
        """
        if self.__tIsRegistrationEnabled:
            self.configureNoSignalDoRegister(**{propertyName:propertyValue})

    def initializeSignal(self, signallingObject, propertyName, messageId,
                         sendCallback=None):
        """
        Initializes a signal instance to be sent for further signalling of
        property value changes (see L{pdk.messaging.Signal} class). This is
        mainly done for performance reasons to avoid re-instantiating the
        same signal each time a change has to be signalled.

        @param signallingObject: object associated with the signal
        @type signallingObject: arbitrary object
        @param propertyName: name of the property to signal value changes for
        @type propertyName: string
        @param messageId: message ID for the signal
        @type messageId: string
        @param sendCallback: send callback
        @type sendCallback: callable object
        @return: a L{pdk.messaging.Signal} instance
        """
        # this initializes the signal. By default, the message payload will
        # be the current property value:
        if sendCallback is None:
            oWeakRef = weakref.ref(signallingObject)
            oSendDataFunction = lambda oRef=oWeakRef,strName=propertyName: \
                                    getattr(oRef(), strName)
        else:
            oSendDataFunction = sendCallback
        oSignal = self.__dctPropertySignals[propertyName] = \
                  Signal(messageId, sendCallback=oSendDataFunction)
        return oSignal

    #
    # private methods:
    #

    def __configure(self, oBaseMethod, tNoSignal, tDoRegister, dctProperties):
        """
        Implements "reporting" configuration: automatically signals and
        registers value changes in properties, if this was enabled during
        initialization.

        @param tNoSignal: if set, signalling is suppressed for this call
        @type tNoSignal: Boolean
        @param tDoRegister: if set, registration is enabled for this call
        @type tDoRegister: Boolean
        """
        oBaseMethod(**dctProperties)
        # if enabled and not suppressed, signal each property value change:
        if self.__tIsSignallingEnabled and not tNoSignal:
            for strPropertyName, oPropertyValue in dctProperties.items():
                try:
                    oSignal = self.__dctPropertySignals[strPropertyName]
                except KeyError:
                    strMessageId = _getConfigureMessageId(self,
                                                          strPropertyName)
                    oSignal = self.initializeSignal(self, strPropertyName,
                                                    strMessageId)
                sendSignalObject(oSignal)
        # if enabled and requested, store each property value change:
        if self.__tIsRegistrationEnabled and tDoRegister:
            for strPropertyName, oPropertyValue in dctProperties.items():
                self.__oRegistry.setValue(strPropertyName,
                                          oPropertyValue)

def _getConfigureMessageId(managedObject, propertyName):
    """
    Returns a unique message id for a property configuration event.

    The ID is created using the class name of L{managedObject} and the
    property name L{propertyName}.

    @param managedObject: object for which configuration events should be
      generated
    @type managedObject: a {ReportingPropertyManager} instance
    @param propertyName: property for which a configuration event message ID
      is needed
    @type propertyName: string
    @note: using the class name of an object for generating the configure
      message ID string implies that multiple instances of the same class
      cannot be managed separately (the reasoning for this solution is that
      we might not always have a handle on the object instance when we want
      to register a slot!)
    @return: message ID string
    """
    return "configuration_%s_%s" % \
           (managedObject.__class__.__name__, propertyName)


def registerSlotConfigure(signalObject, propertyName,
                          slotObject, receiveCallback, **options):
    """
    Registers a specialized slot for a property configuration message.

    @param signalObject: object that will signal configuration events for the
      specified property
    @type signalObject: L{ReportingPropertyManager}
      instance
    @param propertyName: name of the property to track
    @type propertyName: string
    @param slotObject: object that will receive the configuration event
      messages
    @type slotObject: arbitrary object
    @param receiveCallback: callback which will receive the message payload
      (i.e., the new property value)
    @type receiveCallback: callable object
    @param options: keyword arguments to be passed to the
      L{pdk.messaging.registerSlot} function
    @type options: variable-length dictionary
    @raise IllegalArgumentError: if L{signalObject} is not an instance of
      L{ReportingPropertyManager}
    """
    # we make sure `signalObject` is an instance of ReportingPropertyManager:
    if not isinstance(signalObject, ReportingPropertyManager):
        raise IllegalArgumentError('cannot register configure slot for '
                                   'instance of class %s. Needs to be '
                                   'a ReportingPropertyManager instance.' %
                                   signalObject.__class__.__name__)
    strMessageId = _getConfigureMessageId(signalObject, propertyName)
    from pdk.messaging import registerSlot # avoiding circular imports...
    registerSlot(strMessageId, slotObject, receiveCallback, **options)


def unregisterSlotConfigure(signalObject, propertyName, slotObject):
    """
    Un-registers a configuration message slot previously registered with
    L{registerSlotConfigure}.

    @param signalObject: object that is signalling configuration events for
      the specified property
    @type signalObject: L{ReportingPropertyManager}
      instance
    @param propertyName: name of the property to track
    @type propertyName: string
    @param slotObject: object that was registered to listen to configuration
      event messages
    @type slotObject: arbitrary object
    """
    messageId = _getConfigureMessageId(signalObject, propertyName)
    from pdk.messaging import unregisterSlot # avoiding circular imports...
    unregisterSlot(messageId, slotObject)


if __name__ == "__main__":
    from pdk.util.pyutils import execMainDocTest
    execMainDocTest()
