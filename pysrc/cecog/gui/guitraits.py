"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

#-------------------------------------------------------------------------------
# standard library imports:
#

#-------------------------------------------------------------------------------
# extension module imports:
#

#-------------------------------------------------------------------------------
# cecog imports:
#
from cecog.traits import traits

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class GuiTrait(object):

    def __init__(self, label, tooltip=None, doc=None, checkable=False):
        self.label = label
        self.tooltip = tooltip
        self.doc = doc
        self.checkable = checkable
        self._widget = None

    def set_widget(self, widget):
        self._widget = widget


class GuiNumberTrait(GuiTrait):

    def __init__(self, label, step=None, tooltip=None, doc=None):
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)
        self.step = step

    def set_value(self, widget, value):
        if self.checkable:
            widget[0].setValue(value[0])
            widget[1].setChecked(value[1])
        else:
            widget.setValue(value)


class IntTrait(traits.IntTrait, GuiNumberTrait):

    def __init__(self, default_value, min_value, max_value, step=None,
                 label=None, tooltip=None, doc=None):
        traits.IntTrait.__init__(self, default_value, min_value, max_value)
        GuiNumberTrait.__init__(self, label, step=step, tooltip=tooltip,
                                doc=doc)


class FloatTrait(traits.FloatTrait, GuiNumberTrait):

    def __init__(self, default_value, min_value, max_value, digits=1, step=None,
                 label=None, tooltip=None, doc=None):
        traits.FloatTrait.__init__(self, default_value, min_value, max_value,
                                   digits=digits)
        GuiNumberTrait.__init__(self, label, step=step, tooltip=tooltip,
                                doc=doc)


class StringTrait(traits.StringTrait, GuiTrait):

    def __init__(self, default_value, max_length, mask=None,
                 label=None, tooltip=None, doc=None, widget_info=None):
        traits.StringTrait.__init__(self, default_value, max_length, mask=mask)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)
        if widget_info is None:
            widget_info = self.STRING_NORMAL
        self.widget_info = widget_info

    def set_value(self, widget, value):
        widget.setToolTip(value)
        widget.setText(value)


class BooleanTrait(traits.BooleanTrait, GuiTrait):

    def __init__(self, default_value, label=None, tooltip=None, doc=None,
                 widget_info=None):
        traits.BooleanTrait.__init__(self, default_value)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)
        if widget_info is None:
            widget_info = self.CHECKBOX
        self.widget_info = widget_info

    def set_value(self, widget, value):
        widget.setChecked(value)


class ListTrait(traits.ListTrait, GuiTrait):

    def __init__(self, default_value, label=None, tooltip=None, doc=None):
        traits.ListTrait.__init__(self, default_value)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)

    def set_value(self, widget, value):
        widget.clear()
        for item in value:
            widget.append(str(item))


class SelectionTrait(traits.SelectionTrait, GuiTrait):

    def __init__(self, default_value, list_data, label=None, tooltip=None, doc=None):
        traits.SelectionTrait.__init__(self, default_value, list_data)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)

    def set_value(self, widget, value):
        widget.setCurrentIndex(self.index(value))


class SelectionTrait2(traits.SelectionTrait2, GuiTrait):

    def __init__(self, default_value, list_data, label=None, tooltip=None, doc=None):
        traits.SelectionTrait2.__init__(self, default_value, list_data)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)

    def set_value(self, widget, value):
        if not value is None:
            index = self.index(value)
            if index is None:
                widget.addItem(str(value))
            else:
                widget.setCurrentIndex(index)

    def set_list_data(self, list_data):
        traits.SelectionTrait2.set_list_data(self, list_data)
        if not self._widget is None:
            current_idx = self._widget.currentIndex()
            for item in sorted(self.list_data):
                if self._widget.findText(item) == -1:
                    self._widget.addItem(item)
            self._widget.setCurrentIndex(current_idx)


class MultiSelectionTrait(traits.MultiSelectionTrait, GuiTrait):

    def __init__(self, default_value, list_data, label=None, tooltip=None, doc=None):
        traits.MultiSelectionTrait.__init__(self, default_value, list_data)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)

    def set_value(self, widget, value):
        widget.clearSelection()
#        for item in value:
#            w_listitem = widget.findItems(str(item), Qt.MatchExactly)
#            #if len(w_listitem) > 0:
#            widget.setCurrentItem(w_listitem[0], QItemSelectionModel.Select)


class DictTrait(traits.DictTrait, GuiTrait):

    def __init__(self, default_value, label=None, tooltip=None, doc=None):
        traits.DictTrait.__init__(self, default_value)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)


#-------------------------------------------------------------------------------
# main:
#

