"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

import types, pprint

class Trait(object):

    DATATYPE = None

    def __init__(self, default_value):
        self.default_value = default_value

    def convert(self, value):
        if not self.DATATYPE is None and not type(value) == self.DATATYPE:
            return self.DATATYPE(value)
        else:
            return value


class NumberTrait(Trait):

    def __init__(self, default_value, min_value, max_value):
        super(NumberTrait, self).__init__(default_value)
        self.min_value = min_value
        self.max_value = max_value

    def set_min_value(self, min_value):
        self.min_value = min_value

    def set_max_value(self, max_value):
        self.max_value = max_value

class IntTrait(NumberTrait):

    DATATYPE = int


class FloatTrait(NumberTrait):

    DATATYPE = float

    def __init__(self, default_value, min_value, max_value, digits=1):
        super(FloatTrait, self).__init__(default_value, min_value, max_value)
        self.digits = digits


class StringTrait(Trait):

    DATATYPE = str
    STRING_NORMAL = 0
    STRING_PATH = 1
    STRING_FILE = 2
    STRING_GRAYED = 3


    def __init__(self, default_value, max_length=None, mask=None):
        super(StringTrait, self).__init__(default_value)
        self.max_length = max_length
        self.mask = mask


class BooleanTrait(Trait):

    DATATYPE = bool
    CHECKBOX = 0
    RADIOBUTTON = 1

    def convert(self, value):
        if type(value) == self.DATATYPE:
            return value
        else:
            return False if str(value).lower() in ['0', 'false'] else True


class ListTrait(Trait):

    DATATYPE = list

    def convert(self, value):
        if type(value) == self.DATATYPE:
            return value
        else:
            value = eval(value)
            if not type(value) in [types.ListType, types.DictType]:
                value = [value]
            return value


class SelectionTrait(ListTrait):

    def __init__(self, default_value, list_data):
        super(SelectionTrait, self).__init__(default_value)
        self.list_data = list_data

    def index(self, value):
        try:
            idx = self.list_data.index(value)
        except ValueError:
            raise ValueError("The value '%s' is not in the list %s." %
                             (value, self.list_data))
        else:
            return idx

    def length(self):
        return len(self.list_data)

    def convert(self, value):
        return value


class SelectionTrait2(SelectionTrait):

    def index(self, value):
        if value in self.list_data:
            index = self.list_data.index(value)
        else:
            index = None
        return index

    def set_list_data(self, list_data):
        self.list_data = list_data


class DictTrait(ListTrait):

    DATATYPE = dict

    def convert(self, value):
        if type(value) == self.DATATYPE:
            return value
        else:
            value = eval(value)
            if not type(value) == types.DictType:
                value = {}
            return value

        def set_value(self, widget, value):
            widget.setText(pprint.pformat(value, indent=2))
