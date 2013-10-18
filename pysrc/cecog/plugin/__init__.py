"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__all__ = ['PluginManager', '_Plugin']

import logging
from collections import OrderedDict

from cecog import PLUGIN_MANAGERS
from cecog.gui.guitraits import SelectionTrait2
from cecog.util.decorator import stopwatch

class PluginManager(object):

    PREFIX = 'plugin'
    LABEL = ''

    def __init__(self, display_name, name, section):
        super(PluginManager, self).__init__()
        self.display_name = display_name
        self.name = name
        self.section = section
        self._plugins = OrderedDict()
        self._instances = OrderedDict()
        self._observer = []

    def init_from_settings(self, settings):
        plugin_params = {}
        plugin_cls_names = {}

        for option_name in settings.options(self.section):
            items = option_name.split('__')
            if len(items) > 4 and items[0] == self.PREFIX and items[1] == self.name:
                plugin_cls_name = items[2]
                plugin_name = items[3]
                params = items[4]
                if not plugin_name in plugin_cls_names:
                    plugin_cls_names[plugin_name] = plugin_cls_name
                else:
                    assert plugin_cls_names[plugin_name] == plugin_cls_name
                plugin_params.setdefault(plugin_name, []).append((option_name, params))

        for plugin_name in plugin_params:
            plugin_cls_name = plugin_cls_names[plugin_name]
            plugin_cls = self._plugins[plugin_cls_name]
            param_manager = \
                ParamManager.from_settings(plugin_cls, plugin_name, settings, self, plugin_params[plugin_name])
            instance = plugin_cls(plugin_name, param_manager)
            self._instances[plugin_name] = instance
            self.notify_instance_modified(plugin_name)

        for observer in self._observer:
            observer.init()

    def clear(self):
        for plugin_name, instance in self._instances.iteritems():
            instance.close()
            self.notify_instance_modified(plugin_name, True)
        self._instances.clear()

    def add_instance(self, plugin_cls_name, settings):
        if not plugin_cls_name in self._plugins:
            raise ValueError("Plugin '%s' not registered for '%s'." % (plugin_cls_name, self.name))

        plugin_cls = self._plugins[plugin_cls_name]
        plugin_name = self._get_plugin_name(plugin_cls)
        param_manager = ParamManager(plugin_cls, plugin_name, settings, self)
        instance = plugin_cls(plugin_name, param_manager)
        self._instances[plugin_name] = instance
        self.notify_instance_modified(plugin_name)
        return plugin_name

    def remove_instance(self, plugin_name, settings):
        if not plugin_name in self._instances:
            raise ValueError("Plugin instance '%s' not found for '%s'." % (plugin_name, self.name))

        plugin = self._instances[plugin_name]
        plugin.close()
        del self._instances[plugin_name]
        self.notify_instance_modified(plugin_name, True)

    def notify_instance_modified(self, plugin_name, removed=False):
        for observer in self._observer:
            observer.notify(plugin_name, removed)

    def _get_plugin_name(self, plugin_cls):
        """
        generate new plugin name which is not used yet. starting at the plugin class NAME and appending numbers from
        2 to n, like 'primary', 'primary2', 'primary3'
        """
        cnt = 2
        result = plugin_cls.NAME
        while result in self._instances:
            result = plugin_cls.NAME + str(cnt)
            cnt += 1
        return result

    def get_trait_name_template(self, plugin_cls_name, plugin_name):
        return '__'.join([self.PREFIX, self.name, plugin_cls_name, plugin_name, '%s'])

    def register_plugin(self, plugin_cls):
        self._plugins[plugin_cls.NAME] = plugin_cls

    def register_observer(self, observer):
        self._observer.append(observer)

    def unregister_observer(self, observer):
        self._observer.remove(observer)

    def add_referee_to_instance(self, plugin_name, referee):
        instance = self.get_plugin_instance(plugin_name)
        instance.add_referee(referee)

    def remove_referee_from_instance(self, plugin_name, referee):
        instance = self.get_plugin_instance(plugin_name)
        instance.remove_referee(referee)

    def handle_referee(self, plugin_name_new, plugin_name_old, referee):
        # remove old and add new referee to instance
        #print self.name, plugin_name_new, plugin_name_old, referee
        if plugin_name_old in self._instances:
            self.remove_referee_from_instance(plugin_name_old, referee)
        if plugin_name_new in self._instances:
            self.add_referee_to_instance(plugin_name_new, referee)

    def get_referees_for_instance(self, plugin_name):
        instance = self.get_plugin_instance(plugin_name)
        return instance.referees

    def get_plugin_cls_names(self):
        return self._plugins.keys()

    def get_plugin_labels(self):
        return [(name, cls.LABEL) for name, cls in self._plugins.iteritems()]

    def get_plugin_names(self):
        return sorted(self._instances.keys())

    def get_plugin_cls(self, name):
        return self._plugins[name]

    def get_plugin_instance(self, name):
        return self._instances[name]

    def number_loaded_plugins(self):
        """Return the number of plugins that are invoked if run is executed."""
        return len(self._instances)

    # FIXME **option is dangerous, what if one calls run(foo=bar)
    @stopwatch(level=logging.INFO)
    def run(self, *args, **options):
        results = OrderedDict()
        for instance in self._instances.itervalues():
            inst_args = list(args)
            if not instance.REQUIRES is None:
                if not 'requirements' in options:
                    raise ValueError(("PluginManager(%s).run needs 'requirements' options, "
                                      "because Plugin instances '%s' defines requirements."
                                      % (self.name, instance.name)))
                requirements = options['requirements']
                for idx in range(len(instance.REQUIRES)):
                    value = instance.get_requirement_info(idx)[1]
                    data = requirements[idx].get_requirement(value)
                    inst_args.append(data)
            results[instance.name] = instance.run(*inst_args)
        return results


