"""
Generalized messaging services.

Allows broadcasting of messages to arbitrary listeners, both locally and
across a network. The implementation is modelled after the Signal/Slot
architecture of the Qt toolkit.

Message IDs are strings (internally, the hash value of each ID string is used
for efficiency).

Also features
 - thread-safety
 - message payloads (arbitrary arguments and options to be passed from
   sender to receiver)
 - automatic de-registration of slots for objects that are destroyed

Notes:
 - call L{newMessageId} or L{newMessageIds} to obtain unique message ID
   strings for a given session
 - call the L{registerSlot} and L{sendSignal} convenience functions for
   simple registration of a slot or sending of a signal
 - if the L{pdk.remote.messaging} module is available, messages can be sent
   across a network (just use C{remote=True} when calling L{registerSlot} and
   L{sendSignal}
 - I{never} unregister a slot in a callback for the same message ID - the
   resulting behavior is undefined
 - in order to pass more than one argument to the receive callback of a slot,
   pass a 2-tuple C{(args,options)} as the message payload data, where C{args}
   is a tuple containing the positional arguments and C{options} is a
   dictionary containing the keyword arguments for the receiving callback

FOG,RH 01.2000,08.2001,10.2002,08.2003
"""

__docformat__ = "epytext"

__author__ = "F Oliver Gathmann"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"


