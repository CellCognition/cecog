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

__all__ = ['TraitDisplayMixin']

#-------------------------------------------------------------------------------
# standard library imports:
#
import os, \
       types, \
       functools

#-------------------------------------------------------------------------------
# extension module imports:
#
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.Qt import *

from pdk.ordereddict import OrderedDict

#-------------------------------------------------------------------------------
# cecog imports:
#
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
from cecog.util.util import convert_package_path
from cecog.gui.util import show_html

#-------------------------------------------------------------------------------
# constants:
#


#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#

class TraitDisplayMixin(object):

    SECTION_NAME = None
    DISPLAY_NAME = None

    def __init__(self, settings):
        self._registry = {}
        self._settings = settings
        self._extra_columns = 0
        self._final_handlers = {}

    def get_name(self):
        return self.SECTION_NAME if self.DISPLAY_NAME is None \
            else self.DISPLAY_NAME

    def add_handler(self, name, function):
        self._final_handlers[name] = function

    def add_plugin_bay(self, plugin_manager, settings):
        frame = self._get_frame(self._tab_name)
        frame_layout = frame.layout()
        frame_layout.addWidget(PluginBay(self, plugin_manager, settings),
                               frame._input_cnt, 0)
        frame._input_cnt += 1

    def add_group(self, trait_name, items, layout="grid",
                  link=None, label=None):
        frame = self._get_frame(self._tab_name)
        frame_layout = frame.layout()

        if not trait_name is None:
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
                if type(info[0]) == types.TupleType:
                    if len(info) >= 2:
                        grid = info[1]
                    if len(info) >= 3:
                        alignment = info[2]
                    w_group2 = QGroupBox(w_group)
                    w_group2._input_cnt = 0
                    #QGridLayout(w_group2)
                    QBoxLayout(QBoxLayout.LeftToRight, w_group2)
                    self.add_input(info[0][0], parent=w_group2, grid=(0,0,1,1),
                                   alignment=alignment)
                    self.add_input(info[0][1], parent=w_group2, grid=(0,1,1,1),
                                   alignment=alignment)
                    w_group.layout().addWidget(w_group2, w_group._input_cnt, 1, 1, 1)
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
                                       alignment=alignment, last=last)

            frame_layout.addWidget(w_group, frame._input_cnt, 1, 1, 1)

            if not trait is None:
                w_group.setEnabled(self._get_value(trait_name))
                handler = lambda x : w_group.setEnabled(w_input.isChecked())
                self.connect(w_input, SIGNAL('toggled(bool)'), handler)

        frame._input_cnt += 1

    def _create_label(self, parent, label, link=None):
        if link is None:
            link = label
        w_label = QLabel(parent)
        w_label.setTextFormat(Qt.AutoText)
        #w_label.setOpenExternalLinks(True)
        w_label.setStyleSheet("*:hover { border:none; background: #e8ff66; text-decoration: underline;}")
        w_label.setText('<style>a { color: black; text-decoration: none;}</style>'
                        '<a href="%s">%s</a>' % (link, label))
        self.connect(w_label, SIGNAL('linkActivated(const QString&)'),
                     self._on_show_help)
        w_label.setSizePolicy(QSizePolicy(QSizePolicy.Fixed,
                                          QSizePolicy.Fixed))
        w_label.setToolTip('Click on the label for help.')
        return w_label

    def add_input(self, trait_name, parent=None, grid=None, alignment=None,
                  last=False):
        if parent is None:
            parent = self._get_frame(self._tab_name)

        policy_fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        policy_expanding = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        trait = self._get_trait(trait_name)

        label = trait.label
        w_label = self._create_label(parent, label, link=trait_name)
        w_button = None
        #w_doc = None
        #w_label.setMinimumWidth(width)

        value = self._get_value(trait_name)

        handler = lambda name: lambda value: self._set_value(name, value)

        if isinstance(trait, StringTrait):
            w_input = QLineEdit(parent)
            w_input.setMaxLength(trait.max_length)
            w_input.setSizePolicy(policy_expanding)
            w_input.setToolTip(value)
            if not trait.mask is None:
                regexp = QRegExp(trait.mask)
                regexp.setPatternSyntax(QRegExp.RegExp2)
                w_input.setValidator(QRegExpValidator(regexp, w_input))
            trait.set_value(w_input, value)
            handler = lambda name: lambda value: self._set_value(name, value,
                                                                 tooltip=value)
            self.connect(w_input, SIGNAL('textEdited(QString)'),
                         handler(trait_name))

            if trait.widget_info != StringTrait.STRING_NORMAL:
                w_button = QPushButton("Browse", parent)
                handler2 = lambda name, mode: lambda: \
                    self._on_browse_name(name, mode)
                self.connect(w_button, SIGNAL('clicked()'),
                             handler2(trait_name, trait.widget_info))

        elif isinstance(trait, IntTrait):
            w_input = QSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            self.connect(w_input, SIGNAL('valueChanged(int)'),
                         handler(trait_name))
