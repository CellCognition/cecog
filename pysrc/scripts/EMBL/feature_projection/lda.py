import os, sys, time, re, pickle
import types

import numpy
#import mlpy

from cecog.learning.util import SparseWriter, ArffWriter, ArffReader

from scikits.learn.lda import LDA


class TrainingSet(object):
    def init(self):
        self._ar = None

    def readArffFile(self, filename):
        print 'reading %s' % filename
        self._ar = ArffReader(filename)
        self.getClasses()
        return

    def getClasses(self):
        self._phenoClasses = self._ar.dctFeatureData.keys()
        self._phenoClasses = filter(lambda x: x in self._ar.dctClassLabels, self._phenoClasses)
        return

    def checkMatrixForNAN(self, mat):
        bad_indices = []
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):

                if type(mat[i][j]) is types.StringType:
                    bad_indices.append((i,j))
                    continue

                if mat[i][j] is None:
                    bad_indices.append((i,j))
                    continue

                if numpy.isnan(mat[i][j]):
                    bad_indices.append((i,j))
                    continue

        return bad_indices

    def checkVariance(self, mat, epsilon=0.001):
        stdev = numpy.std(mat, axis=0, dtype=numpy.float64)
        bad_cols = numpy.where(stdev<=epsilon)
        return bad_cols

    def checkVarianceToAverageRatio(self, mat, epsilon=0.001):
        stdev = numpy.std(mat, axis=0, dtype=numpy.float64)
        avg = numpy.average(mat, axis=0)
        ratio = numpy.array([abs(x/y) if float(y)!=0.0 else 0.0
                             for x,y in zip(stdev, avg)], dtype=numpy.float64)
        bad_cols = numpy.where(ratio<=epsilon)
        return bad_cols

    def checkCorrelation(self, mat, correlation_threshold=0.999):
        cc = numpy.corrcoef(numpy.transpose(mat), rowvar=1) - \
             numpy.diag([1.0 for a in range(mat.shape[1])])
        bad_cols = numpy.where(cc >= correlation_threshold)
        return bad_cols

    # recodes the classes according to the codes.
    # e.g. phenoClasses = ['Interphase', 'Mitosis', 'Apoptosis']
    # initial code = [1, 2, 3]
    # codes = [-1, 1, 0]
    # the mapping is updated by the function.
    def recodeClasses(self, phenoClasses, codes):
        recode_dictionary = dict(zip([self._ar.dctClassLabels[phenoClass] for phenoClass in phenoClasses],
                                     codes))
        return recode_dictionary

    def DEPRECATED_getTwoClassRecodeDictionary(self, pheno1, pheno2):
        recode_dictionary = {
                             self._ar.dctClassLabels[pheno1]: -1,
                             self._ar.dctClassLabels[pheno2]:  1,
                             }
        return recode_dictionary

    def recodeTargets(self, y, recode_dictionary):
        for old, new in recode_dictionary.iteritems():
            y[numpy.where(y==old)] = new
        return y

    def __call__(self, filename,
                 nan_action='remove_columns',
                 variance=0.0,
                 features_remove=None,
                 correlation_threshold=None,
                 phenoClasses=None,
                 normalization_method=None,
                 recode_dictionary=None):

        self.readArffFile(filename)
        self.filterData(nan_action, variance, features_remove, correlation_threshold)
        datamat, targetvec = self.extractData(phenoClasses=phenoClasses)
        X, y = self.normalizeFeatures(datamat, targetvec, normalization_method)
        if not recode_dictionary is None:
            y = self.recodeTargets(y, recode_dictionary)

        return X, y

    def filterData(self,
                   nan_action='remove_columns',
                   variance=0.0,
                   features_remove=None,
                   correlation_threshold=None):

        # predefined features to remove (typically particular classes
        # of features)
        if not features_remove is None:
            print 'removing %i features (chosen)' % (len(features_remove))
            self.removeFeatures(features_remove)

        # check if there are undefined values
        if not nan_action is None:
            mat,y = self.extractData()
            bad_indices = self.checkMatrixForNAN(mat)
            cols = [bad_index[0] for bad_index in bad_indices]
            rows = [bad_index[1] for bad_index in bad_indices]
            print 'NAN values in %i rows and %i columns' % (len(rows), len(cols))

            if len(cols) > 0 or len(rows) > 0:
                print '%s: the following columns are not valid: ' % annotation_class, list(set(cols))
                print '%s: the following rows are not valid: ' % annotation_class, list(set(rows))

                if nan_action =='remove_features':
                    print '%i out of %i are removed' % (len(cols), len(self._ar.dctFeatureData[phenoClass].shape[0]))
                    self.removeFeatures(indices=cols)
                elif nan_action == 'remove_samples':
                    print '%i out of %i samples are removed' % (len(rows), len(self._ar.dctFeatureData[phenoClass].shape[1]))
                    self.removeSamples(phenoClass, indices=rows)
                else:
                    print 'no action is taken'

        # remove features with low variance
        if not variance is None:
            mat,y = self.extractData()
            bad_cols = self.checkVariance(mat, variance)
            print 'Variance: %i features have a variance of %f' % (len(bad_cols),
                                                                   variance)
            self.removeFeatures(indices=bad_cols)

        # remove correlated features
        # for each pair of correlated features, remove the first (arbitrary)
        # should only be used for very high correlation_thresholds (typically 0.999)
        if not correlation_threshold is None:
            mat,y = self.extractData()
            bad_cols = self.checkCorrelation(mat, correlation_threshold)

            rem_indices = []
            for f1, f2 in zip(bad_cols[0], bad_cols[1]):
                if not f1 in rem_indices and not f2 in rem_indices:
                    rem_indices.append(f1)
            rem_indices.sort()
            print 'Correlation: %i features have a correlation of %f' % (len(rem_indices),
                                                                         correlation_threshold)

            self.removeFeatures(indices=rem_indices)

        return

    def removeSamples(self, phenoClass, indices):
        indices = numpy.array(indices)
        for phenoClass in self._ar.dctFeatureData.keys():
            self._ar.dctFeatureData[phenoClass] = \
                numpy.delete(self._ar.dctFeatureData[phenoClass], indices, axis=0)

        return

    # removes features (which can be given by either names or indices)
    # to retrieve the initial values again, the arff file has to be reloaded.
    def removeFeatures(self, features=None, indices=None):
        if features is None and indices is None:
            raise ValueError("You must provide either a list of features or a list of indices.")
        if features is None:
            all_features = numpy.array(self._ar.lstFeatureNames)
            features = all_features[indices]
        features = filter(lambda x: x in self._ar.lstFeatureNames, features)
        if indices is None:
            indices = [self._ar.lstFeatureNames.index(x) for x in features]
            features = numpy.array(features)
        indices = numpy.array(indices)
        self._ar.lstFeatureNames = filter(lambda x: x not in features, self._ar.lstFeatureNames)
        for phenoClass in self._ar.dctFeatureData.keys():
            self._ar.dctFeatureData[phenoClass] = \
                numpy.delete(self._ar.dctFeatureData[phenoClass], indices, axis=1)
        return

    # here a subset of the feature data can be extracted.
    def extractData(self, features=None, phenoClasses=None):
        if features is None:
            features = self._ar.lstFeatureNames
        if phenoClasses is None:
            phenoClasses = self._phenoClasses

        indices = numpy.array(
                              [self._ar.lstFeatureNames.index(x)
                               for x in features]
                              )
        annotation_data = numpy.concatenate([self._ar.dctFeatureData[annotation_class][:,indices]
                                             for annotation_class in phenoClasses])
        target_vec = numpy.concatenate([[self._ar.dctClassLabels[annotation_class]
                                         for i in self._ar.dctFeatureData[annotation_class]]
                                        for annotation_class in phenoClasses])

        return annotation_data, target_vec

    def getFeatureNames(self):
        return self._ar.lstFeatureNames

    # phenoClasses is a subset of the classes in the arff file
    # if a class has no annotations, ar warning is produced, and the data
    # for the rest of the classes is extracted.
    def extractFeatureAndAnnotationData(self, phenoClasses=None):

        if annotation_classes is None:
            phenoClasses = self._phenoClasses

        annotation_data = []
        target_vec = []

        annotation_data = numpy.concatenate([self._ar.dctFeatureData[annotation_class]
                                             for annotation_class in phenoClasses])
        target_vec = numpy.concatenate([[self._ar.dctClassLabels[annotation_class]
                                         for i in self._ar.dctFeatureData[annotation_class]]
                                        for annotation_class in phenoClasses])

        return annotation_data, target_vec

    def normalizeFeatures(self, mat=None, y=None, method='z'):

        if mat is None or y is None:
            mat, y = self.extractData()

        normmat = mat

        if method == 'z':
            avg = numpy.average(mat, axis=0)
            stdev = numpy.std(mat, axis=0, dtype=numpy.float64)
            normmat = (mat - avg) / stdev
            self._avg = avg
            self._stdev = stdev

        if method == 'minmax':
            maxvals = numpy.max(mat, axis=0)
            minvals = numpy.min(mat, axis=0)
            normmat = 2.0 * (mat - minvals) / (maxvals - minvals) - 1.0
            self._minvals = minvals
            self._maxvals = maxvals

        return normmat, y