__all__ = ['MSG_OK',
           'MSG_CANCEL',
           'MSG_CLOSE',
           'MSG_KEYPRESSED',
           'MSG_EXIT',
           'MSG_BUSY',
           'MSG_IDLE',
           'Signal',
           'Slot',
           'getRegisteredSlotObjects',
           'isRegisteredSlot',
           'isRegisteredSlotObject',
           'listener',
           'newMessageId',
           'newMessageIds',
           'queueSignal',
           'queueSignalObject',
           'registerSlot',
           'registerSlotObject',
           'sendAnonymousSignal',
           'sendQueuedSignals',
           'sendSignal',
           'sendSignalObject',
           'signaler',
           'unregisterMessageSlots',
           'unregisterObjectSlots',
           'unregisterSlot',
           'unregisterSlotObject',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import logging, \
       sys, \
       threading
from weakref import ref
from types import LambdaType

#------------------------------------------------------------------------------
# pdk imports:
#
try:
    from pdk.remote.messaging import (remotePublish,
                                      remoteSubscribe,
                                      remoteUnsubscribe)
    _REMOTE_MESSAGING_ENABLED = True
except ImportError:
    _REMOTE_MESSAGING_ENABLED = False
from pdk.containers.weaklist import WeakList
from pdk.containers.queues import ClearableQueue
from pdk.proxies import getCallableProxy

#------------------------------------------------------------------------------
# constants:
#

# shared message IDs:
MSG_OK = 'msg_ok'
MSG_CANCEL = 'msg_cancel'
MSG_CLOSE = 'msg_close'
MSG_KEYPRESSED = 'msg_keypressed'
MSG_EXIT = 'msg_exit'
MSG_BUSY = 'msg_busy'
MSG_IDLE = 'msg_idle'

#------------------------------------------------------------------------------
# helper classes:
#

class signalonce(object):
    """
    A decorator class that records the messages sent by the sendSignal function.

    The decorated function's first argument is expected to be a message Id string.
    """

    __messages = []

    def __init__(self, f):
        self.__f = f
        self.__f.reset = signalonce.reset

    def __call__(self, messageIdString, *args, **kwargs):
        if not messageIdString in self.__messages:
            self.__messages.append(messageIdString)
            return self.__f(messageIdString, *args, **kwargs)

    @staticmethod
    def reset(messageIdString=None):
        if messageIdString is None:
            signalonce.__messages = []
        else:
            signalonce.__messages.remove(messageIdString)


#------------------------------------------------------------------------------
# helper functions:
#
def getMessageId(messageIdString):
    """
    Converts the given message ID string to an integer ID.

    @param messageIdString: message ID
    @type messageIdString: string
    """
    return hash(messageIdString)


def sendSignal(messageIdString, signalObject=None, data=None, **options):
    """
    Convenience function to broadcast a message with the given ID string
    See the L{_MessagingRegistry.sendSignal} method for details.

    @param messageIdString: the message ID
    @type messageIdString: string
    @param signalObject: the object sending the signal. If this is left at
      its default value of C{None}, the signal will be anonymous
    @type signalObject: weakly referenceable object object or C{None}
    @param data: the payload data
    @type data: arbitrary object
    @param options: further options to be passed to the L{Signal} constructor
    @type options: variable-length dictionary
    """
    # FIXME: make the signalObject parameter positional once we made the
    #        sendAnonymousSignal function replace the old sendSignal function
    options['signalObject'] = signalObject
    oSignal = Signal(messageIdString, **options)
    sendSignalObject(oSignal, data)


def sendAnonymousSignal(messageIdString, data=None, **options):
    """
    Like L{sendSignal}, but without providing a sending object.
    """
    sendSignal(messageIdString, None, data=data, **options)


def queueSignal(messageIdString, signalObject=None, data=None, **options):
    """
    Convenience function to queue a signal with the given message ID string,
    signal object, and data for later sending. See
    L{_MessagingRegistry.queueSignal} for details.
    """
    # FIXME: make the signalObject parameter positional once we made the
    #        sendAnonymousSignal function replace the old sendSignal function
    options['signalObject'] = signalObject
    oSignal = Signal(messageIdString, **options)
    queueSignalObject(oSignal, data)


@signalonce
def sendSignalOnce(messageIdString, **options):
    """
    This is a decorated send signal function that sends the signal only once.

    It is useful inside threads to send the message only once... especially
    when the receiving main thread has to stop the thread that sended the signal.

    @param options: further options to be passed to L{sendSignal} function
    @type options: variable-length dictionary
    @note: you have to call sendSignalOnce.reset(messageIdString) in order to
      be able to send the same signal again or sendSignalOnce.reset() for all
      sent signals.
    """
    sendSignal(messageIdString, **options)


def registerSlot(messageIdString, slotObject, receiveCallback, **options):
    """
    Convenience function to register a slot for the given object to respond
    to messages with the given ID. See the
    L{_MessagingRegistry.registerSlot} method for details.

    @param messageIdString: message ID
    @type messageIdString: string
    @param slotObject: the object to associate the new slot with
    @type slotObject: weakly referenceable object
    @param receiveCallback: callback to call when a message is received
    @type receiveCallback: callable object
    @param options: further options to be passed to the L{Slot} constructor
    @type options: variable-length dictionary
    """
    oSlot = Slot(messageIdString, slotObject, receiveCallback, **options)
    registerSlotObject(oSlot)


def unregisterSlot(messageIdString, slotObject, domain=None):
    """
    Convenience function to unregister a slot that was previously registered
    for the given object and messaging ID combination. See the
    L{_MessagingRegistry.unregisterSlot} method for details.

    @param messageIdString: message ID
    @type messageIdString: string
    @param slotObject: object that the slot to unregister is associated with
    @type slotObject: arbitrary object
    @param domain: message domain to unregister the slot in
    @type domain: string or C{None} (for the default domain)
    """
    oSlot = Slot(messageIdString, slotObject, domain=domain)
    try:
        unregisterSlotObject(oSlot)
    except ValueError:
        # a ValueError is currently raised if there is no such message slot
        # for this object, e.g. after a slot as already been unregistered
        # auto-magically. This can be safely ignored here.
        pass


def isRegisteredSlot(messageIdString, slotObject, domain=None):
    """
    Convenience function for checking if a slot is registered for the given
    object and messaging ID combination. See the
    L{_MessagingRegistry.isRegisteredSlot} method for details.

    @param messageIdString: message ID
    @type messageIdString: string
    @param slotObject: object that the slot to be checked is associcated with
    @type slotObject: arbitrary object
    @param domain: message domain to check the message ID in
    @type domain: string or C{None} (for the default domain)
    """
    oSlot = Slot(messageIdString, slotObject, domain=domain)
    return isRegisteredSlotObject(oSlot)


def signaler(*messages):
    """
    A decorator that sets a callable as a signaler of messages

    Calls the decorated callable (e.g. function, method) with the given args and
    options and on success sends signals with the given message ids.
    """
    def decorate(target):
        if not callable(target):
            raise TypeError('Decorated object must be callable: %s' % target)
        def handler(*args, **kwargs):
            try:
                oResult = target(*args, **kwargs) # IGNORE:W0142
            except:
                raise
            else:
                for strMessageId in messages:
                    sendSignal(strMessageId)
                return oResult
        return handler

        return callable
    return decorate


def listener(*messages):
    """
    A decorator that sets a class method as the listener of messages

    Sets the special attribute "listenerMessages" to the decorated method as
    a list of messages to listen. This special attribute should to be retrieved
    in the slot object's constructor in order to register new slots.
    """
    def decorate(target):
        if not callable(target):
            raise TypeError('Method must be callable: %s' % target)
        elif not hasattr(target, 'listenerMessages'):
            target.listenerMessages = messages
        else:
            raise ValueError('Method is already a listener: %s' % target)
        return target
    return decorate

#------------------------------------------------------------------------------
# classes:
#


class _Messaging(object):
    """
    Abstract base class for both signals and slots
    """

    __slots__ = ['domain',
                 'messageIdString',
                 'messageId',
                 'messageObjectReference',
                 'remote',
                 'callback',
                 '_Messaging__iHashValue',
                 '__weakref__'
                 ]

    def __init__(self, messageIdString, messageObject, callback,
                 remote=False, domain=None):
        """
        Constructor.

        @param messageIdString: message ID
        @type messageIdString: string
        @param messageObject: object associated with this message, either
          on the sending or on the receiving end
        @type messageObject: weakly referenceable object or C{None}
        @param callback: callback to call when a message is processed
        @type callback: callable or C{None} (see L{Signal} and L{Slot}
          classes)
        @param remote: flag indicating if this should be a remote message
        @type remote: Boolean
        @param domain: message domain
        @type domain: string or C{None} (for the default domain)
        @raise RuntimeError: if remote messaging is not enabled
        """
        # make sure we are set up for remote messaging when this is requested:
        if remote and not _REMOTE_MESSAGING_ENABLED:
            raise RuntimeError('no remote messaging possible (make '
                               'sure the pdk.remote package is '
                               'installed correcty).')
        self.domain = domain
        self.messageIdString = messageIdString
        self.messageId = getMessageId(messageIdString)
        if not messageObject is None:
            self.messageObjectReference = ref(messageObject)
        else:
            self.messageObjectReference = None
        self.remote = remote
        # we build the hash value now; partly for efficiency reasons,
        # partly to still have it available when the object's lifetime might
        # have ended:
        self.__iHashValue = hash(str(hash(messageObject))+messageIdString)
        # process the callback:
        if not callback is None:
            if not callable(callback):
                raise ValueError('invalid message callback object (%s); must '
                                 'be a callable' % callback)
            if type(callback) is LambdaType:
                # if a lambda was passed in, we assume that we should take
                # ownership of it:
                self.callback = callback
            else:
                self.callback = getCallableProxy(callback)
        else:
            self.callback = None

    #
    # magic methods:
    #

    def __hash__(self):
        return self.__iHashValue

    #
    # private methods:
    #

    def __getObject(self):
        return self.messageObjectReference()

    #
    # public properties:
    #

    messageObject = property(__getObject,
                             doc='a reference to the object associated with '
                                 'this message, or C{None}, if none is '
                                 'available')


class Signal(_Messaging):
    """
    Sends a message to an unknown receiver object
    """

    __slots__ = ['isQueued'
                 ]

    def __init__(self, messageIdString, signalObject=None, sendCallback=None,
                 **options):
        """
        Constructor.

        @param messageIdString: message ID
        @type messageIdString: string
        @param signalObject: object sending this signal. If this is left
          at its default C{None} value, this signal is sent anonymously and
          it will not be possible to set up slots listening only to a
          specific sender
        @type signalObject: weakly referenceable object or C{None}
        @param sendCallback: callback to be called when a message is sent to
          generate the message payload; defaults to C{None} (no callback)
        @type sendCallback: callable or C{None}
        """
        self.isQueued = False
        super(Signal, self).__init__(messageIdString, signalObject,
                                     sendCallback, **options)

    #
    # magic methods:
    #

#    def __call__(self):
#        """
#        Called when this signal is called. Calls the send callback if one
#        was defined.
#
#        @return: message payload or C{None}, if no callback was defined
#        """
#        if not self.callback is None:
#            oData = self.callback()
#        else:
#            oData = None
#        return oData

    def __str__(self):
        return 'Signal%s[Message ID string: %s, Object: %s]' % \
               (id(self), self.messageIdString, self.messageObjectReference())


class Slot(_Messaging):
    """
    Receives a message from another object
    """

    __slots__ = ['rank',
                 'signalObjectReference',
                 'threadName',
                 'threadSafe',
                 ]

    def __init__(self, messageIdString, slotObject, receiveCallback=None,
                 rank=None, threadSafe=True, signalObject=None, **options):
        """
        Extends L{_Messaging.__init__}.

        @param messageIdString: the message ID
        @type messageIdString: string
        @param slotObject: object that this slot is associated with
        @type slotObject: weakly referenceable object
        @param receiveCallback: callback to call with the message payload
          data when a message is received; defaults to C{None} (no callback)
        @type receiveCallback: callable or C{None}
        @param rank: determines the processing order in case more than one
          slot is defined for this message ID. Smaller numbers indicate higher
          rank; slots with the same rank are processed in random order
        @type rank: integer
        @param threadSafe: flag indicating if signals sent from another
          thread should I{only} be handled from the thread that this slot
          was registered from
        @type threadSafe: Boolean
        @param options: additional keyword arguments to be passed to the
          base class constructor
        @param signalObject: signalling object to I{exclusively} register
          this slot for
        @type signalObject: hashable object
        @type options: variable-length dictionary
        @note: both the slot object L{slotObject} and the receiving callable
          L{receiveCallback} are only weakly referenced by this slot
        """
        super(Slot, self).__init__(messageIdString, slotObject,
                                   receiveCallback, **options)
        if rank is None:
            rank = sys.maxint
        self.rank = rank
        self.threadName = threading.currentThread().getName()
        self.threadSafe = threadSafe
        if not signalObject is None:
            self.signalObjectReference = ref(signalObject)
        else:
            self.signalObjectReference = None

    #
    # magic methods:
    #

    def __call__(self, data):
        """
        Called when this slot is called. Passes the given message payload
        to the receive callable of the slot.

        @param data: message payload data. If L{data} is a 2-tuple
          C{(args,options)}, where C{args} is a tuple and C{options} is a
          dictionary, the receive callable is called with the C{args} tuple
          as positional and the C{options} tuple as keyword arguments.
        @type data: arbitrary object
        @note: the special convention for 2-tuples being treated as callback
          argument wrappers implies that passing a 2-tuple consisting of a
          tuple and a dictionary B{as is} requires wrapping it in a 1-tuple!
        """
        if not self.callback is None:
            tplArgs, dctOptions = self.__parsePayload(data)
            oResult = self.callback(*tplArgs, **dctOptions)
        else:
            oResult = None
        return oResult

    def __str__(self):
        """
        Called to obtain a string representation of this slot.
        """
        return 'Slot%d[Message ID string: %s, Object: %s, Rank: %s]' % \
               (id(self), self.messageIdString,
                self.messageObjectReference(), self.rank)

    # these magic methods allow sorting a sequence of slots by rank:

    def __lt__(self, other):
        return self.rank < other.rank

    def __le__(self, other):
        return self.rank <= other.rank

    def __eq__(self, other):
        return self.rank == other.rank

    def __ne__(self, other):
        return self.rank != other.rank

    def __gt__(self, other):
        return self.rank > other.rank

    def __ge__(self, other):
        return self.rank >= other.rank

    #
    # private methods:
    #

    def __parsePayload(self, data):
        # note that a 2-tuple containing a tuple as the first and a dictionary
        # as the second element is interpreted as a containing positional and
        # keyword arguments for the callback
        if data is None:
            tplArgs = ()
            dctOptions = {}
        else:
            # try to parse data as (arg tuple, option dict):
            if isinstance(data, tuple):
                try:
                    tplArgs, dctOptions = data
                except ValueError:
                    tIsOk = False
                else:
                    tIsOk = isinstance(tplArgs, tuple) and \
                            isinstance(dctOptions, dict)
            else:
                tIsOk = False
            # any other data are passed in a tuple:
            if not tIsOk:
                tplArgs = (data,)
                dctOptions = {}
        return tplArgs, dctOptions


class MessagingRegistry(object):
    """
    Global registry for setting up slignal/slot connections

    Messages are sent as a signal and received by one or several slots.
    Slots are registered with the L{registerSlot} method.

    When a message is sent (by calling the .L{sendSignal} method or
    indirectly via the L{sendSignal} function)

     1. if no payload (i.e., arbitrary data to be passed to the
        receiving slot(s)) is passed in with the signal, the signal's
        send callback is executed (if specified) to generate the
        payload
     2. the list of slots connected to the signal is traversed
        (in the order of the rank(s) defined by some or all of
        the slots) and not-C{None} client data are passed to the
        receive callback of each slot

    @cvar __dctMessageSlots: dictionary mapping message ID to slots
    @cvar __dctWeakRefSlots: dictionary mapping object weak references to
      slots
    @cvar __dctSlotHashSlots: dictionary mapping slot hash values to slots
    @cvar __dctThreadNameQueue: dictionary mapping thread names to
      signal queues
    @note: only weak references to the messaging objects are kept
    """

    __attributes__ = []

    # the global signal and reference dictionaries:
    __dctMessageSlots = {}
    __dctWeakRefSlots = {}
    __dctSlotHashSlots = {}
    __dctThreadNameQueue = {}

    # the global messaging locks:
    __oSendLock = threading.RLock()
    __oRegisterLock = threading.RLock()

    def __init__(self):
        """
        Constructor.

        @raises NotImplementedError
        """
        raise NotImplementedError('MessagingRegistry can not be '
                                  'instantiated!')

    #
    # public methods:
    #

    @staticmethod
    def sendSignal(signal, data=None):
        """
        Main signalling routine to call all slots associated with the
        given signal.

        By default, slots are processed in a random order, unless one or
        several of the slots registered for L{signal} have a rank.
        If given, the L{data} argument is passed to the registered slots.

        @param signal: signal sending the message
        @type signal: a L{Signal} instance
        @param data: message payload
        @type data: arbitrary object
        """
        oLogger = logging.getLogger('pdk.messaging')
        oLogger.debug('sending signal: %s.%s, remote: %s' %
                      (signal.domain, signal.messageIdString, signal.remote))
        MessagingRegistry.__oSendLock.acquire()
        try:
            if data is None and not signal.callback is None:
                # call the custom message payload producer:
                data = signal.callback()
            if not signal.remote:
                # send the signal locally:
                try:
                    tplKey = (signal.domain, signal.messageId)
                    lstSlots = MessagingRegistry.__dctMessageSlots[tplKey]
                except KeyError:
                    pass
                else:
                    # process the slots (which are sorted by rank) with the
                    # message data as argument:
                    strCallerThreadName = threading.currentThread().getName()
                    oThreadNames = set()
                    tCheckSender = not signal.messageObjectReference is None
                    for oSlot in lstSlots:
                        if tCheckSender and \
                           not oSlot.signalObjectReference is None \
                           and signal.messageObjectReference != oSlot.signalObjectReference:
                            continue
                        if oSlot.threadSafe:
                            if strCallerThreadName == oSlot.threadName:
                                # we are in the right thread - call!
                                oSlot(data)
                            else:
                                # collect the slot thread name for queueing
                                # (if this is not already a queued delivery...)
                                if not signal.isQueued:
                                    oThreadNames.add(oSlot.threadName)
                        elif not signal.isQueued:
                            # don't call thread-unsafe slots multiple times
                            # if this is a queued-signal delivery...
                            oSlot(data)
                    if len(oThreadNames) > 0:
                        MessagingRegistry.__queueSignal(oThreadNames,
                                                        signal, data)
            else:
                # publish the signal remotely, if this was requested (note
                # that this will also be delivered locally!):
                remotePublish(signal.messageIdString, data,
                              domain=signal.domain)
        finally:
            MessagingRegistry.__oSendLock.release()

    @staticmethod
    def registerSlot(slot):
        """
        Registers the given slot to respond to incoming signals.

        @param slot: slot to register
        @type slot: a L{slot} instance
        @note: L{slot} will *replace* a slot with the same message ID and slot
          object registered earlier (i.e., you can`t register two signal
          callbacks for the same ID *and* the same object)
        @note: registered slots are un-registered automatically whenever
          the object that is referenced in the slot is being destroyed (by
          virtue of using a weak reference callback)
        """
        oLogger = logging.getLogger('pdk.messaging')
        oLogger.debug('registering slot: %s.%s, remote: %s' %
                      (slot.domain, slot.messageIdString, slot.remote))
        MessagingRegistry.__oRegisterLock.acquire()
        try:
            if slot.remote:
                remoteSubscribe(slot.messageIdString, domain=slot.domain)
            # register with the (weak) list of slots for the given message ID:
            tplKey = (slot.domain, slot.messageId)
            try:
                lstSlots = MessagingRegistry.__dctMessageSlots[tplKey]
            except KeyError:
                lstSlots = MessagingRegistry.__dctMessageSlots[tplKey] = \
                           WeakList()
            iSlotCount = 0
            while True:
                try:
                    oMsgSlot = lstSlots[iSlotCount]
                except IndexError:
                    lstSlots.append(slot)
                    break
                else:
                    if oMsgSlot.messageObjectReference==slot.messageObjectReference and \
                       oMsgSlot.signalObjectReference==slot.signalObjectReference:
                        lstSlots[iSlotCount] = slot
                        break
                iSlotCount += 1
            lstSlots.sort() # slots are sortable by their rank
            # register with the (weak) list of slots for the given slot object:
            oRef = ref(slot.messageObject,
                       MessagingRegistry.__safelyUnregisterSlotsForObject)
            try:
                lstObjectSlots = MessagingRegistry.__dctWeakRefSlots[oRef]
            except KeyError:
                lstObjectSlots = MessagingRegistry.__dctWeakRefSlots[oRef] = \
                                 WeakList()
            lstObjectSlots.append(slot)
            # finally, store in the (real) dictionary of slots (Note: a
            # simple list of slots will *not* work!)
            MessagingRegistry.__dctSlotHashSlots[id(slot)] = slot
        finally:
            MessagingRegistry.__oRegisterLock.release()

    @staticmethod
    def unregisterSlot(slot):
        """
        Explicitly removes the given registered slot.

        @param slot: slot to unregister
        @type slot: L{Slot} instance
        @raise KeyError: if no slots are registered for the message ID of
          L{slot}
        @raise ValueError: if among the slots for this message ID there is
          no slot for the object associated with L{slot}
        @note: this does not need to be called in the usual case where we
          want a slot to be unregistered when its associated object is
          destroyed (as this is done automagically using a weak reference
          callback); only if the slot object is kept alive, but should no
          longer respond to messages, this method is needed
        """
        oRegisteredSlot = MessagingRegistry.__findSlot(slot)
        if oRegisteredSlot is None:
            raise ValueError('could not find a registered slot for slot '
                             '%s' % slot)
        MessagingRegistry.__unregisterRegisteredSlot(oRegisteredSlot)

    @staticmethod
    def unregisterSlotsForMessageId(messageIdString, domain=None):
        """
        Unregisters all slots registered for the given message ID.

        @param messageIdString: message ID
        @type messageIdString: string
        @param domain: message domain to obtain the registered slots for
        @type domain: string or C{None} (for the default domain)
        """
        tplKey = (domain, getMessageId(messageIdString))
        for oSlot in MessagingRegistry.__dctMessageSlots[tplKey]:
            MessagingRegistry.unregisterSlot(oSlot)

    @staticmethod
    def unregisterSlotsForObject(slotObject):
        """
        Unregisters all slots registered for the given object.

        @param slotObject: the object that all slots should be unregistered
          for
        @type slotObject: arbitrary object
        """
        MessagingRegistry.__unregisterSlotsForObject(ref(slotObject), False)

    @staticmethod
    def isRegisteredSlot(slot):
        """
        Checks whether the given slot is a registered slot.

        @param slot: slot to check
        @type slot: L{Slot} instance
        """
        return not MessagingRegistry.__findSlot(slot) is None

    @staticmethod
    def getRegisteredSlotObjects(messageIdString, domain=None):
        """
        Returns a list of slot objects registered with the given message ID.

        @param messageIdString: message ID
        @type messageIdString: string
        @param domain: message domain to obtain the registered slots for
        @type domain: string or C{None} (for the default domain)
        """
        tplKey = (domain, getMessageId(messageIdString))
        return [oSlot.messageObjectReference()
                for oSlot in MessagingRegistry.__dctMessageSlots[tplKey]]

    @staticmethod
    def queueSignal(signal, data=None):
        """
        Queues the given signal for later delivery with L{sendQueuedSignals}.
        """
        oLogger = logging.getLogger('pdk.messaging')
        oLogger.debug('sending signal: %s.%s, remote: %s' %
                      (signal.domain, signal.messageIdString, signal.remote))
        MessagingRegistry.__oSendLock.acquire()
        try:
            strThreadName = threading.currentThread().getName()
            MessagingRegistry.__queueSignal([strThreadName],
                                            signal, data)
        finally:
            MessagingRegistry.__oSendLock.release()

    @staticmethod
    def sendQueuedSignals():
        """
        Sends queued signals for the calling thread. Call this periodically
        from your thread's main loop (e.g., from the GUI event loop) to
        safely deliver queued messages, or use it in combination with
        L{queueSignal} to delay the delivery of one or several signals.
        """
        strCallerThreadName = threading.currentThread().getName()
        try:
            oQueue = \
                  MessagingRegistry.__dctThreadNameQueue[strCallerThreadName]
        except KeyError:
            pass
        else:
            try:
                lstSignalInfos = oQueue.purge()
            except KeyError:
                pass
            else:
                for oSignal, oData in lstSignalInfos:
                    MessagingRegistry.sendSignal(oSignal, oData)

    #
    # private methods:
    #

    @staticmethod
    def __findSlot(oSlot):
        """
        Finds a registered slot matching the given slot (via a corresponding
        slot object).

        @return: registered L{Slot} instance or C{None}, if no such slot can be
          found.
        """
        lstRegisteredSlots = \
         MessagingRegistry.__dctMessageSlots[(oSlot.domain, oSlot.messageId)]
        oResult = None
        for oRegSlot in lstRegisteredSlots:
            if oRegSlot.messageObjectReference==oSlot.messageObjectReference:
                oResult = oRegSlot
                break
        return oResult

    @staticmethod
    def __unregisterSlotsForObject(oRef, tCatchErrors):
        """
        Unregisters all matching slots (i.e., slots that are weakly referenced
        to the same object as L{oRef}.

        @param oRef: weak reference to the object that all slots should
          be unregistered for
        @type oRef: weak reference type
        @param tCatchErrors: flag indicating that exceptions should be caught
          and logged
        @type tCatchErrors: Boolean
        """
        lstObjectSlots = MessagingRegistry.__dctWeakRefSlots.pop(oRef)
        # we can't just loop over the object slots here since the size of the
        # list is changed during iteration!
        while lstObjectSlots:
            oObjectSlot = lstObjectSlots.pop()
            try:
                MessagingRegistry.__unregisterRegisteredSlot(oObjectSlot)
            except ReferenceError: # the slot has already gone out of scope
                pass
            except:
                if tCatchErrors:
                    from pdk.util.pyutils import getTraceback
                    oLogger = logging.getLogger('pdk.messaging')
                    oLogger.warning('exception during automated slot '
                                    'unregistration \n%s' % getTraceback())
                else:
                    raise

    @staticmethod
    def __safelyUnregisterSlotsForObject(oRef):
        """
        Like L{_MessagingRegistry__unregisterSlotsForObject}, but with a
        catch-all C{except} clause that causes exceptions to be caught and
        logged. See {__unregisterSlotForObject} for parameter details.

        @note: this is the method that is registered as a GC callback with
          weak references to slots
        """
        MessagingRegistry.__unregisterSlotsForObject(oRef, True)

    @staticmethod
    def __unregisterRegisteredSlot(oRegisteredSlot):
        """
        Unregisters the given registered slot.

        @param oRegisteredSlot: the slot to unregister
        @type oRegisteredSlot: L{Slot} instance
        """
        oLogger = logging.getLogger('pdk.messaging')
        oLogger.debug('unregistering slot: %s.%s, remote: %s' %
                      (oRegisteredSlot.domain,
                       oRegisteredSlot.messageIdString,
                       oRegisteredSlot.remote))
        MessagingRegistry.__oRegisterLock.acquire()
        try:
            if oRegisteredSlot.remote:
                # unsubsribe remotely:
                try:
                    # it's possible that an AttributeError is raised when
                    # trying to unregister events during interpreter shutdown
                    # (i.e. exit):
                    remoteUnsubscribe(oRegisteredSlot.messageIdString,
                                      domain=oRegisteredSlot.domain)
                except AttributeError:
                    pass
            # by removing the only real reference, this will also remove the
            # slot from all the message ID and slot object lists that hold a
            # weak reference to it:
            del MessagingRegistry.__dctSlotHashSlots[id(oRegisteredSlot)]
        finally:
            MessagingRegistry.__oRegisterLock.release()

    @staticmethod
    def __queueSignal(lstThreadNames, oSignal, oData):
        """
        Queues the given signal and message payload for later delivery in the
        specified threads.

        @param lstThreadNames: names of the threads the signal should be
          delivered to
        @type lstThreadNames: list of strings
        @param oSignal: signal to queue
        @type oSignal: L{Signal} instance
        @param oData: message payload
        @type oData: arbitrary object
        """
        oSignal.isQueued = True
        dctQueues = MessagingRegistry.__dctThreadNameQueue
        for strThreadName in lstThreadNames:
            try:
                oQueue = dctQueues[strThreadName]
            except KeyError:
                oQueue = dctQueues[strThreadName] = ClearableQueue()
            oQueue.put((oSignal, oData))

# convenience accessors:
sendSignalObject = MessagingRegistry.sendSignal
registerSlotObject = MessagingRegistry.registerSlot
unregisterSlotObject = MessagingRegistry.unregisterSlot
unregisterMessageSlots = MessagingRegistry.unregisterSlotsForMessageId
unregisterObjectSlots = MessagingRegistry.unregisterSlotsForObject
isRegisteredSlotObject = MessagingRegistry.isRegisteredSlot
getRegisteredSlotObjects = MessagingRegistry.getRegisteredSlotObjects
queueSignalObject = MessagingRegistry.queueSignal
sendQueuedSignals = MessagingRegistry.sendQueuedSignals


class MessageIdGenerator(object):
    """
    Unique message ID producer

    @cvar __ID: ID counter, starting at C{1000}
    """

    __ID = 1000

    @staticmethod
    def newId(text=None):
        """
        Generates a message ID that is unique within this process.

        @param text: prefix to use for the message ID
        @type text: string
        @return: message ID string
        """
        MessageIdGenerator.__ID += 1
        return 'msg_%s%d' % (not text is None and text + '_' or '',
                             MessageIdGenerator.__ID)

    @staticmethod
    def newIds(n, text=None):
        """
        Generates the given number of unique message IDs.

        @param n: number of message IDs to create
        @type n: integer
        @param text: prefix to use for the message ID
        @type text: string
        @return: a list of message ID strings
        """
        return [MessageIdGenerator.newId(text) for iStep in range(n)]

# convenience accessors:
newMessageId  = MessageIdGenerator.newId
newMessageIds = MessageIdGenerator.newIds
