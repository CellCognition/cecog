#pylint: disable-msg=E1101
# Pylint doesn't understand how options work
"""
Code for Option containers.

FOG 03.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['Option',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
from copy import copy, deepcopy

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.attributemanagers import get_slot_values
from pdk.pyutils import (dump_function,
                         load_function)

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class Option(object):
    """
    Simple container for options
    """

    __slots__ = ['autoInitialize',
                 'callback',
                 'default',
                 'doc',
                 'initialized',
                 'value',
                 'cmdLineInfo'
                 ]

    def __init__(self, default, callback=None,
                 doc=None, cmdLineInfo=None, autoInitialize=True):
        """
        Constructor.

        @param default: the default value for this option
        @type default: arbitrary object
        @param callback: callback to call with the new option value whenever
          the option is set
        @type callback: callable object
        @param doc: description for this option
        @type doc: string
        @param cmdLineInfo: information for exporting this option as a
          command line option
        @type cmdLineInfo: tuple
        @param autoInitialize: flag indicating if this option should be
          auto-initialized at instantiation time
        @type autoInitialize: Boolean
        """
        self.__reset(initialized=False,
                     value=None,
                     default=default,
                     callback=callback,
                     doc=doc,
                     cmdLineInfo=cmdLineInfo,
                     autoInitialize=autoInitialize)

    #
    # public methods:
    #

    def initialize(self, optionHolder):
        """
        Initializes the callback for this option, passing in the option holder
        instance L{optionHolder}. No-op if the callback slot is set to C{None}.

        @param optionHolder: object holding this option
        @type optionHolder: arbitrary object
        """
        oCallback = self.callback
        if not oCallback is None:
            if callable(oCallback):
                oCallbackFunction = lambda value,callback=oCallback: \
                                        callback(optionHolder, value)
            elif isinstance(oCallback, basestring) and \
                 callable(getattr(optionHolder, oCallback)):
                oCallbackFunction = getattr(optionHolder, oCallback)
            else:
                raise ValueError('invalid value for option callback (%s)' %
                                 oCallback)
            self.callback = oCallbackFunction
        self.initialized = True

    def disable(self):
        """
        Irreversibly disables the callback for this option.
        """
        self.callback = None

    #
    # magic methods:
    #

    def __getstate__(self):
        """
        Called to obtain the state for this option.

        Supports dumping the callback function of this option, if defined.
        """
        dctState = get_slot_values(self)
        if not self.callback is None:
            dctState['callbackString'] = dump_function(dctState['callback'])
            del dctState['callback']
        return dctState

    def __setstate__(self, state):
        """
        Called to restore the state of this option from the given
        state dictionary.

        Supports restoring the callback function of this option, if defined.

        @param state: slot name to value mapping
        @type state: dictionary
        """
        try:
            state['callback'] = load_function(state['callbackString'])
        except KeyError:
            pass
        else:
            del state['callbackString']
        self.__reset(**state)

    def __copy__(self):
        """
        Called to obtain a copy of this option.
        """
        return self.__makeCopy(copy(self.default),
                               copy(self.value))

    def __deepcopy__(self, memo):
        """
        Called to obtain a deep copy of this option.
        """
        return self.__makeCopy(deepcopy(self.default, memo),
                               deepcopy(self.value, memo))

    def __repr__(self):
        """
        Called to obtain a string representation of this option.
        """
        return 'Option(%s,callback=%s,doc=%s)' % \
               (self.default,self.callback,self.doc)

    def __setattr__(self, attribute_name, attribute_value):
        """
        Called to set an attribute of this option.

        Protects sensitive attributes from being set more than once.
        """
        tIsSensitive = (attribute_name == 'callback' and self.initialized) or \
                      attribute_name in ('doc','cmdLineInfo')
        if tIsSensitive:
            try:
                tIsExisting = not getattr(self, attribute_name) is None
            except AttributeError:
                tIsExisting = False
            if tIsSensitive and tIsExisting and not attribute_value is None:
                raise AttributeError('trying to set an initialized write-once '
                                     'attribute "%s" in instance "%s" to a '
                                     'non-None value.' % (attribute_name,self))
        super(Option, self).__setattr__(attribute_name, attribute_value)

    #
    # private methods:
    #

    def __reset(self, **options):
        for strSlot in Option.__slots__:
            super(Option, self).__setattr__(strSlot, options[strSlot])

    def __makeCopy(self, default, value):
        oCopy = Option(default,
                       callback=None,
                       doc=self.doc,
                       cmdLineInfo=self.cmdLineInfo,
                       autoInitialize=self.autoInitialize)
        oCopy.callback = self.callback
        oCopy.value = value
        oCopy.initialized = self.initialized
        return oCopy

#------------------------------------------------------------------------------
# functions:
#

