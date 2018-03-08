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

__all__ = ('ClassDefinition', )


import csv
from os.path import join
import numpy as np
from collections import OrderedDict
import matplotlib as mpl
from matplotlib.colors import rgb2hex
from matplotlib.colors import ListedColormap


class ClassDefinition(object):

    Definition = 'class_definition.txt'
    Annotations = 'annotations'

    def __init__(self, classes=None):
        super(ClassDefinition, self).__init__()
        self.colors = OrderedDict()
        self.labels = OrderedDict()
        self.names = OrderedDict()

        if classes is not None:
            self._from_recarray(classes)

    def __len__(self):
        return len(self.names)

    def __iter__(self):
        for label, name in self.names.iteritems():
            yield (name, label, self.colors[name])

    @classmethod
    def from_txt(cls, file_):
        rec = np.recfromcsv(file_, delimiter="\t", comments="##")
        return cls(rec)

    @property
    def normalize(self):
        """Return a matplotlib normalization instance to the class lables
        corretly mapped to the colors"""
        return mpl.colors.Normalize(vmin=0,
                                    vmax=max(self.names.keys()))

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
            writer.writerow(["label", "name", "color"])
            for name in self.names.values():
                label = self.labels[name]
                color = self.colors[name]
                writer.writerow([label, name, color])

    def clear(self):
        self.names.clear()
        self.labels.clear()
        self.colors.clear()

    def _from_recarray(self, classes):
        # to maintain compatibility with older files

        dtypes = classes.dtype.names

        if dtypes is None:
            for (name, label_, color) in classes[1:, :]:
                label = int(label_)
                self.labels[name] = label
                self.names[label] = name
                self.colors[name] = str(color)

        elif dtypes[0].startswith("name"):
            for (name, label, color) in classes:
                self.labels[name] = label
                self.names[label] = name
                self.colors[name] = str(color)

        elif dtypes[0].startswith("label"):
            for (label, name, color) in classes:
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