class ParamManager(object):

    GROUP_NAME = 'plugin'

    def __init__(self, plugin_cls, plugin_name, settings, manager, set_default=True):
        self._settings = settings
        self._section = manager.section
        self._lookup = {}
        self._lookup_reverse = {}
        self._observer_traits = []
        self._plugin_name = plugin_name
        params = plugin_cls.PARAMS
        trait_name_template = manager.get_trait_name_template(plugin_cls.NAME, plugin_name)

        # inject traits controlling plugin requirements dynamically
        foreign_managers = dict([(mngr.name, mngr) for mngr in PLUGIN_MANAGERS])
        if not plugin_cls.REQUIRES is None:
            for idx, require in enumerate(plugin_cls.REQUIRES):
                # get the foreign manager that controls the requirement
                foreign_manager = foreign_managers[require]
                # get the names of plugin instances of the foreign manager
                names = foreign_manager.get_plugin_names()
                # define an update callback which is triggered every time the requirement (plugin instance) is changed
                update_callback = lambda referee: lambda new, old: foreign_manager.handle_referee(new, old, referee)
                # define a new trait for the current requirement
                trait = SelectionTrait2(None if len(names) < 1 else names[0], names, label=foreign_manager.display_name,
                                        update_callback=update_callback((manager.name, plugin_name)))
                # register this trait to the foreign manager which controls the dependency for change notifications
                foreign_manager.register_observer(trait)
                self._observer_traits.append((foreign_manager, trait))
                params.append((plugin_cls._REQUIRE_STR % idx, trait))

        for param_name, trait in params:
            trait_name = trait_name_template % param_name
            self._lookup[param_name] = trait_name
            self._lookup_reverse[trait_name] = param_name
            settings.register_trait(self._section, self.GROUP_NAME, trait_name, trait)
            if set_default or not settings.has_option(self._section, trait_name):
                settings.set(self._section, trait_name, trait.default_value)

    def clear(self):
        for foreign_manager, trait in self._observer_traits:
            # enforce a 'handle_referee' on the foreign_manager by setting the requirement to an empty string
            trait.set_list_data([])
            # unregister the trait as an observer of the foreign_manager
            foreign_manager.unregister_observer(trait)
        for trait_name in self._lookup.itervalues():
            self._settings.unregister_trait(self._section, self.GROUP_NAME, trait_name)

    def has_param(self, param_name):
        return param_name in self._lookup

    def get_trait_name(self, param_name):
        return self._lookup[param_name]

    def get_param_name(self, trait_name):
        return self._lookup_reverse.get(trait_name)

    def get_params(self):
        return self._lookup.items()

    @classmethod
    def from_settings(cls, plugin_cls, plugin_name, settings, manager, param_info):
        """
        register all traits for the given params to the settings manager
        """
        instance = cls(plugin_cls, plugin_name, settings, manager, False)
        for trait_name, param_name in param_info:
            if instance.has_param(param_name):
                value = settings.get_value(manager.section, trait_name)
                settings.set(manager.section, trait_name, value)
            else:
                raise ValueError("Parameter '%s' not specified." % param_name)
        return instance

    def __getitem__(self, param_name):
        return self._settings.get(self._section, self._lookup[param_name])

    def __setitem__(self, param_name, value):
        return self._settings.set(self._section, self._lookup[param_name], value)


class _Plugin(object):

    PARAMS = []
    NAME = None
    DOC = None
    REQUIRES = None
    QRC_PREFIX = None

    # do not overwrite
    _REQUIRE_STR = 'require%02d'

    def __init__(self, name, param_manager):
        self.name = name
        self.param_manager = param_manager
        self._referees = []

    def close(self):
        self.param_manager.clear()

    def add_referee(self, referee):
        self._referees.append(referee)

    def remove_referee(self, referee):
        if referee in self._referees:
            self._referees.remove(referee)

    @property
    def referees(self):
        return self._referees[:]

    @property
    def params(self):
        return self.param_manager

    def get_requirement_info(self, idx):
        name = self._REQUIRE_STR % idx
        return name, self.params[name]

    @property
    def requirements(self):
        result = []
        idx = 0
        while True:
            name = self._REQUIRE_STR % idx
            if self.param_manager.has_param(name):
                result.append(name)
                idx += 1
            else:
                break
        return result

    def run(self, *args, **options):
        """
        Method wrapping the _run method, which is re-implemented in every plugin.
        """
        return self._run(*args, **options)

    def _run(self, *args, **options):
        """
        The actual code of a plugin normally executed by the PluginManager for all instances.
        The parameter and result handling is done by the PluginManager as well.
        """
        raise NotImplementedError('This method must be implemented.')

    def render_to_gui(self, panel):
        """
        Defines how parameters are displayed to the GUI. panel is an instance of PluginParamFrame and implements the
        TraitDisplayMixin, which dynamically displays traits on a frame, which are connected to the settings instance
        (changes are traced and written to the .conf file)

        If not implemented by a plugin the parameters are displayed in one column sorted by appearance in PARAMS
        """
        raise NotImplementedError('This method must be implemented.')
