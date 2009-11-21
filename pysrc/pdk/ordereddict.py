"""Ordered dictionary

A dictionary that returns keys and values in the order they were added
"""

import copy

from pdk.map import dict_values

class OrderedDict(dict):

    """
    A dictionary that returns keys and values in the order they were added
    """

    def __init__(self,  *tplArgs, **dctValues):
        # required to preserve superclass semantics pylint: disable-msg=W0142
        super(OrderedDict, self).__init__(*tplArgs, **dctValues)
        self.__keysList = super(OrderedDict, self).keys()

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        dup = OrderedDict()
        for k, v in self.iteritems():
            k2 = copy.deepcopy(k, memo)
            v2 = copy.deepcopy(v, memo)
            dup[k2] = v2
        return dup

    def __setitem__(self, key, value):
        if key not in self:
            self.__keysList.append(key)
        super(OrderedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.__keysList.remove(key)

    def __iter__(self):
        return self.__keysList.__iter__()

    def iteritems(self):
        for key in self.__keysList:
            yield (key, self[key])

    def iterkeys(self):
        for key in self.__keysList:
            yield key

    def itervalues(self):
        for key in self.__keysList:
            yield self[key]

    def items(self):
        return zip(list(self.iterkeys()), list(self.itervalues()))

    def keys(self):
        return self.__keysList[:]

    def values(self):
        return dict_values(self, self.__keysList)

    def clear(self):
        super(OrderedDict, self).clear()
        self.__keysList = []

    def copy(self):
        result = OrderedDict()
        for key, value in self.iteritems():
            result[key] = value
        return result

    def deepcopy(self):
        result = OrderedDict()
        for key, value in self.iteritems():
            result[copy.deepcopy(key)] = copy.deepcopy(value)
        return result

    def update(self, *args, **options):
        if len(args) == 1:
            items = args[0]
            if isinstance(items, (list, tuple)):
                keys = [key[0] for key in items]
            else:
                keys = items.keys()
            for key in keys:
                if key not in self:
                    self.__keysList.append(key)
            super(OrderedDict, self).update(items)
        else:
            for key in options:
                if key not in self:
                    self.__keysList.append(key)
            super(OrderedDict, self).update(**options)


    def fromkeys(self, seq, value=None):
        result = OrderedDict()
        for key in seq:
            result[key] = value
        return result

    def setdefault(self, key, value=None):
        if key not in self:
            self.__keysList.append(key)
        return super(OrderedDict, self).setdefault(key, value)

    def pop(self, key, value=None):
        if key in self:
            self.__keysList.remove(key)
        return super(OrderedDict, self).pop(key, value)

    def popitem(self):
        # raise KeyError for dict convenience
        try:
            key = self.__keysList[-1]
        except IndexError:
            raise KeyError('no items left')
        value = self.pop(key)
        return (key, value)

    def sort(self, cmp=None, key=None, reverse=False):
        # keep same paramater names as list.sort pylint: disable-msg=W0622
        self.__keysList.sort(cmp, key, reverse)

    def getat(self, index):
        key = self.__keysList[index]
        return self.__getitem__(key)

    def insertat(self, index, key, value):
        self.__keysList.insert(index, key)
        self.__setitem__(key, value)

    def index(self, key):
        return self.__keysList.index(key)
