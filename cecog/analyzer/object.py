"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import
import six

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = ["Region", "ImageObject", "ObjectHolder"]

import copy
import numpy as np
from collections import OrderedDict

class Region(object):

    def __init__(self, oRoi=None, tplCoords=None):
        if oRoi is not None:
            self.upperLeft = (oRoi.upperLeft.x, oRoi.upperLeft.y)
            self.lowerRight = (oRoi.lowerRight.x, oRoi.lowerRight.y)
        elif tplCoords is not None:
            self.upperLeft = (tplCoords[0], tplCoords[1])
            self.lowerRight = (tplCoords[2], tplCoords[3])
        else:
            self.upperLeft = None
            self.lowerRight = None

class Orientation(object):

    def __init__(self, angle=np.nan, eccentricity=np.nan):
        self.angle=angle
        self.eccentricity=eccentricity

class ImageObject(object):

    def __init__(self, oObject=None, iId=None):
        if oObject is not None:
            self.oCenterAbs = (oObject.oCenterAbs.x, oObject.oCenterAbs.y)
            self.oRoi = Region(oRoi=oObject.oRoi)
        else:
            self.oCenterAbs = None
            self.oRoi = None

        self.iLabel = None
        self.dctProb = {}
        self.strClassName = None
        self.strHexColor = None
        self.iId = iId
        self.aFeatures = None
        self.crack_contour = None
        self.file = None
        self.roisize = None
        self.signal = None
        # ORIENTATION TEST: orientation of objects (for tracking) #
        self.orientation = Orientation()

    def squaredMagnitude(self, oObj):
        x = float(oObj.oCenterAbs[0] - self.oCenterAbs[0])
        y = float(oObj.oCenterAbs[1] - self.oCenterAbs[1])
        return x*x + y*y

    def touches_border(self, width, height):
        """Determines if region of interes touch the border given by
        width and height.
        """
        if (self.oRoi.upperLeft[0] > 0 and
            self.oRoi.upperLeft[1] > 0 and
            self.oRoi.lowerRight[0] < width-1 and
            self.oRoi.lowerRight[1] < height-1):
            return False
        else:
            return True

class ObjectHolder(OrderedDict):
    """Container class for image objects. Provides object access by label (key),
    feature access by name and the possibility to concatenate features
    of different object with the  same label.
    """

    def __init__(self, name):
        super(ObjectHolder, self).__init__()
        self.name = name
        self.feature_names = []

    def has_feature(self, name):
        return name in self.feature_names

    @property
    def files(self):
        return [sample.file for sample in list(self.values())]

    @property
    def n_features(self):
        return len(self.feature_names)

    def features_by_name(self, label, feature_names):
        assert isinstance(feature_names, (list, tuple))
        if feature_names is None:
            feature_names = self.feature_names

        idx = [self.feature_names.index(fn) for fn in feature_names]
        return self[label].aFeatures[idx]

    def copy_samples(self, holder, feature_names):
        """Deepcopy image objects from one holder to self. Feature names must be
        provides separatly.
        """
        self.feature_names = feature_names
        for label, sample in six.iteritems(holder):
            self[label] = copy.deepcopy(sample)

    def remove_incomplete(self):
        """Remove samples that do not have the same number of features as
        necessary. This can happen in merged channels. i.e. where features of
        different processing channels are concatenated and the sample was
        skipped in on channel for some reasion.
        """
        removed = list()
        for label, sample in list(self.items()):
            if sample.aFeatures.size != len(self.feature_names):
                del self[label]
                removed.append(label)
        return removed

    def cat_samples(self, holder, feature_names):
        """Concatenate features of image objects. If the dict does not contain
        the image object, it's added automatically.
        """
        self.feature_names.extend(feature_names)

        for label, sample in six.iteritems(holder):
            if label in self:
                sample0 = self[label]
                sample0.aFeatures = np.append(sample0.aFeatures,
                                              np.array(sample.aFeatures))
            else:
                # including the crack_contour
                self[label] = copy.deepcopy(sample)
