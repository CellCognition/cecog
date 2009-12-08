"""
Classes for managing options.

By default, options are declared in an "C{OPTIONS}" class dictionary;
however, the name of the option container can be configured by overriding
the C{getOptionDeclarationContainerName} method.

Example:

    >>> from pdk.options import Option
    >>> from pdk.optionmanagers import OptionManager
    >>> class Z(OptionManager):
    ...     OPTIONS = {"a" : Option(-1,
    ...                             callback="onA"),
    ...                "b" : 3
    ...                }
    ...     def onA(self, value):
    ...         print "onA called with value", value
    >>> z = Z(a=1, b=2)
    onA called with value 1
    >>> z.getOption("a")
    1
    >>> z.getOption("b")
    2
    >>> z.configure(a=5)
    onA called with value 5
    >>> z.getOption("a")
    5

FOG 03.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['MetaOptionDeclarationCollector',
           'OptionDeclarationCollector',
           'OptionManager',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#

#------------------------------------------------------------------------------
# extension module imports:
#
from copy import deepcopy

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.attributes import Attribute
from pdk.options import Option
from pdk.declarationcollectors import (DeclarationCollector,
                                       MetaDeclarationCollector)

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class MetaOptionDeclarationCollector(MetaDeclarationCollector):
    """
    Meta class for option collectors
    """

    #
    # public methods:
    #

    def getManagedOptions(mcs):
        """
        Returns the container holding the managed options for this class.

        @return: dictionary mapping option names to option instances
        """
        return getattr(mcs, mcs.getOptionDeclarationContainerName())

    def getManagedOptionNames(mcs):
        """
        Returns the managed option names for this class.

        @return: list of option name strings
        @note: the option names are returned in no particular order
        """
        return getattr(mcs, mcs.getOptionDeclarationContainerName()).keys()


class OptionDeclarationCollector(DeclarationCollector):
    """
    Declaration collector class for options held in a dictionary.
    """

    __metaclass__ = MetaOptionDeclarationCollector

    @classmethod
    def get_declaration_class(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_class}.

        Calls L{getOptionDeclaratorClass}.
        """
        return cls.getOptionDeclaratorClass()

    @classmethod
    def get_declaration_container_name(cls):
        """
        Implements
        L{pdk.declarations.DeclarationCollector.get_declaration_container_name}.

        Calls L{getOptionDeclarationContainerName}.
        """
        return cls.getOptionDeclarationContainerName()

    @classmethod
    def getOptionDeclaratorClass(cls):
        """
        Returns the class object to use for attribute declarations gathered
        by this collector.

        @return: attribute declarator class (class object)
        """
        return Option

    @classmethod
    def getOptionDeclarationContainerName(cls):
        """
        Returns the name of the class attribute referring to the conainer
        that will hold the optiondeclarations to gather by this collector.

        @return: option declaration container attribute name (string)
        """
        return 'OPTIONS'


