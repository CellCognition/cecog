"""
Utilities for iterator and iterable manipulation.

AB 04.2005
"""

__docformat__ = "epytext"

__author__ = "Aaron Bingham"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['first',
           'rest',
           'all_equal',
           'all_of_type',
           'difference',
           'symmetric_difference',
           'flatten',
           'group',
           'has_duplicates',
           'intersection',
           'is_subset',
           'union',
           'unique',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import itertools

#------------------------------------------------------------------------------
# functions:
#

def first(iterable, default=None):
    """
    Returns the first element of the given iterable, or the given default, if
    the iterable is empty.

    @param iterable: iterable to get the first element from
    @type iterable: iterable object
    @param default: default value to return if L{iterable} is empty
    @type default: arbitrary object
    @return: first element of L{iterable} (arbitrary object), or L{default}
    """
    try:
        oElement = iter(iterable).next()
    except StopIteration:
        oElement = default
    return oElement


def rest(iterable):
    """
    Returns an iterator over all but the first element of the given iterable.

    @param iterable: iterable to skip the first element from
    @type iterable: iterable object
    @return: iterator (L{itertools.islice} instance)
    """
    return itertools.islice(iterable, 1, None)


def all_equal(sequence, value):
    """
    Checks if all elements in the given sequence are equal to the given
    value.

    @return: check result(Boolean)
    """
    for oValue in sequence:
        if not oValue == value:
            return False
    return True


def all_of_type(sysType, sequence):
    """
    Checks if all elements in the given sequence are of the given type.

    @param sysType: type to check for
    @type sysType: type object
    @param sequence: objects to check
    @type sequence: sequence of arbitrary objects
    @return: check result (Boolean)
    """
    for oObj in sequence:
        if not isinstance(oObj, sysType):
            return False
    return True


def unique(seq):
    """
    Returns a list with the duplicates removed from the given sequence
    while preserving the order of the original sequence.

    @param seq: sequence to remove duplicates from
    @type seq: sequence of arbitrary object
    @return: list containing the unique elements from L{seq}
    """
    dctTmp = {}
    return [dctTmp.setdefault(oVal, oVal)
            for oVal in seq if not oVal in dctTmp]


def has_duplicates(seq):
    """
    Checks if the given sequence contains duplicate elements.

    @param seq: sequence to check
    @type seq: sequence of arbitrary objects
    @return: check result (Boolean)
    """
    return len(seq) != len(set(seq))


def intersection(list1, list2):
    """
    returns a list of those elements which are common to both lists. Elements
    are not copied.
    Example: C{intersection(L{5,8,7,6}, L{4,6,8,9})} results in C{L{8,6}}

    @param list1:
    @type list1:
    @param list2:
    @type list2:
    """
    set2 = set(list2)
    return [x for x in list1 if x in set2]


def union(list1, list2):
    """
    returns the union of two lists (adding new elements of list2 to list1).
    Example: C{union(L{2,3,1,1},L{4,3,2})} results in C{L{2,3,1,1,4}}

    @param list1:
    @type list1:
    @param list2:
    @type list2:
    """
    return list1 + difference(list2, list1)


def difference(list1,list2):
    """
    returns the unsymmetric difference of two lists.
    Example: C{difference(L{1,3,1,5,5},L{4,1,9,4,3})}
      results in C{L{5,5}}

    @param list1:
    @type list1:
    @param list2:
    @type list2:
    """
    set2 = set(list2)
    return [x for x in list1 if not x in set2]


def symmetric_difference(list1,list2):
    """
    returns the symmetric difference of two lists.
    Example: C{symmetric_difference(L{1,3,1,5,5},L{4,1,9,4,3})}
      results in C{L{5,5,4,9,4}}

    @param list1:
    @type list1:
    @param list2:
    @type list2:
    """
    return difference(list1,list2) + difference(list2,list1)


def is_subset(list1,list2):
    """
    returns true if list1 is a subset of list2 (orderless)
    Example: C{is_subset(L{1,2,3},L{5,4,3,1,2})} results in C{1}

    @param list1:
    @type list1:
    @param list2:
    @type list2:
    """
    return set(list1).is_subset(set(list2))


def flatten(seq):
    """
    converts the nested sequence L{seq} into a flat sequence (e.g.,
    C{L{(x,),(y,z)}} is converted to C{L{x, y, z}}. Note that each element of
    L{seq} has to be indexable.

    @param seq:
    @type seq:
    """
    return [ x for y in seq for x in y ]


def group(L, n):
    """
    Given a list L of length n*k return a list of k/n n-tuples
    consisting of (LL{0}, LL{1}, ..., LL{n-1}), (LL{n}, LL{n+1}, ...,
    LL{2*n-1}), etc.

    @param L:
    @type L:
    @param n:
    @type n:
    """
    if n <= 0:
        raise ValueError, "n must be positive"
    if len(L) % n != 0:
        raise ValueError, "len(L) must be a multiple of n"
    return [tuple(L[i:i+n]) for i in range(0, len(L), n)]
