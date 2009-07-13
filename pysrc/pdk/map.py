"""
Utilities for map and dictionary manipulation.

AB 03.2005
"""

__docformat__ = "epytext"

__author__ = "Aaron Bingham, Michael Held"
__date__ = "$Date$"
__revision__ = "$Rev$"
__source__ = "$URL::                                                          $"

__all__ = ['aggregate_dict',
           'dict_append_list',
           'dict_except',
           'dict_not_equal',
           'dict_not_none',
           'dict_subset',
           'dict_values',
           'pivot_dict',
           'pivot_list_dict'
           ]

from pdk.functional import identity

#------------------------------------------------------------------------------
# functions:
#

def dict_subset(dictionary, keys, remove=False):
    """
    Returns a dictionary containing the items from the given dictionary
    which correspond to the given keys.

    @param dictionary: dictionary to process
    @type dictionary: dictionary with arbitrary keys and values
    @param keys: keys defining the subset
    @type keys: sequence of strings
    @param remove: if set, the keys are removed from the source dictionary
    @type remove: Boolean
    @return: new dictionary containing all items with keys in L{keys}
    """
    return dict([(key, val) for (key, val) in dictionary.items()
                 if key in keys and
                 ((remove and dictionary.__delitem__(key)) or True)])


def dict_except(dictionary, keys):
    """
    Returns a dictionary containing the items from the given dictionary
    except the given keys.

    @param dictionary: dictionary to process
    @type dictionary: dictionary with arbitrary keys and values
    @param keys: keys to exclude
    @type keys: sequence of strings
    @return: new dictionary containing all items with keys that are not
      in L{keys}
    """
    return dict([(key, val) for (key, val) in dictionary.items()
                 if key not in keys])


def dict_not_equal(dictionary, value):
    """
    Returns a dictionary containing all items from the given dictionary
    except the ones with a value equal to the given value.

    @param dictionary: dictionary to process
    @type dictionary: dictionary with arbitrary keys and values
    @param value: value to exclude
    @type value: arbitrary object
    @return: new dictionary containing all items with not-C{None} value
    """
    return dict([(key, val) for (key, val) in dictionary.items()
                 if val != value])


def dict_not_none(**dictionary):
    """
    Like L{dict_not_equal}, but does a C{is not None} check.
    """
    # FIXME: do we really need the variable-length dictionary here?
    return dict([(key, val) for (key, val) in dictionary.items()
                 if val is not None])


def dict_values(dictionary, keys):
    """
    Returns all values of L{dictionary} given by and in the order of L{keys}.

    @param dictionary: dictionary to process
    @type dictionary: dictionary with arbitrary keys and values
    @param keys: sequence of keys
    @type keys: sequence
    @return: list
    """
    return [dictionary[key] for key in keys]


def dict_append_list(dictionary, key, value):
    """
    Shortcut to append a value to a list in a dictionary at a certain key.
    The list is created if the key does not exist.

    @param dictionary: dictionary to process
    @type dictionary: dictionary with arbitrary keys and values
    @param key: dictionary key to enter list value
    @type key: any hashable value
    @param value: value to append to list
    @type value: any
    """
    if not key in dictionary:
        dictionary[key] = []
    dictionary[key].append(value)



def aggregate_dict(iterable):
    """
    Returns a dictionary containing the union of keys found in the
    dictionaries in the given iterable.

    If a key appears in more than one of these dictionaries, the value
    associated with one of these is picked arbitrarily.

    @param iterable: iterable to process
    @type iterable: iterable having dictionaries as elements
    @return: new dictionary forming the union of all dictionaries in
      L{iterable}
    """
    aggregate = {}
    for element in iter(iterable):
        aggregate.update(element)
    return aggregate


def pivot_dict(iterable, key, none_mode='ignore', key_transform=None):
    """
    Builds a dictionary using the values of the given key in each of the
    indexable items in the given iterable as keys and the single item for
    each key as values.

    Example: ::

    >>> from pdk.util.map import pivot_dict
    >>> pivot_dict([dict(a=1, b=1), dict(a=2, b=2)], 'a')
    {1: {'a': 1, 'b': 1}, 2: {'a': 2, 'b': 2}}
    >>> pivot_dict([[0, 1], [1, 0]], 0)
    {0: [0, 1], 1: [1, 0]}

    @param iterable: iterable to pivot
    @type iterable: iterable of indexable objects
    @param key: key to index each element in L{iterable} by
    @type key: arbitrary object
    @param none_mode: if set to anything else than "ignore" (the
      default), then C{None} values are included in the resulting pivoted
      dictionary
    @type none_mode: string
    @param key_transform: transforms the value for L{key} obtained from each
      indexable item to a new value to be used as key in the pivoted
      dictionary
    @type key_transform: callable object accepting one value and returning
      one value
    @raise KeyError: if a duplicate key for the pivoted dictionary is
      encountered
    @return: pivoted dictionary containing the items of L{iterable} as
      values and the transformed values obtained from each item as keys
    """
    if key_transform is None:
        key_transform = identity
    pivot = {}
    for item in iter(iterable):
        new_key = item[key]
        if new_key is None and none_mode == 'ignore':
            continue
        if new_key in pivot:
            raise KeyError("duplicate keys: %r" % new_key)
        pivot[key_transform(new_key)] = item
    return pivot


def pivot_list_dict(iterable, key, none_mode='ignore', key_transform=None):
    """
    Builds a dictionary using the values of the given key in each of the
    indexable items in the given iterable as keys and lists of all items
    with the same key as values.

    Similar to L{pivot_dict} (see there for details on parameters), but it
    handles duplicate keys gracefully by building lists of items for each key.

    Example: ::

    >>> from pdk.util.map import pivot_list_dict
    >>> pivot_list_dict([dict(a=1, b=1), dict(a=2, b=2), dict(a=1, b=2)], 'a')
    {1: [{'a': 1, 'b': 1}, {'a': 1, 'b': 2}], 2: [{'a': 2, 'b': 2}]}
    >>> pivot_list_dict([[0, 1], [1, 0], [0, 2]], 0)
    {0: [[0, 1], [0, 2]], 1: [[1, 0]]}

    Given an `iterable`, of indexable items (e.g. maps or sequences),
    return a dictionary where the keys are the values of
    `key_transform(item[key])` and the values are lists of the items
    themselves.  `none_mode` defines how None keys are treated.  If
    `none_mode` is \'ignore\', don\'t include items where the key would
    be `None`.

    @return: pivoted dictionary containing lists of one or more items of
      L{iterable} as values and the transformed values obtained from each
      item as keys
    """
    if key_transform is None:
        key_transform = identity
    list_pivot = {}
    for item in iter(iterable):
        if item[key] is None and none_mode == 'ignore':
            continue
        list_pivot.setdefault(key_transform(item[key]), []).append(item)
    return list_pivot