class OptionManager(OptionDeclarationCollector):
    """
    Handles publicly declared options in class instances

    Provides runtime access to all options declared in a public class
    dictionary.

    Option declarations are of the simple form: ::
         { <option name> : <option default value> }

     or ::
         { <option name> : Option(<option default value>,
                                  callback=<option callback>,
                                  doc=<option doc string>) }

    The option callback can be a callable or the name of a method
    to call on the class instance.

    To use the option machinery, either call L{processOptions} manually in
    the constructor of the derived class, or call the cooperative constructor
    to have it call L{processOptions} for you. If any of the declared
    options defines a callback, L{initializeOptions} also needs to be called
    once the constructor has returned.

    All declared options can be accessed with the L{getOption} method and
    set with the L{setOption} or L{configure} methods.

    @note: if the constructor dictionary does not provide a value for
      an option, the declared default value is used as value for the option
    @note: the options dictionary can be updated in derived classes (e.g.,
      to declare new options or to assign new default values to existing
      options)
    @note: the name of the option holder can be changed by overriding the
      L{getOptionDeclarationContainerName} method (defaults to "OPTIONS")
    @note: if a value for C{<option callback>} is passed, this must be
      either a callable (which will be called with C{self} and the new
      option value as arguments) or a string (which will be interpreted
      as the name of a method to be called with the new option value as
      argument)
    @note: when deriving from this class, make sure to include a variable
      keyword argument in your constructor
    """

    __attributes__ = [Attribute('_OptionManager__dctOptions'),
                      ]

    def __init__(self, *args, **options):
        """
        Constructor.

        Calls L{processOptions} I{before} calling the base class constructor,
        and L{initializeOptions} I{thereafter}.
        """
        strOptionContainerName = \
            self.__class__.getOptionDeclarationContainerName()
        self.__dctOptions = deepcopy(getattr(self, strOptionContainerName, {}))
        self.processOptions(options, destructive=True)
        super(OptionManager, self).__init__()
        self.initializeOptions(autoInitializeOnly=True)

    #
    # magic methods:
    #

    def __getstate__(self):
        """
        Called to obtain the state of this option manager.

        Extracts all managed options from this instance and stores them
        under the key C{'options'} in a dictionary.

        @return: dictionary of managed option names and values
        """
        try:
            dctState = super(OptionManager, self).__getstate__()
        except AttributeError:
            dctState = {}
        dctState['options'] = self.getAllOptions()
        return dctState

    def __setstate__(self, state):
        """
        Called to restore the state of this option manager from the given
        state dictionary.

        @param state: maps manged option names to their values
        @type state: dictionary
        """
        strOptionContainerName = \
            self.__class__.getOptionDeclarationContainerName()
        self.__dctOptions = deepcopy(getattr(self, strOptionContainerName))
        self.processOptions(state['options'])
        del state['options']
        try:
            super(OptionManager, self).__setstate__(state)
        except AttributeError:
            pass
        self.initializeOptions(autoInitializeOnly=True)

    #
    # public methods:
    #

    def processOptions(self, initOptions, destructive=False):
        """
        Extracts all options declared for this class from the given
        constructor keyword argument dictionary.

        @note: since the call to this method always precedes all other
          initializations, it is *not* safe to call option callbacks at this
          stage. You will have to explicitly call .L{initializeOptions} for
          that purpose.
        @param initOptions: maps intialization option names to values
        @type initOptions: dictionary
        @param destructive: flag indicating if processed options should be
          removed from L{initOptions}
        @type destructive: Boolean
        """
        dctOptions = self.__dctOptions
        for strOptionName in dctOptions.iterkeys():
            try:
                dctOptions[strOptionName].value = initOptions[strOptionName]
            except KeyError: # set to default value
                dctOptions[strOptionName].value = \
                                            dctOptions[strOptionName].default
            else:
                if destructive:
                    del initOptions[strOptionName]

    def initializeOptions(self, autoInitializeOnly=False):
        """
        Triggers all option callbacks with the current option values.

        @param autoInitializeOnly: flag indicating that options that do not
          have the "autoInitialize" attribute set should be ignored
        @type autoInitializeOnly: Boolean
        """
        dctOptions = self.__dctOptions
        for oOption in dctOptions.itervalues():
            if oOption.value is None:
                continue
            if not oOption.callback is None:
                if autoInitializeOnly and not oOption.autoInitialize:
                    continue
                self.__callOptionCallback(oOption)

    def initializeOption(self, optionName):
        """
        Explicitly initializes the given option. This is useful for options
        that do not have the "autoInitialize" flag set.

        @param optionName: name of the option to initialize
        @type optionName: string
        """
        oOption = self.__dctOptions[optionName]
        if not oOption.value is None and not oOption.callback is None:
            self.__callOptionCallback(oOption)

    def setOption(self, optionName, optionValue):
        """
        Sets the given option to a new value.

        @param optionName: name of the option to set
        @type optionName: string
        @param optionValue: new option value
        @type optionValue: arbitrary object
        """
        oOption = self.__dctOptions[optionName]
        oOption.value = optionValue
        if not oOption.callback is None:
            self.__callOptionCallback(oOption)

    def setOptions(self, **options):
        """
        Sets several options in one call.

        @param options: maps option names to their new values
        @type options: variable-length dictionary
        """
        # FIXME: setOptions should be the one called with a dictionary,
        #        and configure the one with the star-args notation
        for strOptionName,oOptionValue in options.iteritems():
            self.setOption(strOptionName, oOptionValue)

    def configure(self, **options):
        """
        Alias for L{setOptions}.
        """
        self.setOptions(**options)

    def getOption(self, optionName):
        """
        Returns the value for the given option.

        @param optionName: name of the option to query
        @type optionName: string
        @return: option value (arbitrary object)
        """
        return self.__dctOptions[optionName].value

    def getOptionDefault(self, optionName):
        """
        Returns the default value for the given option.

        @param optionName: name of the option to query
        @type optionName: string
        @return: option value (arbitrary object)
        """
        return self.__dctOptions[optionName].default

    def setOptionDefault(self, optionName, optionDefaultValue):
        """
        Sets a new default for the given option.

        @param optionName: name of the option to modify
        @type optionName: string
        @param optionDefaultValue: new default option value
        @type optionDefaultValue: arbitrary object
        """
        self.__dctOptions[optionName].default = optionDefaultValue

    def setOptionDefaults(self, **options):
        """
        Sets several new default option values in one call.

        @param options: maps option names to their new default values
        @type options: variable-length dictionary
        """
        for strOptionName, oOptionDefaultValue in options.iteritems():
            self.setOptionDefault(strOptionName, oOptionDefaultValue)

    def getOptions(self, optionNames=None):
        """
        Calls .L{getOption} on all the given options. Returns a list of option
        values.

        @param optionNames: sequence of option values. If this is not given,
          the L{getOptionNames} method is called to obtain a list of all
          managed option names
        @type optionNames: list of strings, or C{None}
        @return: list of option values (arbitrary objects)
        """
        if optionNames is None:
            optionNames = self.getOptionNames()
        return [self.getOption(strOptionName) for strOptionName in optionNames]

    def getAllOptions(self):
        """
        Returns the values for all managed options of this instance.

        @return: dictionary mapping managed option names to their values
        """
        return dict([(strName, self.getOption(strName))
                     for strName in self.getOptionNames()])

    def getOptionNames(self):
        """
        Returns the names of all managed options of this instance.

        @return: list of option names
        """
        return self.__class__.getManagedOptionNames() # IGNORE:E1101 (meta class method)

    def hasOption(self, optionName):
        """
        Checks if the given option exists.

        @param optionName: name of the option to query
        @type optionName: string
        """
        return optionName in self.__class__.getManagedOptionNames() # IGNORE:E1101 (meta class method)

    def isOptionSetToDefault(self, optionName):
        """
        Checks if the given option is currently set to its default value.

        @param optionName: name of the option to query
        @type optionName: string
        """
        return self.getOption(optionName) == self.getOptionDefault(optionName)

    def reset(self):
        """
        Sets all options back to their default values.
        """
        for oOption in self.__dctOptions.itervalues():
            oOption.value = oOption.default

    @classmethod
    def getClassOptionNames(cls):
        """
        Returns all option names for this class.

        @return: list of option name strings
        """
        return cls.getManagedOptionNames() # IGNORE:E1101 (meta class method)

    @classmethod
    def getClassOptionDefault(cls, optionName):
        """
        Gets the default value for the given class option.

        @param optionName: name of the class option to query
        @type optionName: string
        @return: option value (arbitrary object)
        """
        oOptionContainer = getattr(cls,
                                   cls.getOptionDeclarationContainerName())
        return oOptionContainer[optionName].default

    @classmethod
    def setClassOptionDefault(cls, optionName, optionDefaultValue):
        """
        Sets a new class default for the given option.

        @param optionName: name of the class option to set
        @type optionName: string
        @param optionDefaultValue: new option default value
        @type optionDefaultValue: arbitrary object
        """
        oOptionContainer = getattr(cls,
                                   cls.getOptionDeclarationContainerName())
        oOptionContainer[optionName].default = optionDefaultValue

    @classmethod
    def setClassOptionDefaults(cls, **options):
        """
        Sets several class option default values in one call.

        @param options: maps class option names to their new default values
        @type options: variable-lenth dictionary
        """
        for strOptionName, oOptionDefaultValue in options.iteritems():
            cls.setClassOptionDefault(strOptionName, oOptionDefaultValue)

    #
    # private methods:
    #

    def __callOptionCallback(self, option):
        if not option.initialized:
            option.initialize(self)
        option.callback(option.value)

#------------------------------------------------------------------------------
# functions:
#

if __name__ == "__main__":
    from pdk.util.pyutils import execMainDocTest
    execMainDocTest()
