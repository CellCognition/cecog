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


from cecog.traits import traits


class GuiTrait(object):

    def __init__(self, label, tooltip=None, doc=None, checkable=False):
        self.label = label
        self.tooltip = tooltip
        self.doc = doc
        self.checkable = checkable
        self._widget = None

    def set_widget(self, widget):
        self._widget = widget

    def get_widget(self):
        return self._widget


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

    def set_min_value(self, min_value):
        traits.IntTrait.set_min_value(self, min_value)
        if self._widget is not None:
            self._widget.setMinimum(min_value)

    def set_max_value(self, max_value):
        traits.IntTrait.set_max_value(self, max_value)
        if self._widget is not None:
            self._widget.setMaximum(max_value)



class FloatTrait(traits.FloatTrait, GuiNumberTrait):

    def __init__(self, default_value, min_value, max_value, digits=1, step=None,
                 label=None, tooltip=None, doc=None):
        traits.FloatTrait.__init__(self, default_value, min_value, max_value,
                                   digits=digits)
        GuiNumberTrait.__init__(self, label, step=step, tooltip=tooltip,
                                doc=doc)


class StringTrait(traits.StringTrait, GuiTrait):

    def __init__(self, default_value, max_length=None, mask=None,
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
        self._widget = None
        if widget_info is None:
            widget_info = self.CHECKBOX
        self.widget_info = widget_info

    def set_widget(self, widget):
        self._widget = widget

    def set_value(self, value):
        assert isinstance(value, bool)
        self._widget.setChecked(value)

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

    def __init__(self, default_value, list_data, label=None, tooltip=None,
                 doc=None, update_callback=None):
        traits.SelectionTrait2.__init__(self, default_value, list_data)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)
        self._update_callback = update_callback
        self._previous_value = None

    def set_value(self, widget, value):
        if not value is None:
            index = self.index(value)
            if index is None:
                widget.clear()
                widget.addItem(str(value))
                # FIXME: the Qt interface is not returning an index
                index = widget.count() - 1
            widget.setCurrentIndex(index)

    def set_list_data(self, list_data=None):
        index = None
        if not list_data is None:
            traits.SelectionTrait2.set_list_data(self, list_data)
        list_data = self.list_data

        if self._widget is not None:
            current_idx = self._widget.currentIndex()

            text = str(self._widget.itemText(current_idx))
            self._widget.clear()
            str_data = map(str, list_data)
            self._widget.addItems(str_data)
            if text in str_data:
                index = str_data.index(text)
                self._widget.setCurrentIndex(index)
            else:
                index = None
            return index

    def init(self):
        pass

    def notify(self, name, removed):
        if removed:
            try:
                self.list_data.remove(name)
            except ValueError:
                pass
        else:
            self.list_data.append(name)
        self.set_list_data()

    def on_update_observer(self, value):
        if not self._update_callback is None:
            self._update_callback(value, self._previous_value)
            self._previous_value = value


class DictTrait(traits.DictTrait, GuiTrait):

    def __init__(self, default_value, label=None, tooltip=None, doc=None):
        traits.DictTrait.__init__(self, default_value)
        GuiTrait.__init__(self, label, tooltip=tooltip, doc=doc)
