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

__all__ = ['TraitDisplayMixin']

import os
import types
import functools

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from PyQt5 import QtWidgets

from cecog.gui.guitraits import (StringTrait,
                                 IntTrait,
                                 FloatTrait,
                                 BooleanTrait,
                                 SelectionTrait,
                                 SelectionTrait2,
                                 MultiSelectionTrait,
                                 DictTrait,
                                 ListTrait
                                 )

class TraitDisplayMixin(QtWidgets.QFrame):

    DISPLAY_NAME = None

    def __init__(self, settings,
                 parent=None, has_label_link=True, label_click_callback=None,
                 *args, **kw):

        super(TraitDisplayMixin, self).__init__(parent, *args, **kw)
        self._registry = {}
        self._settings = settings
        self._extra_columns = 0
        self._final_handlers = {}
        self._tab_name = None
        self._input_cnt = 0
        self._has_label_link = has_label_link
        self._label_click_callback = label_click_callback

    def get_name(self):
        return self.name if self.DISPLAY_NAME is None \
            else self.DISPLAY_NAME

    def add_handler(self, name, function):
        self._final_handlers[name] = function

    def add_expanding_spacer(self):
        frame = self._get_frame(name=self._tab_name)
        dummy = QWidget(frame)
        dummy.setMinimumSize(0,0)
        dummy.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                        QSizePolicy.Expanding))
        frame.layout().addWidget(dummy, frame._input_cnt, 0)
        frame._input_cnt += 1

    def add_text(self, text_str):
        frame = self._get_frame(name=self._tab_name)
        text = QLabel(text_str)
        frame.layout().addWidget(text, frame._input_cnt, 0,
                                 Qt.AlignRight|Qt.AlignTop)
        frame._input_cnt += 1

    def add_line(self):
        frame = self._get_frame(name=self._tab_name)
        line = QFrame(frame)
        line.setFrameShape(QFrame.HLine)
        frame.layout().addWidget(line, frame._input_cnt, 0, 1, 2)
        frame._input_cnt += 1

    def add_label(self, label, link, margin=3, isHeading=False):
        label = self._create_label(self, label, link)
        label.setMargin(margin)
        if isHeading:
            frame = self._get_frame(name=self._tab_name)
            frame.layout().addWidget(label, frame._input_cnt, 0, 1, 2)
            frame._input_cnt += 1

        return label

    def add_pixmap(self, pixmap, align=Qt.AlignLeft):
        frame = self._get_frame(name=self._tab_name)
        label = QLabel(frame)
        label.setPixmap(pixmap)
        frame.layout().addWidget(label, frame._input_cnt, 0, 1, 2, align)
        frame._input_cnt += 1

    def add_group(self, trait_name, items, layout="grid", link=None, label=None,
                  sublinks=True):
        frame = self._get_frame(self._tab_name)
        frame_layout = frame.layout()

        if trait_name is not None:
            w_input = self.add_input(trait_name)
            trait = self._get_trait(trait_name)
        else:
            w_input = self._create_label(frame, label, link=link)
            frame_layout.addWidget(w_input, frame._input_cnt, 0,
                                   Qt.AlignRight|Qt.AlignTop)
            trait = None

        if len(items) > 0:
            w_group = QGroupBox(frame)
            w_group.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                              QSizePolicy.Fixed))

            w_group._input_cnt = 0
            if layout == 'grid':
                l = QGridLayout(w_group)
            else:
                l = QBoxLayout(QBoxLayout.LeftToRight, w_group)
            l.setContentsMargins(10, 5, 10, 5)
            for info in items:
                grid = None
                alignment = None
                last = False

                if isinstance(info[0], QLabel):
                    w_group.layout().addWidget(info[0], *info[1])

                elif type(info[0]) == types.TupleType:
                    if len(info) >= 2:
                        grid = info[1]
                    if len(info) >= 3:
                        alignment = info[2]
                    w_group2 = QGroupBox(w_group)
                    w_group2._input_cnt = 0
                    #QGridLayout(w_group2)
                    QBoxLayout(QBoxLayout.LeftToRight, w_group2)
                    self.add_input(info[0][0], parent=w_group2, grid=(0,0,1,1),
                                   alignment=alignment, link=sublinks)
                    self.add_input(info[0][1], parent=w_group2, grid=(0,1,1,1),
                                   alignment=alignment, link=sublinks)
                    w_group.layout().addWidget(w_group2, w_group._input_cnt,
                                               1, 1, 1)
                else:
                    trait_name2 = info[0]
                    # add a line
                    if trait_name2 is None:
                        line = QFrame(w_group)
                        line.setFrameShape(QFrame.HLine)
                        grid = info[1]
                        w_group.layout().addWidget(line, *grid)
                    else:
                        if len(info) >= 2:
                            grid = info[1]
                        if len(info) >= 3:
                            alignment = info[2]
                        if len(info) >= 4:
                            last = info[3]
                        self.add_input(trait_name2, parent=w_group, grid=grid,
                                       alignment=alignment, last=last, link=sublinks)

            frame_layout.addWidget(w_group, frame._input_cnt, 1, 1, 1)

            if not trait is None:
                w_group.setEnabled(self._get_value(trait_name))
                handler = lambda x : w_group.setEnabled(w_input.isChecked())
                w_input.toggled.connect(handler)

        frame._input_cnt += 1

    def _create_label(self, parent, label, link=None):
        if link is None:
            link = label
        w_label = ClickableQLabel(parent)

        if self._has_label_link and link is not False:
            w_label.setTextFormat(Qt.AutoText)
