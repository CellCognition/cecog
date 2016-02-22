"""
classdefinition.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ('ClassDefinition', 'ClassDefinitionUnsup')


import csv
from os.path import join
from collections import OrderedDict
import matplotlib as mpl
from matplotlib.colors import rgb2hex
from matplotlib.colors import ListedColormap

from cecog.colors import unsupervised_cmap
from .gmm import GaussianMixtureModel


class ClassDefinitionCore(object):

    Definition = 'class_definition.txt'
    Annotations = 'annotations'

    def __init__(self, channels=None, feature_names=None):
        super(ClassDefinitionCore, self).__init__()
        self.feature_names = feature_names
        self.channels = channels
        self.colors = dict()
        self.labels = dict()
        self.names = OrderedDict()

    def __len__(self):
        return len(self.names)

    @property
    def normalize(self):
        """Return a matplotlib normalization instance to the class lables
        corretly mapped to the colors"""
        return mpl.colors.Normalize(vmin=0,
                                    vmax=max(self.names.keys()))

    @property
    def regions(self):
        if len(self.channels) == 1:
            return self.channels.values()[0]
        else:
            return self.channels.values()

    def __iter__(self):
        for label, name in self.names.iteritems():
            yield (name, label, self.colors[name])

    def addClass(self, name, label, color):
        self.names[label] = name
        self.colors[name] = color
        self.labels[name] = label

    def removeClass(self, klass):

        if klass in self.names.values():
            del self.names[self.labels[klass]]
            del self.colors[klass]
            del self.labels[klass]

        elif klass in self.labels.values():
            name = self.name[klass]
            del self.labels[name]
            del self.colors[name]
            del self.names[klass]
        else:
            raise KeyError("No class %s defined" %klass)

    def save2csv(self, path):

        with open(join(path, self.Definition), "wb") as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            writer.writerow(["name", "label", "color"])
            for name in self.names.values():
                label = self.labels[name]
                color = self.colors[name]
                writer.writerow([name, label, color])

    def clear(self):
        self.names.clear()
        self.labels.clear()
        self.colors.clear()


class ClassDefinition(ClassDefinitionCore):
    """Class definition based on a recarray return from a ch5 file"""

    def __init__(self, classes=None, *args, **kw):
        super(ClassDefinition, self).__init__(*args, **kw)

        if classes is not None:
            self._from_recarray(classes)

    def _from_recarray(self, classes):

        dtypes = classes.dtype.names

        if dtypes[0].startswith("name"):
            for (name, label, color) in classes:
                self.labels[name] = label
                self.names[label] = name
                self.colors[name] = str(color)

        else:
            for (label, name, color) in classes:
                self.labels[name] = label
                self.names[label] = name
                self.colors[name] = str(color)

        colors = ["#ffffff"]*(max(self.names.keys())+1)
        for k, v in self.names.iteritems():
            colors[k] = self.colors[v]
        self.colormap = ListedColormap(colors, 'cmap-from-table')


class ClassDefinitionUnsup(ClassDefinitionCore):
    """Unsupervised class definition has hard wired class labels and
    a destinct colormap to make it easy distinguishable from user defined
    class definitions.
    """

    def __init__(self, nclusters, *args, **kw):
        super(ClassDefinitionUnsup, self).__init__(*args, **kw)
        self.nclusters = nclusters
        self.colormap = unsupervised_cmap(self.nclusters)
        # dummy attribute to recyle export function in timeholder
        self.classifier = GaussianMixtureModel()

        for i in xrange(self.nclusters):
            name = "cluster-%d" %i
            self.labels[name] = i
            self.names[i] = name
            self.colors[name] = rgb2hex(self.colormap(i))
