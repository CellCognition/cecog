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


import os
from os.path import join,  isfile

from svm import svm_model
from cecog.learning.util import Normalizer
from cecog.util.logger import LoggerObject


class GaussianMixtureModel(object):
    """Dummy class for hdf5 export."""

    # need only these two class attributes
    NAME = "sklearn.mixture.GMM"
    METHOD = "Gaussian Mixture Model"


class LibSvmClassifier(LoggerObject):

    NAME = 'libSVM'
    METHOD = 'Support Vector Machine'

    def __init__(self, data_dir, svm_prefix, has_zero_insert):
        super(LibSvmClassifier, self).__init__()
        self.data_dir = data_dir
        self.svm_prefix = svm_prefix
        self.has_zero_insert = has_zero_insert


        model_path = join(data_dir, svm_prefix+'.model')
        if os.path.isfile(model_path):
            self.logger.info("Loading libSVM model file '%s'." %model_path)
            self.svm_model = svm_model(model_path)
        else:
            raise IOError("libSVM model file '%s' not found!" %model_path)

        range_file = join(data_dir, svm_prefix+'.range')
        if isfile(range_file):
            self.logger.info("Loading libSVM range file '%s'." %range_file)
            self.normalizer = Normalizer(range_file)
        else:
            raise IOError("libSVM range file '%s' not found!" %range_file)

        self.probability = True if self.svm_model.probability == 1 else False

    def normalize(self, sample_feature_data):
        return self.normalizer.scale(sample_feature_data)

    def __call__(self, sample_feature_data):
        features_scaled = self.normalize(sample_feature_data)
        if self.has_zero_insert:
            features_scaled = [0] + features_scaled
        if self.probability:
            label, prob = self.svm_model.predict_probability(features_scaled)
            label = int(label)
        else:
            label = self.svm_model.predict(features_scaled)
            label = int(label)
            prob = {label: 1.0}
        return label, prob