#             w_label.setStyleSheet(("*:hover { border:none; background: "
#                                    "#e8ff66; text-decoration: underline;}"))
            w_label.setText(label)
            w_label.setLink(link)

            w_label.setToolTip('Click on the label for help.')
            if self._label_click_callback is None:
                w_label.clicked.connect(self._on_show_help)
#                 w_label.linkActivated.connect(self._on_show_help)
            else:
                w_label.clicked.connect(
                    functools.partial(self._label_click_callback, link))
        else:
            w_label.setText(label)
        return w_label

    def add_input(self, trait_name, parent=None, grid=None, alignment=None,
                  last=False, link=True):
        if parent is None:
            parent = self._get_frame(self._tab_name)

        policy_fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        policy_expanding = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        trait = self._get_trait(trait_name)

        label = trait.label
        if link:
            w_label = self._create_label(parent, label, link=trait_name)
        else:
            w_label = self._create_label(parent, label, link=False)
        w_button = None

        # read value from settings-instance
        value = self._get_value(trait_name)
        handler = lambda name: lambda value: self._set_value(name, value)

        if isinstance(trait, StringTrait):
            w_input = QLineEdit(parent)
            w_input.setMaxLength(trait.max_length)
            w_input.setSizePolicy(policy_expanding)
            w_input.setToolTip(value)
            w_input.setAcceptDrops(True)
            w_input.setDragEnabled(True)

            if not trait.mask is None:
                regexp = QRegExp(trait.mask)
                regexp.setPatternSyntax(QRegExp.RegExp2)
                w_input.setValidator(QRegExpValidator(regexp, w_input))
            trait.set_value(w_input, value)
            handler = lambda name: lambda value: self._set_value(name, value,
                                                                 tooltip=value)

            w_input.textEdited.connect(handler(trait_name))

            if trait.widget_info != StringTrait.STRING_NORMAL and \
                    trait.widget_info != StringTrait.STRING_GRAYED:
                w_button = QPushButton("Browse", parent)
                handler2 = lambda name, mode: lambda: \
                    self._on_browse_name(name, mode)
                w_button.clicked.connect(
                    handler2(trait_name, trait.widget_info))

            if trait.widget_info == StringTrait.STRING_GRAYED:
                w_input.setReadOnly(True)
                w_input.setEnabled(False)

        elif isinstance(trait, IntTrait):
            w_input = QSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            w_input.valueChanged[int].connect(handler(trait_name))
            trait.set_widget(w_input)

        elif isinstance(trait, FloatTrait):
            w_input = QDoubleSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            if not trait.digits is None:
                w_input.setDecimals(trait.digits)
            w_input.valueChanged.connect(handler(trait_name))

        elif isinstance(trait, BooleanTrait):
            if trait.widget_info == BooleanTrait.CHECKBOX:
                w_input = QCheckBox(parent)
            elif trait.widget_info == BooleanTrait.RADIOBUTTON:
                w_input = QRadioButton(parent)
            trait.set_widget(w_input)
            trait.set_value(value)
            handler = lambda n: lambda v: self._set_value(n, trait.convert(v))
            w_input.setSizePolicy(policy_fixed)
            w_input.toggled.connect(handler(trait_name))

        elif isinstance(trait, MultiSelectionTrait):
            w_input = QListWidget(parent)
            w_input.setMaximumHeight(100)
            w_input.setSelectionMode(QListWidget.ExtendedSelection)
            w_input.setSizePolicy(policy_fixed)

            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_selection_changed(n)
            w_input.itemSelectionChanged.connect(handler(trait_name))

        elif isinstance(trait, SelectionTrait):
            w_input = QComboBox(parent)
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            w_input.setSizePolicy(policy_expanding)
            handler = lambda n: lambda v: self._on_current_index(n, v)
            w_input.currentIndexChanged.connect(handler(trait_name))

        elif isinstance(trait, SelectionTrait2):
            w_input = QComboBox(parent)
            w_input.currentIndexChanged[str].connect(trait.on_update_observer)
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_widget(w_input)
            trait.set_value(w_input, value)
            w_input.setSizePolicy(policy_expanding)
            handler = lambda n: lambda v: self._on_current_index(n, v)
            w_input.currentIndexChanged[int].connect(handler(trait_name))


        elif isinstance(trait, DictTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_dict(n)
            w_input.textChanged.connect(handler(trait_name))

        elif isinstance(trait, ListTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_list(n)
            w_input.textChanged.connect(handler(trait_name))

        else:
            raise TypeError("Cannot handle name '%s' with trait '%s'." %
                            (trait_name, trait))

        self._registry[trait_name] = w_input

        if not w_button is None:
            w_button.setSizePolicy(policy_fixed)
            self._extra_columns = 1

        layout = parent.layout()
        if isinstance(layout, QGridLayout):

            if grid is None:
                layout.addWidget(w_label, parent._input_cnt, 0, Qt.AlignRight)
                layout.addWidget(w_input, parent._input_cnt, 1)
                if not w_button is None:
                    layout.addWidget(w_button, parent._input_cnt, 2)
            else:
                layout.addWidget(w_label, grid[0], grid[1]*3, Qt.AlignRight)
                if alignment is None:
                    layout.addWidget(w_input, grid[0], grid[1]*3+1,
                                     grid[2], grid[3])
                else:
                    layout.addWidget(w_input, grid[0], grid[1]*3+1,
                                     grid[2], grid[3], alignment)
                if not w_button is None:
                    layout.addWidget(w_button, grid[0], grid[1]*3+2+grid[3])
                # do not add a spacer if the element is last in a row
                if not last:
                    # layout.setColumnStretch(grid[1]*3+2, 0)
                    layout.addItem(QSpacerItem(0, 0,
                                               QSizePolicy.MinimumExpanding,
                                               QSizePolicy.Fixed),
                                   grid[0], grid[1]*3+2)
        else:
            layout.addWidget(w_label)
            layout.addWidget(w_input)
            if not last:
                layout.addStretch()
            if not w_button is None:
                layout.addWidget(w_button)

        parent._input_cnt += 1
        return w_input

    def update_input(self):
        for name, value in self._settings.items(self.name):
            if name in self._registry:
                w_input = self._registry[name]
                trait = self._get_trait(name)
                if isinstance(trait, BooleanTrait):
                    trait.set_widget(w_input)
                    trait.set_value(value)
                else:
                    trait.set_value(w_input, value)

    def get_widget(self, trait_name):
        return self._registry[trait_name]

    def _get_value(self, name):
        return self._settings.get_value(self.name, name)

    def _set_value(self, name, value, tooltip=None):
        if not tooltip is None:
            widget = self._registry[name]
            widget.setToolTip(str(tooltip))
        self._settings.set(self.name, name, value)

    def _get_trait(self, name):
        return self._settings.get_trait(self.name, name)

    def _on_show_help(self, link):
        self.parent().assistant.show(link)
        self.parent().assistant.raise_()

    def _on_set_radio_button(self, name, value):
        # FIXME: this is somehow hacky. we need to inform all the radio-buttons
        #        if the state of one is changed
        for option in self._settings.options(self.name):
            trait = self._get_trait(option)
            if (isinstance(trait, BooleanTrait) and
                trait.widget_info == BooleanTrait.RADIOBUTTON):
                # print option, name, value
                self._set_value(option, option == name)

    def _on_current_index(self, name, index):
        # FIXME: signals are send during init but registry is not set yet
        if name in self._registry:
            self._set_value(name, str(self._registry[name].currentText()))

    def _on_selection_changed(self, name):
        # FIXME: signals are send during init but registry is not set yet
        if name in self._registry:
            widgets = self._registry[name].selectedItems()
            self._set_value(name, [str(w.text()) for w in widgets])

    def _on_text_to_list(self, name):
        # FIXME: signals are send during init but registry is not set yet
        if name in self._registry:
            text = str(self._registry[name].toPlainText())
            self._set_value(name, [x.strip() for x in text.split('\n')])

    def _on_text_to_dict(self, name):
        # FIXME: signals are send during init but registry is not set yet
        if name in self._registry:
            text = str(self._registry[name].toPlainText())
            value = eval(text)
            assert type(value) == types.DictType
            self._set_value(name, value)

    def _on_browse_name(self, name, mode):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            dir_ = os.path.abspath(str(self._registry[name].text()))

            if mode == StringTrait.STRING_FILE:
                result = QFileDialog.getOpenFileName(self, 'Select a file', dir_)
            else:
                result = QFileDialog.getExistingDirectory(self, \
                           'Select a directory', dir_)

            if result:
                self._registry[name].setText(result)
                self._set_value(name, result)
                # call final handler
                if name in self._final_handlers:
                    self._final_handlers[name]()


class ClickableQLabel(QLabel):

    clicked = pyqtSignal(str)

    def setLink(self, link):
        self.link = link

    def mouseReleaseEvent(self, event):
        self.clicked.emit(self.link)
        return super(ClickableQLabel, self).mouseReleaseEvent(event)