class Rpy2LDA(object):
    def __init__(self):
        print 'Rpy2LDA'

        # import rpy2
        from rpy2.robjects import r
        from rpy2.robjects import IntVector, Formula
        from rpy2.robjects.packages import importr
        import rpy2.robjects as robjects

        r.require("MASS")
        self._calc = False
        self.model = None
        self.mu = None

    def predict(self, X):
        if self.model is None:
            raise ValueError("The model has to be learned first.")

        # get the weights
        vals = self.model[3]
        w  = [vals[i] for i in range(len(vals))]

        Xnorm = X - self.mu
        decision_vals = numpy.dot(Xnorm, w)
        #predictions = numpy.sign(decision_vals)
        predictions = [int(x) for x in numpy.sign(decision_vals).tolist()]
        self.realpred = decision_vals

        return predictions

    def weights(self, X, y):
        if not self._calc:
            self.compute(X, y)
        vals = self.model[3]
        w  = [vals[i] for i in range(len(vals))]
        return w

    def compute(self, X, y):

        # conversion of numpy arrays
        Xrpy = r.matrix(r.unlist(X.tolist()), ncol=X.shape[1],
                        nrow=X.shape[0], byrow=True)
        yrpy = robjects.IntVector(y.tolist())

        print 'FORMULA'
        # formula environment
        fmla = Formula('y ~ X')
        env = fmla.environment
        env['X'] = Xrpy
        env['y'] = yrpy

        print 'MAKE MODEL'
        self.model = r('lda(%s)' % fmla.r_repr())

        print 'COLLECT RESULTS'
        mu1 = numpy.mean(X[y==1,], axis=0)
        mu2 = numpy.mean(X[y==-1,], axis=0)
        self.mu = .5 * (mu1 + mu2)
        self._calc = True
        return

        #ldares <- lda(grouping ~ ., subsetTrainingData)
        #completePrediction <- predict(ldares, normTrainingData)
        #trainingData$projections <- completePrediction$x
        #normTrainingData$projections <- completePrediction$x

