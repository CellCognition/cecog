"""
section_core.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from collections import OrderedDict

class TraitGroup(object):

    def __init__(self, name):
        self.name = name
        self._registry = OrderedDict()

    def register_trait(self, name, trait):
        self._registry[name] = trait

    def unregister_trait(self, name):
        del self._registry[name]

    def get_trait(self, name):
        return self._registry[name]

    def get_trait_names(self):
        return self._registry.keys()


class SectionCore(object):

    SECTION_NAME = None
    OPTIONS = None

    def __init__(self):
        super(SectionCore, self).__init__()
        self._registry = OrderedDict()
        self._traitname_grpname = OrderedDict()

        for group_name, grp_items in self.OPTIONS:
            grp = TraitGroup(group_name)
            self._registry[group_name] = grp
            for trait_name, trait in grp_items:
                trait_name = trait_name.lower()
                self.register_trait(group_name, trait_name, trait)

    def get_group(self, name):
        return self._registry[name]

    def register_trait(self, group_name, trait_name, trait):
        if not group_name in self._registry:
            self._registry[group_name] = TraitGroup(group_name)
        grp = self._registry[group_name]
        self._traitname_grpname[trait_name] = group_name
        grp.register_trait(trait_name, trait)

    def unregister_trait(self, group_name, trait_name):
        grp = self._registry[group_name]
        del self._traitname_grpname[trait_name]
        grp.unregister_trait(trait_name)

    def get_group_names(self):
        return self._registry.keys()

    def get_trait(self, trait_name):
        grp_name = self._traitname_grpname[trait_name]
        grp = self._registry[grp_name]
        return grp.get_trait(trait_name)

    def get_trait_names(self):
        names = []
        for grp in self._registry.values():
            names += grp.get_trait_names()
        return set(names)

    def get_trait_names_for_group(self, name):
        grp = self.get_group(name)
        return grp.get_trait_names()
