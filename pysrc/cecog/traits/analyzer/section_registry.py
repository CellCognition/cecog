"""
section_registry.py

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from collections import OrderedDict
from cecog.util.pattern import Singleton
from cecog.traits.traits import StringTrait

from cecog.traits.analyzer.objectdetection import SectionObjectdetection
from cecog.traits.analyzer.classification import SectionClassification
from cecog.traits.analyzer.featureextraction import SectionFeatureExtraction
from cecog.traits.analyzer.general import SectionGeneral
from cecog.traits.analyzer.tracking import SectionTracking
from cecog.traits.analyzer.errorcorrection import SectionErrorcorrection
from cecog.traits.analyzer.output import SectionOutput
from cecog.traits.analyzer.processing import SectionProcessing
from cecog.traits.analyzer.cluster import SectionCluster
from cecog.traits.analyzer.postprocessing import SectionPostProcessing
from cecog.traits.analyzer.eventselection import SectionEventSelection


class SectionRegistry(object):
    """SectionRegistry keeps the default values of the settings. Those
    are defined as class attributes, therefore hardwired. SectionRegistry is
    a singleton."""
    # XXX take care of thread safety.

    __metaclass__ = Singleton

    def __init__(self):
        """Initializes setction settings and registers sections in
        the SectionRegistry (singleton)
        """
        self._sections = OrderedDict()
        self.add(SectionGeneral())
        self.add(SectionObjectdetection())
        self.add(SectionFeatureExtraction())
        self.add(SectionClassification())
        self.add(SectionTracking())
        self.add(SectionEventSelection())
        self.add(SectionErrorcorrection())
        self.add(SectionPostProcessing())
        self.add(SectionOutput())
        self.add(SectionProcessing())
        self.add(SectionCluster())

    def add(self, section):
        self._sections[section.SECTION_NAME] = section

    def delete(self, name):
        del self._sections[name]

    def get_section(self, name):
        return self._sections[name]

    def section_names(self):
        return self._sections.keys()

    def get_path_settings(self):
        result = []
        for section_name, section in self._sections.iteritems():
            for trait_name in section.get_trait_names():
                trait = section.get_trait(trait_name)
                if (isinstance(trait, StringTrait) and
                    trait.widget_info in [StringTrait.STRING_FILE,
                                          StringTrait.STRING_PATH]):
                    result.append((section_name, trait_name, trait))
        return result