# makes an API to different LDA implementations
# coming from:
# - mlpy
# - rpy2
# - scikit
class ScikitLDA(object):
    def __init__(self):
        self.clf = LDA()
        self.realpred = None
        self._calc = False

        #w = predictor.weights(X, y)
        #predictions = predictor.predict(X)
        #realvals = predictor.realpred

    def predict(self, X):
        if not self._calc:
            raise ValueError("The classifier has not yet been trained.")
        ypred = self.clf.predict(X)
        discriminant_values = self.clf.decision_function(X)
        self.realpred = discriminant_values[:,0]
        return ypred

    def compute(self, X, y):
        self.clf.fit(X,y)
        self._calc = True
        return

    def weights(self, X, y):
        self.clf.fit(X, y)
        weights = numpy.transpose(self.clf.scaling)[0]
        self._calc = True
        return weights


class LDAClassifier(object):

    def __init__(self):
        self._weights = None
        self._ts = TrainingSet()

    def readTrainingSet(self, filename):
        self._ts.readArffFile(filename)
        return

    def makeCrossValidation(self, X, y, phenoClassLabels,
                            predictor=None, fold=10):
        if predictor is None:
            predictor = mlpy.Fda()

        cv_indices = self.getEQCrossValidationIndices(y, phenoClassLabels, fold)
        correct = 0
        for i in cv_indices.keys():
            training_indices = cv_indices[i]['train']
            test_indices = cv_indices[i]['test']
            #print 'length of the training set: %i' % len(training_indices)
            #print 'length of the test set: %i' % len(test_indices)
            X_train = X[training_indices]
            y_train = y[training_indices]
            X_test = X[test_indices]
            y_test = y[test_indices]

            #fda = self.learnKernelFDA(X_reduced, y_reduced)
            #predictor = mlpy.Fda()
            predictor.compute(X_train, y_train)
            y_pred = predictor.predict(X_test)

            correct_predictions_i = numpy.count_nonzero(y_pred==y_test)

            correct += correct_predictions_i
            print
            print y_test
            print y_pred
            #print 'score: ', predictor.realpred
            #print '%i: %i / %i' % (i, correct_predictions_i, len(y_test))

        print
        print '*************************'
        print '%i fold cross validation:' % fold
        print '%i / %i (accuracy: %f)' % (correct, len(y),
                                          (float(correct)/float(len(y))) )
        print 'DONE!'
        return correct

    # get equally balanced indices for cross validation.
    def getEQCrossValidationIndices(self, y, phenoClassLabels, fold):
        res = {}
        for classLabel in phenoClassLabels:

            indices = numpy.where(y==classLabel)[0]
            #print 'indices: ', indices

            rand_indices = numpy.random.permutation(indices)
            #print 'rand_indices: ', rand_indices

            step_size = numpy.ceil(len(indices) / float(fold))

            for i in range(fold):
                if not i in res:
                    res[i] = {'test':  numpy.array([], dtype = numpy.integer),
                              'train': numpy.array([], dtype = numpy.integer)}

                test_indices =  rand_indices[(i*step_size):min(step_size*(i+1),
                                                               len(rand_indices))]
                train_indices = numpy.setdiff1d(rand_indices, test_indices)
                res[i]['test'] = numpy.append(res[i]['test'], test_indices)
                res[i]['train'] = numpy.append(res[i]['train'], train_indices)

        return res

    def getWeights(self, X, y, predictor):
        w = predictor.weights(X, y)
        return w




