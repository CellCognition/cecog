"""
Functional programming utilities.

AB 04.2005
"""

__docformat__ = "epytext"

__author__ = "Aaron Bingham"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['identity',
           ]

#------------------------------------------------------------------------------
# functions:
#

def identity(x):
    """
    Return the single given parameter unchanged.

    @param x: identity parameter
    @type x: arbitrary object
    @return: L{x}
    """
    return x


def memoize(fn):
    """
    Decorator which permenantly memoizes the given function.

    Results of the function are kept for every combination of parameters.
    When a memoized function is repeatedly called with the same parameters,
    the result is returned without re-evaluating the original function.

    Because the results are kept for the lifetime of the process, this
    decorator should only be used for functions where the allowable range
    is limited.

    Can only be used if all arguments to the decorated function are hashable
    and the decorared function is referentially transparent.
    """
    memo = {}
    def memoizer(*args):
        """See memoize for explanation"""
        if args not in memo:
            memo[args] = fn(*args) # legitimate pylint: disable-msg=W0142
        return memo[args]
    return memoizer
