import os, sys, time, re, numpy

import scripts.EMBL.feature_projection.lda
reload(scripts.EMBL.feature_projection.lda)

import scripts.EMBL.plotter.colors

from scripts.EMBL.feature_projection.lda import *
from scripts.EMBL.plotter.colors import *
from scripts.EMBL.plotter.stats import *

from scripts.EMBL.settings import Settings

import scikits.learn.lda

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc
# if rpy2 is going to be used: export PATH=/Users/twalter/software/R/R.framework/Resources/bin:${PATH}
# This is necessary, because without that he finds the wrong R executable.
# st = scripts.EMBL.projects.feature_projection_study.Study("/Users/twalter/workspace/cecog/pysrc/scripts/EMBL/settings_files/settings_lda_study_lamin.py")
#
class Study(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.settings = settings
        elif not settings_filename is None:
            self.settings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        self.lda = None
        self.ts = TrainingSet()

        for folder in self.settings.makefolders:
            if not os.path.exists(folder):
                os.makedirs(folder)

    # import the full training data (all classes)
    def importTrainingData(self, filename):
        self.ts.readArffFile(filename)
        X, y = self.ts(filename,
                       features_remove=self.settings.FEATURES_REMOVE,
                       correlation_threshold=0.99,
                       phenoClasses=None,
                       normalization_method='z',
                       recode_dictionary=None)

        XF = numpy.float64(X)
        return XF, y

    # import training data from 2 classes.
    def import2ClassTrainingData(self, filename):
        self.ts.readArffFile(filename)
        X, y = self.ts(filename,
                       features_remove=self.settings.FEATURES_REMOVE,
                       correlation_threshold=0.99,
                       phenoClasses=self.settings.PHENOCLASSES_FOR_TRAINING,
                       normalization_method='z',
                       recode_dictionary=None)

        XF = numpy.float64(X)
        return XF, y

    # this is only for comparison of different classifiers.
    # here, the classes have to be recoded, because mlpy requires
    # the classes to be [-1, 1].
    def importTrainingDataForComparison(self, filename):
        self.ts.readArffFile(filename)

        recode_dict = self.ts.recodeClasses(self.settings.PHENOCLASSES_FOR_TRAINING, [-1, 1])
        X, y = self.ts(filename,
                       features_remove=self.settings.FEATURES_REMOVE,
                       correlation_threshold=0.99,
                       phenoClasses=self.settings.PHENOCLASSES_FOR_TRAINING,
                       normalization_method='z',
                       recode_dictionary=recode_dict)

        XF = numpy.float64(X)
        return XF, y

    def getTrainingDataSubset(self, phenoClasses):
        X, y = self.ts.extractData(phenoClasses=phenoClasses)
        return X, y

    def calcProjectionDistributionForTrainingSet(self, classifier_name):

        # all classes
        X, y = self.importTrainingData(self.settings.classifier_names[classifier_name])

        # all classes
        Xtrain, ytrain = self.getTrainingDataSubset(self.settings.PHENOCLASSES_FOR_TRAINING)
        #pheno_class1 = self.settings.PHENOCLASSES_FOR_TRAINING[0]
        #ytrain[ytrain==self.ts._ar.dctClassLabels[self.settings.PHENOCLASSES_FOR_TRAINING[0]]] = -1
        #ytrain[ytrain==self.ts._ar.dctClassLabels[self.settings.PHENOCLASSES_FOR_TRAINING[1]]] =  1
        Xtrain = numpy.float64(Xtrain)

        # learning the classifier
        self.lda = scikits.learn.lda.LDA()
        self.lda.fit(Xtrain,ytrain)
        #discriminant_values = self.lda.decision_function(X)

        weights = numpy.transpose(self.lda.scaling)[0]

        plotDir = os.path.join(self.settings.plotDir, 'distribution_projected_values')
        if not os.path.exists(plotDir):
            os.makedirs(plotDir)

        filename = os.path.join(plotDir, 'projection_distribution_%s.png' % classifier_name)
        projected = numpy.dot(X, weights)
        #all_target_vals = self.ts.getClasses()
        vals = {}
        for phenoClass in self.settings.PHENOCLASSES:
            Xsubset, ysubset = self.getTrainingDataSubset([phenoClass])
            vals[phenoClass] = numpy.dot(Xsubset, weights)

        colorvec = [self.settings.colordict[phenoClass]
                    for phenoClass in self.settings.PHENOCLASSES]
        histoplotter = scripts.EMBL.plotter.stats.Histogram()
        histoplotter([vals[phenoClass] for phenoClass in self.settings.PHENOCLASSES],
                     filename, side_by_side=False,
                     title="histogram of projected values (LDA) : %s" % classifier_name,
                     xlabel='projection value', colorvec=colorvec, bins=60)
        
        return

    def compareLDAImplementations(self, X, y):
        predictors = [mlpy.Srda(),
                      mlpy.Fda(),
                      mlpy.Dlda(),
                      mlpy.Pda(),
                      ScikitLDA(),
                      ]
        predictor_names = ['srda',
                           'fda',
                           'dlda',
                           'pda',
                           'scikitlda']
        for pred, predname in zip(predictors, predictor_names):
            self.compareDiscriminantValuesWithProjections(X, y, pred, predname)

        return

    def compareDiscriminantValuesWithProjections(self, X, y,
                                                 predictor, predictor_name):
        w = predictor.weights(X, y)
        predictions = predictor.predict(X)
        realvals = predictor.realpred
        projected = numpy.dot(X, w)

        plotDir = os.path.join(self.settings.plotDir, 'compare_projections', predictor_name)
        if not os.path.exists(plotDir):
            os.makedirs(plotDir)

        histoplotter = scripts.EMBL.plotter.stats.Histogram()
        for dataset, dataset_name in zip([realvals, projected], ['discriminant_values', 'projections']):
            group1 = dataset[numpy.where(y == -1)]
            group2 = dataset[numpy.where(y ==  1)]

            cm = colors.ColorMap()
            colorvec = cm.makeDivergentColorRamp(2)

            filename = os.path.join(plotDir, "LDA_histo_%s_%s_2classes.png" % (dataset_name, predictor_name))
            histoplotter([group1, group2], filename, side_by_side=False,
                         title="histogram: %s %s" % (dataset_name, predictor_name),
                         xlabel=dataset_name, colorvec=colorvec)

            filename = os.path.join(plotDir, "LDA_histo_%s_%s_class1.png" % (dataset_name, predictor_name))
            histoplotter([group1], filename, side_by_side=False,
                         title="histogram: %s %s" % (dataset_name, predictor_name),
                         xlabel=dataset_name, colorvec=colorvec[:1])

            filename = os.path.join(plotDir, "LDA_histo_%s_%s_class2.png" % (dataset_name, predictor_name))
            histoplotter([group2], filename, side_by_side=False,
                         title="histogram: %s %s" % (dataset_name, predictor_name),
                         xlabel=dataset_name, colorvec=colorvec[1:])

        return

