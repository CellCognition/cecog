"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['PluginBay', 'PluginParamFrame', 'PluginItem']

import functools

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.Qt import *

from collections import OrderedDict
from cecog.gui.display import TraitDisplayMixin
from cecog.gui.util import question
from cecog.gui.helpbrowser import HelpBrowser

class PluginParamFrame(TraitDisplayMixin):

    label_clicked = pyqtSignal(str)

    def __init__(self, parent, param_manager):
        super(PluginParamFrame, self).__init__(
            param_manager._settings,
            parent, label_click_callback=self._show_help)
        self.name = param_manager._section
        self.param_manager = param_manager
        QGridLayout(self)

    def _show_help(self, trait_name):
        self.label_clicked.emit(trait_name)

    def _get_frame(self, name=None):
        return self

    def add_input(self, param_name, **options):
        if self.param_manager.has_param(param_name):
            trait_name = self.param_manager.get_trait_name(param_name)
        else:
            trait_name = param_name
        return super(PluginParamFrame, self).add_input(trait_name, **options)

    def add_group(self, param_name, items, **options):
        if self.param_manager.has_param(param_name):
            trait_name = self.param_manager.get_trait_name(param_name)
        else:
            trait_name = param_name
        super(PluginParamFrame, self).add_group(trait_name, items, **options)


class PluginDocumentation(QFrame):

    def __init__(self, parent, plugin):
        super(PluginDocumentation, self).__init__(parent)
        self.helpbrowser = HelpBrowser(parent=None)
        self._plugin = plugin

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        help_button = QToolButton(self)
        help_button.setIcon(QIcon(':question_mark'))
        help_button.clicked.connect(self.on_label_clicked)
        layout.addWidget(help_button)

        self._content = plugin.DOC
        if len(self._content) > 0 and self._content[0] == ':':
            self._content = self.helpbrowser.load_qrc_text( \
                'plugins/%s/%s' %(plugin.QRC_PREFIX or '', self._content[1:]))

    def on_label_clicked(self, trait_name=None):
        param_name = self._plugin.param_manager.get_param_name(str(trait_name))
        self.helpbrowser.show( \
            self._plugin.name, html_text=self._content, link=param_name)

    @classmethod
    def has_content(cls, plugin):
        return not plugin.DOC is None and len(plugin.DOC) > 0


class PluginItem(QFrame):

    remove_item = pyqtSignal()

    def __init__(self, parent, plugin, settings):
        super(QFrame, self).__init__(parent)

        layout = QVBoxLayout(self)
        # layout.setContentsMargins(5, 5, 5, 5)

        frame1 = QFrame(self)
        frame1.setStyleSheet("QFrame { background: #CCCCCC; }")

        frame2 = PluginParamFrame(self, plugin.param_manager)
        layout.addWidget(frame1)
        layout.addWidget(frame2)

        layout = QHBoxLayout(frame1)
        #layout.setContentsMargins(5, 5, 5, 5)
        label = QLabel(plugin.LABEL, self)
        label.setStyleSheet("font-weight: bold;")
        txt = QLineEdit(plugin.name, self)
        txt.setReadOnly(True)
        btn = QPushButton('Remove', self)
        btn.clicked.connect(self._on_remove)
        layout.addWidget(label)
        layout.addWidget(txt, 1)

        # add a collapsible documentation to the plugin
        # (image and/or html-compatible text)
        if PluginDocumentation.has_content(plugin):
            doc = PluginDocumentation(self, plugin)
            frame2.label_clicked.connect(doc.on_label_clicked)
            layout.addWidget(doc)

        layout.addWidget(btn)

        requirements = plugin.requirements
        try:
            plugin.render_to_gui(frame2)
        except NotImplementedError:
            for info in plugin.param_manager.get_params():
                if info[0] not in requirements:
                    frame2.add_input(info[1])

        # add requirements in special group
        if len(requirements) > 0:
            frame2.add_group(None,
                             [(name, (idx, 0, 1, 1)) for idx, name in
                              enumerate(requirements)],
                             link='requirements', label='Plugin dependencies')


    def _on_remove(self):
        self.remove_item.emit()


class PluginBay(QFrame):

    def __init__(self, parent, plugin_manager, settings):
        super(QFrame, self).__init__(parent)
        self.plugin_manager = plugin_manager
        self.plugin_manager.register_observer(self)

        self.settings = settings
        self._plugins = OrderedDict()

        self.setStyleSheet(("PluginItem { border: 1px solid black; "
                            "background: white; }"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        frame1 = QFrame(self)
        self._frame2 = QFrame(self)
        layout.addWidget(frame1)
        layout.addSpacing(10)
        layout.addWidget(self._frame2)

        label = QLabel('%s plugins' % plugin_manager.display_name, frame1)
        label.setStyleSheet("font-weight: bold;")
        btn = QPushButton('Add', frame1)
        btn.clicked.connect(self._on_add_plugin)
        self._cb = QComboBox(frame1)
        self._set_plugin_labels()

        layout = QHBoxLayout(frame1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(self._cb, 1)
        layout.addWidget(btn)

        layout = QVBoxLayout(self._frame2)
        layout.setContentsMargins(0, 0, 0, 0)

    def init(self):
        self.reset()
        for plugin_name in self.plugin_manager.get_plugin_names():
            self.add_plugin(plugin_name)

    def notify(self, plugin_name, removed):
        pass

    def _set_plugin_labels(self):
        self._cb.clear()
        for name, label in self.plugin_manager.get_plugin_labels():
            self._cb.addItem(label, name)

    def reset(self):
        self._set_plugin_labels()
        for plugin_name in self._plugins.keys()[:]:
            self.remove_plugin(plugin_name)

    def add_plugin(self, plugin_name):
        plugin = self.plugin_manager.get_plugin_instance(plugin_name)
        item = PluginItem(self._frame2, plugin, self.settings)
        item.remove_item.connect(functools.partial(\
                self._on_remove_plugin, plugin_name))
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
        name_cls = self._cb.itemData(self._cb.currentIndex())
        plugin_name = self.plugin_manager.add_instance(name_cls, self.settings)
        self.add_plugin(plugin_name)

    def _on_remove_plugin(self, plugin_name):
        instance = self.plugin_manager.get_plugin_instance(plugin_name)
        result = False
        n = len(instance.referees)
        if n == 0:
            result = question(None, 'Removing the plugin "%s"' %plugin_name,
                              "Are you sure to remove this plugin?")
        elif n > 0:
            detail = '\n'.join(['%s (%s)' % x[:2] for x in instance.referees])
            result = question(None, 'Removing the plugin "%s"' % plugin_name,
                              ('%d other plugin%s require%s this plugin.'
                               '\n\nAre you sure to remove this plugin?') %
                              (n, 's' if n > 1 else '', 's' if n == 1 else ''),
                              detail=detail, icon=QMessageBox.Warning)
        if result:
            self.remove_plugin(plugin_name)
            self.plugin_manager.remove_instance(plugin_name, self.settings)
