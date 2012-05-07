"""
Date/time formatting utilities.

RH 02.2003
"""

__docformat__ = "epytext"

__author__ = "Ralph Heinkel, Michael Held"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['DEFAULT_DATETIME_FORMAT',
           'TimeSlot',
           'TimeInterval',
           'StopWatch',
           'datetime_string_from_ticks',
           'ticks_from_datetime_string',
           'time_string_from_seconds',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import time
import math

#------------------------------------------------------------------------------
# pdk imports:
#

#------------------------------------------------------------------------------
# constants:
#
DEFAULT_DATETIME_FORMAT = '%b %d %Y %H:%M:%S'


#------------------------------------------------------------------------------
# functions:
#

def datetime_string_from_ticks(ticks=None, format=DEFAULT_DATETIME_FORMAT):
    """
    Converts the given ticks to a date time string.

    @param ticks: ticks value to convert. If this is C{None}, returns
      the current time as a string
    @type ticks: float
    @param format: date time format to use
    @type format: string
    @return: formatted date time string (string)
    """
    if ticks is None:
        ticks = time.time()
    the_time = time.localtime(ticks)
    return time.strftime(format, the_time)


def ticks_from_datetime_string(datetime_string=None,
                               format=DEFAULT_DATETIME_FORMAT):
    """
    Converts the given date time string to ticks.

    @param datetime_string: date time string to convert. If this is C{None},
      returns the current time as ticks
    @type datetime_string: string
    @param format: format of the given date time string
    @type format: string
    @return: time in ticks (float)
    """
    if datetime_string:
        # a value of -1 for the last value in the tuple passed to
        # time.mktime() results in the correct daylight savings flag
        # to be filled in:
        local_time = time.strptime(datetime_string, format)[:-1] + (-1,)
        ticks = time.mktime(local_time)
    else:
        ticks = time.time()
    return ticks


def time_string_from_seconds(seconds, sep=',', msec=False):
    """
    Formats a time given in seconds to a string of the format
    "5d, 23h, 3m, 1s"

    More examples: ::

          time_string_from_seconds(59) == "59s"
          time_string_from_seconds(60) == "1m"
          time_string_from_seconds(61) == "1m, 1s"
          time_string_from_seconds(0) == "0s"
          time_string_from_seconds(2.58591, sep=" ", msec=True) == "2s 585ms"

    @param seconds: time value in seconds to convert
    @type seconds: integer or float
    @param sep: separation between time tokens
    @type sep: string
    @param msec: if True the fraction part of `seconds` is interpreted as
      milliseconds, otherwise truncated
    @type msec: boolean
    @return: formatted time string (string)
    """
    # convert to integer to make integer division work below:
    parts = []
    time_in_seconds = int(seconds)
    if time_in_seconds == 0: # special case
        parts.append('0s')
    else:
        units = [('d', 24*3600), ('h', 3600), ('m', 60), ('s', 1)]
        for unit, number_seconds in units:
            part = time_in_seconds // number_seconds
            if part:
                time_in_seconds -= part * number_seconds
                parts.append('%d%s' % (part, unit))
    if msec:
        parts.append("%dms" % (math.modf(seconds)[0] * 1000))
    return sep.join(parts)


class TimeSlot(object):
    """
    Defines a time slot to evaluate if the local time is in or out of this slot

    This is useful for daily or permanent processes to define a time window to
    run within.
    """

    def __init__(self, start_time, stop_time, week_days=None):
        """
        Constructor.

        If L{stop_time} is greater than L{start_time}, the values are
        interpreted as a daytime interval; else, they are interpreted as
        a nighttime interval.

        @param start_time: start time in hours, minutes, and seconds
        @type start_time: 3-tuple of integers
        @param stop_time: stop time in hours, minutes, and seconds
        @type stop_time: 3-tuple of integers
        @param week_days: sequence specifying the days of the week
        @type week_days: list of integers in M{[0..6]}
        """
        if week_days is None:
            week_days = []
        self.__start_time = start_time
        self.__stop_time = stop_time
        self.__week_days = week_days

    #
    # public methods:
    #

    def in_time_slot(self):
        """
        Checks if the local time is within the time slot or not.

        @return: check result (Boolean)
        """
        is_in_time = False
        # for worldwide remote use gmtime() would fit better here
        local_time = time.localtime()
        hour = local_time[3]
        minute = local_time[4]
        second = local_time[5]
        # get weekday, if self.__weekdays is empty, daily is choosen
        week_day = local_time[6]
        current_time = (hour, minute, second)
        if self.__start_time < self.__stop_time:
            # slot in one day
            if (week_day in self.__week_days or self.__week_days == []):
                # weekday in list or daily choosen
                if (current_time >= self.__start_time and
                    current_time <= self.__stop_time):
                    # current time in range of start and stop
                    is_in_time = True
        else:
            # slot between two days ("over night")
            if ((week_day in self.__week_days or self.__week_days==[])
                and current_time >= self.__start_time):
                is_in_time = True
            elif (((week_day-1)%7 in self.__week_days or
                   self.__week_days == []) and
                  current_time <= self.__stop_time):
                is_in_time = True
        return is_in_time

    def get_start(self):
        """
        Returns the start time for this time slot.

        @return: 3-tuple of integers containing the start time in hours,
          minutes, and seconds
        """
        return self.__start_time

    def get_stop(self):
        """
        Returns the stop time for this time slot.

        @return: 3-tuple of integers containing the stop time in hours,
          minutes, and seconds
        """
        return self.__stop_time

    def get_week_days(self):
        """
        Returns the weekdays for this time slot.

        @return: list of integers in M{[0..6]}
        """
        return self.__week_days


class TimeInterval(object):
    """
    Representation of a time intervals given as float of seconds since the
    Epoch, as generated by L{StopWatch}.

    Contains methods to convert a time interval into a human readable format.
    """

    def __init__(self, time_interval):
        self._time_interval = time_interval

    #
    # magic methods:
    #

    def __repr__(self):
        return self._time_interval

    def __str__(self):
        return self.format(msec=True)

    def __div__(self, other):
        return TimeInterval(self._time_interval / other)

    def __idiv__(self, other):
        self._time_interval /= other
        return self

    def __mul__(self, other):
        return TimeInterval(self._time_interval * other)

    def __imul__(self, other):
        self._time_interval *= other
        return self

    def __sub__(self, other):
        if type(other) == self.__class__:
            return TimeInterval(self._time_interval - other.get_interval())
        else:
            return TimeInterval(self._time_interval - other)

    def __isub__(self, other):
        if type(other) == self.__class__:
            self._time_interval -= other.get_interval()
        else:
            self._time_interval -= other
        return self

    def __add__(self, other):
        if type(other) == self.__class__:
            return TimeInterval(self._time_interval + other.get_interval())
        else:
            return TimeInterval(self._time_interval + other)

    def __iadd__(self, other):
        if type(other) == self.__class__:
            self._time_interval += other.get_interval()
        else:
            self._time_interval += other
        return self

    #
    # public methods:
    #

    def as_seconds(self):
        """
        Returns time interval on the basis of seconds.

        @return: 2-tuple of integers containing seconds, and milliseconds
        """
        return (int(self._time_interval),
                self.get_milliseconds(self._time_interval))

    def as_minutes(self):
        """
        Returns time interval on the basis of minutes.

        @return: 3-tuple of integers containing minutes, seconds, and
          milliseconds
        """
        interval = int(self._time_interval)
        return (interval / 60,
                interval % 60,
                self.get_milliseconds(self._time_interval))

    def as_hours(self):
        """
        Returns time interval on the basis of hours.

        @return: 4-tuple of integers containing hours, minutes, seconds,
          and milliseconds
        """
        interval = int(self._time_interval)
        return (interval / 3600,
                interval % 3600 / 60,
                interval % 3600 % 60,
                self.get_milliseconds(self._time_interval))

    def format_as_seconds(self, sep=" "):
        tokens = ["%d%s" % (a, b)
                   for a, b in zip(self.as_seconds(),
                                   ["s", "ms"])
                   ]
        return sep.join(tokens)

    def format_as_minutes(self, sep=" "):
        tokens = ["%d%s" % (a, b)
                   for a, b in zip(self.as_minutes(),
                                  ["m", "s", "ms"])
                   ]
        return sep.join(tokens)

    def format_as_hours(self, sep=" ", format=None):
        if format is not None:
            format_tokens = format.split(":")
        else:
            format_tokens = []
        tokens = ["%d%s" % (a,b)
                   for a, b in zip(self.as_hours(),
                                   ["h", "m", "s", "ms"])
                   if b in format_tokens or len(format_tokens) == 0
                   ]
        return sep.join(tokens)

    def format(self, sep=" ", msec=False):
        """
        Automatic format of the time interval as in L{time_string_from_seconds}.
        """
        return time_string_from_seconds(self._time_interval,
                                        sep=sep, msec=msec)

    def get_interval(self):
        return self._time_interval

    @staticmethod
    def get_milliseconds(time_interval):
        return int((time_interval - math.floor(time_interval)) * 1000)


class StopWatch(object):
    """
    Simple stop watch to hold the start time, provide the current time interval
    (from start to any time point) and the stop time.
    """

    def __init__(self, name=''):
        """
        Start the stop watch.
        """
        self._name = name
        self._start_time = None
        self._stop_time = None
        self.reset()

    def __str__(self):
        return self._name + str(self.current_interval())

    def reset(self):
        """
        Restart the stop watch. Set start time to now and delete the stop
        time (if existed).
        """
        self._start_time = self.get_time()
        self._stop_time = None

#    def resume(self):
#        """
#        """
#        if self._stop_time is None:

    def stop(self):
        """
        Stop the stop watch.
        """
        self._stop_time = self.get_time()

    def current_interval(self):
        """
        Provides the current time interval (from start to now).

        @return: instance of L{TimeInterval}
        """
        return TimeInterval(self.get_time() - self._start_time)

    def stop_interval(self):
        """
        Provides the time interval from start to stop.

        @return: instance of L{TimeInterval}
        @raise ValueError: when stop() was not called before.
        """
        if self._stop_time is None:
            raise ValueError("StopWatch has not been stopped.")
        return TimeInterval(self._stop_time - self._start_time)

    def get_start_time(self):
        """
        @return: start time in seconds (float)
        """
        return self._start_time

    def get_stop_time(self):
        """
        @return: stop time in seconds (float)
        """
        return self._stop_time

    @classmethod
    def get_time(cls):
        return time.time()