#            w_input = CecogSpinBox(parent, trait.checkable)
#            w_input.setRange(trait.min_value, trait.max_value)
#            w_input.setSizePolicy(policy_fixed)
#            trait.set_value(w_input, value)
#            if not trait.step is None:
#                w_input.setSingleStep(trait.step)
#            self.connect(w_input.widget, SIGNAL('valueChanged(int)'), handler(name))

        elif isinstance(trait, FloatTrait):
            w_input = QDoubleSpinBox(parent)
            w_input.setRange(trait.min_value, trait.max_value)
            w_input.setSizePolicy(policy_fixed)
            trait.set_value(w_input, value)
            if not trait.step is None:
                w_input.setSingleStep(trait.step)
            if not trait.digits is None:
                w_input.setDecimals(trait.digits)
            self.connect(w_input, SIGNAL('valueChanged(double)'),
                         handler(trait_name))

        elif isinstance(trait, BooleanTrait):
            if trait.widget_info == BooleanTrait.CHECKBOX:
                w_input = QCheckBox(parent)
            elif trait.widget_info == BooleanTrait.RADIOBUTTON:
                w_input = QRadioButton(parent)
            trait.set_value(w_input, value)
            handler = lambda n: lambda v: self._set_value(n, trait.convert(v))
            w_input.setSizePolicy(policy_fixed)
            self.connect(w_input, SIGNAL('toggled(bool)'),
                         handler(trait_name))

        elif isinstance(trait, MultiSelectionTrait):
            w_input = QListWidget(parent)
            w_input.setMaximumHeight(100)
            w_input.setSelectionMode(QListWidget.ExtendedSelection)
            w_input.setSizePolicy(policy_fixed)
            #print "moo1", value
            #value = trait.convert(value)
            #print "moo2", value
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_selection_changed(n)
            self.connect(w_input, SIGNAL('itemSelectionChanged()'),
                         handler(trait_name))

        elif isinstance(trait, SelectionTrait):
            w_input = QComboBox(parent)
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_value(w_input, value)
            w_input.setSizePolicy(policy_fixed)
            handler = lambda n: lambda v: self._on_current_index(n, v)
            self.connect(w_input, SIGNAL('currentIndexChanged(int)'),
                         handler(trait_name))

        elif isinstance(trait, SelectionTrait2):
            w_input = QComboBox(parent)
            for item in trait.list_data:
                w_input.addItem(str(item))
            trait.set_widget(w_input)
            trait.set_value(w_input, value)
            w_input.setSizePolicy(policy_fixed)
            handler = lambda n: lambda v: self._on_current_index(n, v)
            self.connect(w_input, SIGNAL('currentIndexChanged(int)'),
                         handler(trait_name))

        elif isinstance(trait, DictTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_dict(n)
            self.connect(w_input, SIGNAL('textChanged()'),
                         handler(trait_name))

        elif isinstance(trait, ListTrait):
            w_input = QTextEdit(parent)
            w_input.setMaximumHeight(100)
            w_input.setSizePolicy(policy_expanding)
            #print value
            #value = trait.convert(value)
            #print value
            trait.set_value(w_input, value)
            handler = lambda n: lambda: self._on_text_to_list(n)
            self.connect(w_input, SIGNAL('textChanged()'),
                         handler(trait_name))

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
                #if not w_doc is None:
                #    layout.addWidget(w_doc, parent._input_cnt, 1)

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
                    #layout.setColumnStretch(grid[1]*3+2, 0)
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
        #if self._settings.has_section(self.SECTION):
        for name, value in self._settings.items(self.SECTION_NAME):
            #print self.SECTION, name, name in self._registry
            if name in self._registry:
                w_input = self._registry[name]
                trait = self._get_trait(name)
                #print '    ', name, value
                trait.set_value(w_input, value)

    def get_widget(self, trait_name):
        return self._registry[trait_name]

    # convenience methods

    def _get_value(self, name):
        return self._settings.get_value(self.SECTION_NAME, name)

    def _set_value(self, name, value, tooltip=None):
        if not tooltip is None:
            widget = self._registry[name]
            widget.setToolTip(str(tooltip))
        self._settings.set(self.SECTION_NAME, name, value)

    def _get_trait(self, name):
        return self._settings.get_trait(self.SECTION_NAME, name)


    # event methods

    def _on_show_help(self, link):
        print self.SECTION_NAME, link
        show_html(self.SECTION_NAME, link=link,
                  header='_header', footer='_footer')


    def _on_set_radio_button(self, name, value):
        # FIXME: this is somehow hacky. we need to inform all the radio-buttons
        #        if the state of one is changed
        for option in self._settings.options(self.SECTION_NAME):
            trait = self._get_trait(option)
            if (isinstance(trait, BooleanTrait) and
                trait.widget_info == BooleanTrait.RADIOBUTTON):
                #print option, name, value
                self._set_value(option, option == name)

    def _on_browse_name(self, name, mode):
        # FIXME: signals are send during init were registry is not set yet
        if name in self._registry:
            input = convert_package_path(str(self._registry[name].text()))
            dir = os.path.abspath(input)
            if mode == StringTrait.STRING_FILE:
                result = QFileDialog.getOpenFileName(self, 'Select a file', dir)
            else:
                result = QFileDialog.getExistingDirectory(self, 'Select a directory', dir)

            if result:
                self._registry[name].setText(result)
                self._set_value(name, result)
                # call final handler
                if name in self._final_handlers:
                    self._final_handlers[name]()

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


class PluginParamFrame(QFrame, TraitDisplayMixin):

    def __init__(self, parent, settings, section):
        QFrame.__init__(self, parent)
        self._tab_name = None
        self._input_cnt = 0
        TraitDisplayMixin.__init__(self, settings)
        self.SECTION_NAME = section
        QGridLayout(self)

    def _get_frame(self, name=None):
        return self



class PluginItem(QFrame):

    remove_item = pyqtSignal()

    def __init__(self, parent, name, plugin, settings):
        super(QFrame, self).__init__(parent)
        self.name = name

        layout = QHBoxLayout(self)

        frame1 = QFrame(self)
        frame2 = PluginParamFrame(self, settings, plugin.param_manager._section)
        layout.addWidget(frame1)
        layout.addWidget(frame2)

        layout1 = QVBoxLayout(frame1)
        label = QLabel(name, self)
        btn = QPushButton('Remove', self)
        btn.clicked.connect(self._on_remove)
        layout1.addWidget(label)
        layout1.addWidget(btn)

        for param_name, trait_name in plugin.param_manager.get_params():
            frame2.add_input(trait_name)

    def _on_remove(self):
        self.remove_item.emit()


class PluginBay(QFrame):

    def __init__(self, parent, plugin_manager, settings):
        super(QFrame, self).__init__(parent)
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_observer(self)

        self.settings = settings
        self._plugins = OrderedDict()

        layout = QVBoxLayout(self)
        frame1 = QFrame(self)
        self._frame2 = QFrame(self)
        layout.addWidget(frame1)
        layout.addWidget(self._frame2)

        btn = QPushButton('Add', frame1)
        btn.clicked.connect(self._on_add_plugin)
        self._cb = QComboBox(frame1)
        self._cb.addItems(self.plugin_manager.get_plugin_cls_names())

        layout1 = QHBoxLayout(frame1)
        layout1.addWidget(self._cb)
        layout1.addWidget(btn)

        QVBoxLayout(self._frame2)

    def init(self):
        self.reset()
        for plugin_name in self.plugin_manager.get_plugin_names():
            self.add_plugin(plugin_name)

    def reset(self):
        self._cb.clear()
        self._cb.addItems(self.plugin_manager.get_plugin_cls_names())
        for plugin_name in self._plugins.keys():
            self.remove_plugin(plugin_name)

    def add_plugin(self, plugin_name):
        plugin = self.plugin_manager.get_plugin_instance(plugin_name)
        item = PluginItem(self._frame2, plugin_name, plugin, self.settings)
        item.remove_item.connect(functools.partial(self._on_remove_plugin, plugin_name))
        layout = self._frame2.layout()
        layout.insertWidget(0, item)
        self._plugins[plugin_name] = item

    def remove_plugin(self, plugin_name):
        layout = self._frame2.layout()
        item = self._plugins[plugin_name]
        item.close()
        layout.removeWidget(item)
        del self._plugins[plugin_name]

    def _on_add_plugin(self):
        name_cls = str(self._cb.currentText())
        plugin_name = self.plugin_manager.add_instance(name_cls, self.settings)
        self.add_plugin(plugin_name)

    def _on_remove_plugin(self, plugin_name):
        self.remove_plugin(plugin_name)
        self.plugin_manager.remove_instance(plugin_name, self.settings)

