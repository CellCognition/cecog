import os, re, time, pickle, sys

import scripts.EMBL.projects.post_processing
import scripts.EMBL.feature_projection.lda
reload(scripts.EMBL.feature_projection.lda)

from sklearn import svm
from sklearn import lda
from sklearn import datasets
from sklearn import cross_validation
from sklearn.feature_selection import RFE
from sklearn.cross_validation import StratifiedKFold
from sklearn.feature_selection import RFECV
from sklearn.metrics import zero_one
import sklearn.feature_selection.univariate_selection
from sklearn.linear_model import LogisticRegression

import operator

import scripts.EMBL.plotter.stats
reload(scripts.EMBL.plotter.stats)

import numpy
import scipy.stats

from collections import OrderedDict

import matplotlib.pyplot as plt

import lda_helper

# export PYTHONPATH=/Users/twalter/workspace/cecog/pysrc

PLOT_SUFFIX = 'png'


import sklearn

class MyRFE(object):

    def makeCrossValidation(self, X, y, clf, fold=10):
        skf = StratifiedKFold(y, fold)
        nb_test = numpy.array([test.sum() for train, test in skf])
        score = cross_validation.cross_val_score(clf, X, y, cv=skf)
        nb_correct_classifications = numpy.dot(nb_test, score)
        nb_false_classifications = len(y) - nb_correct_classifications
        return nb_correct_classifications, nb_false_classifications

    def __call__(self, X, y, clf):
        nb_samples, nb_features = X.shape
        removed_features = []
        correctclass_vec = []
        falseclass_vec = []

        #print nb_samples, nb_features

        feature_selection_status = numpy.array([True for i in range(nb_features)])

        #clf.fit(X, y)
        #nb_correct, nb_false = self.makeCrossValidation(X, y, clf, 10)
        #falseclass_vec.append(nb_false)
        #correctclass_vec.append(nb_correct)
        self.detailed_score = []

        for i in range(nb_features):
            features = numpy.arange(nb_features)[feature_selection_status]

            clf.fit(X[:, features], y)

            nb_correct, nb_false = self.makeCrossValidation(X[:, features], y, clf, 10)
            falseclass_vec.append(nb_false)
            correctclass_vec.append(nb_correct)

            self.detailed_score.append(clf.coef_ ** 2)
            min_index = numpy.argmin(clf.coef_ ** 2)

            #print min_index
            #print features
            feature_to_remove = features[min_index]
            feature_selection_status[feature_to_remove] = False
            removed_features.append(feature_to_remove)

            print '%i / %i \t removed index: %i\tnb of removed features:%i' % (i, nb_features,
                                                                               feature_to_remove,
                                                                               len(removed_features))


        self.falseclass_vec = falseclass_vec
        self.correctclass_vec = correctclass_vec
        self.accuracy = [x / float(x + y) for x, y in zip(correctclass_vec, falseclass_vec)]
        self.ranking = removed_features
        for ll in [self.ranking, self.accuracy, self.correctclass_vec,
                   self.falseclass_vec, self.detailed_score]:
            ll.reverse()

#            # Remaining features
#            features = np.arange(n_features)[support_]
#
#            # Rank the remaining features
#            estimator = clone(self.estimator)
#            estimator.fit(X[:, features], y)
#            ranks = np.argsort(np.sum(estimator.coef_ ** 2, axis=0))
#
#            # Eliminate the worse features
#            threshold = min(step, np.sum(support_) - self.n_features_to_select)
#            support_[features[ranks][:threshold]] = False
#            ranking_[np.logical_not(support_)] += 1


class MultiClassRFE(MyRFE):
    def __call__(self, X, y, clf):
        nb_samples, nb_features = X.shape
        removed_features = []
        correctclass_vec = []
        falseclass_vec = []

        feature_selection_status = numpy.array([True for i in range(nb_features)])

        self.detailed_score = []

        for i in range(nb_features):
            features = numpy.arange(nb_features)[feature_selection_status]

            clf.fit(X[:, features], y)

            nb_correct, nb_false = self.makeCrossValidation(X[:, features], y, clf, 10)
            falseclass_vec.append(nb_false)
            correctclass_vec.append(nb_correct)

            self.detailed_score.append(clf.coef_ ** 2)
            min_index = numpy.argmin(clf.coef_ ** 2)

            #print min_index
            #print features
            feature_to_remove = features[min_index]
            feature_selection_status[feature_to_remove] = False
            removed_features.append(feature_to_remove)

            print '%i / %i \t removed index: %i\tnb of removed features:%i' % (i, nb_features,
                                                                               feature_to_remove,
                                                                               len(removed_features))


        self.falseclass_vec = falseclass_vec
        self.correctclass_vec = correctclass_vec
        self.accuracy = [x / float(x + y) for x, y in zip(correctclass_vec, falseclass_vec)]
        self.ranking = removed_features
        for ll in [self.ranking, self.accuracy, self.correctclass_vec,
                   self.falseclass_vec, self.detailed_score]:
            ll.reverse()


class feature_projection_study(object):
    def __init__(self, settings_filename):
        self.fpa = scripts.EMBL.projects.post_processing.FeatureProjectionAnalysis(settings_filename)
        self.trainingset_filename = self.fpa.settings.trainingset_filename
        self.ts = scripts.EMBL.feature_projection.lda.TrainingSet()
        self.ts.readArffFile(self.trainingset_filename)

        # plotter classes
        self.bp = scripts.EMBL.plotter.stats.Barplot()
        self.sp = scripts.EMBL.plotter.stats.Scatterplot()
        self.spm = scripts.EMBL.plotter.stats.ScatterplotMatrix()


    def readDataSet(self, phenoClasses=None):
        if phenoClasses is None:
            phenoClasses = self.fpa.settings.PHENOCLASSES_FOR_TRAINING
        Xtemp, y = self.ts(self.trainingset_filename,
                           features_remove=self.fpa.settings.FEATURES_REMOVE,
                           correlation_threshold=0.99,
                           #phenoClasses=['interphase', 'early_prophase'],
                           phenoClasses=phenoClasses,
                           #phenoClasses=self.fpa.settings.PHENOCLASSES,
                           normalization_method='z',
                           recode_dictionary=None)
        X = numpy.float64(Xtemp)
        return X, y


    def testPvals(self):
        Xtemp, y1 = self.ts(self.trainingset_filename,
                           features_remove=self.fpa.settings.FEATURES_REMOVE,
                           correlation_threshold=0.99,
                           #phenoClasses=['interphase', 'early_prophase'],
                           phenoClasses=self.fpa.settings.PHENOCLASSES_FOR_TRAINING,
                           #phenoClasses=self.fpa.settings.PHENOCLASSES,
                           normalization_method='z',
                           recode_dictionary=None)
        X1 = numpy.float64(Xtemp)
        feature_names1 = self.ts.getFeatureNames()

        Xtemp, y2 = self.ts(self.trainingset_filename,
                           features_remove=self.fpa.settings.FEATURES_REMOVE,
                           correlation_threshold=0.99,
                           phenoClasses=['interphase', 'early_prophase'],
                           #phenoClasses=self.fpa.settings.PHENOCLASSES_FOR_TRAINING,
                           #phenoClasses=self.fpa.settings.PHENOCLASSES,
                           normalization_method='z',
                           recode_dictionary=None)
        X2 = numpy.float64(Xtemp)
        feature_names2 = self.ts.getFeatureNames()

        Xtemp, y3 = self.ts(self.trainingset_filename,
                           features_remove=self.fpa.settings.FEATURES_REMOVE,
                           correlation_threshold=0.99,
                           #phenoClasses=['interphase', 'early_prophase'],
                           #phenoClasses=self.fpa.settings.PHENOCLASSES_FOR_TRAINING,
                           phenoClasses=self.fpa.settings.PHENOCLASSES,
                           normalization_method='z',
                           recode_dictionary=None)
        X3 = numpy.float64(Xtemp)
        feature_names3 = self.ts.getFeatureNames()

        Xtemp, y4 = self.ts(self.trainingset_filename,
                           features_remove=self.fpa.settings.FEATURES_REMOVE,
                           correlation_threshold=0.99,
                           phenoClasses=['early_prophase', 'mid_prophase'],
                           #phenoClasses=self.fpa.settings.PHENOCLASSES_FOR_TRAINING,
                           #phenoClasses=self.fpa.settings.PHENOCLASSES,
                           normalization_method='z',
                           recode_dictionary=None)
        X4 = numpy.float64(Xtemp)
        feature_names4 = self.ts.getFeatureNames()

        print '1: ', X1.shape, len(feature_names1), filter(lambda x: x not in feature_names2 or x not in feature_names3 or not x in feature_names4, feature_names1)
        print '2: ', X2.shape, len(feature_names2), filter(lambda x: x not in feature_names1 or x not in feature_names3 or not x in feature_names4, feature_names2)
        print '3: ', X3.shape, len(feature_names3), filter(lambda x: x not in feature_names2 or x not in feature_names1 or not x in feature_names4, feature_names3)
        print '4: ', X4.shape, len(feature_names4), filter(lambda x: x not in feature_names2 or x not in feature_names1 or not x in feature_names3, feature_names4)


        anova_score1 = sklearn.feature_selection.univariate_selection.f_classif(X1, y1)
        anova_score2 = sklearn.feature_selection.univariate_selection.f_classif(X2, y2)
        anova_score3 = sklearn.feature_selection.univariate_selection.f_classif(X3, y3)
        anova_score4 = sklearn.feature_selection.univariate_selection.f_classif(X4, y4)

        N = 3
        print '1: ', zip(['teststat: ' for i in range(N)], anova_score1[0][0:N],
                         ['pval: ' for i in range(N)], anova_score1[1][0:N])
        print '2: ', zip(['teststat: ' for i in range(N)], anova_score2[0][0:N],
                         ['pval: ' for i in range(N)], anova_score2[1][0:N])
        print '3: ', zip(['teststat: ' for i in range(N)], anova_score3[0][0:N],
                         ['pval: ' for i in range(N)], anova_score3[1][0:N])
        print '4: ', zip(['teststat: ' for i in range(N)], anova_score4[0][0:N],
                         ['pval: ' for i in range(N)], anova_score4[1][0:N])

        return

    def getFeatureWeights(self):

        X, y = self.readDataSet()
        feature_names = self.ts.getFeatureNames()

        # get feature weights from linear SVM
        clf = svm.SVC(kernel='linear', probability=False, shrinking=False)
        clf.fit(X, y)
        svm_feature_weights = numpy.abs(clf.coef_[0])
        svm_feature_weights /= max(svm_feature_weights)

        # get the weights from LDA
        clf = lda.LDA()
        clf.fit(X,y)
        lda_feature_weights = numpy.abs(clf.scaling[:,0])
        lda_feature_weights /= max(lda_feature_weights)

        # get the univariate feature scores
        pval, class_pairs = self.getWilcoxonScore(X, y)
        pval_min = pval.min(axis=0)
        sc = -numpy.log10(pval_min)
        univariate_score = sc / max(sc)

        joint_score = [max(k) for k in zip(svm_feature_weights, lda_feature_weights,
                                            univariate_score)]

        total_score = zip(feature_names,
                          svm_feature_weights,
                          lda_feature_weights,
                          univariate_score,
                          joint_score)

        # multi-barplot (ordered by SVM)
        total_score.sort(key=operator.itemgetter(1), reverse=True)
        datamatrix = numpy.transpose(numpy.array([[x[1] for x in total_score],
                                                  [x[2] for x in total_score],
                                                  [x[3] for x in total_score],]))

        filename = os.path.join(self.study_dir, "barplot_feature_weights_lda_svm_orderedbysvm.%s" % PLOT_SUFFIX)
        self.bp.multiBarplot(datamatrix, filename, width=1.0,
                             dataset_names = ['svm', 'lda', 'univariate'])

        # multi-barplot (ordered by LDA)
        total_score.sort(key=operator.itemgetter(2), reverse=True)
        datamatrix = numpy.transpose(numpy.array([[x[1] for x in total_score],
                                                  [x[2] for x in total_score],
                                                  [x[3] for x in total_score],]))

        filename = os.path.join(self.study_dir, "barplot_feature_weights_lda_svm_orderedbylda.%s" % PLOT_SUFFIX)
        self.bp.multiBarplot(datamatrix, filename, width=1.0,
                             dataset_names = ['svm', 'lda', 'univariate'])

        # multi-barplot (ordered by max)
        total_score.sort(key=operator.itemgetter(-1), reverse=True)
        datamatrix = numpy.transpose(numpy.array([[x[1] for x in total_score],
                                                  [x[2] for x in total_score],
                                                  [x[3] for x in total_score]]))

        filename = os.path.join(self.study_dir, "barplot_feature_weights_lda_svm_orderedbymax.%s" % PLOT_SUFFIX)
        self.bp.multiBarplot(datamatrix, filename, width=1.0,
                             dataset_names = ['svm', 'lda', 'univariate'])

        # scatterplot
        filename = os.path.join(self.study_dir, "scatter_feature_weights_lda_svm.%s" % PLOT_SUFFIX)
        self.sp.single(lda_feature_weights, svm_feature_weights, filename,
                       xlabel='LDA', ylabel='SVM',
                       title='Feature Weights (Raw image features for SVM and LDA)',
                       edgecolor=(0.1, 0.1, 0.1))

        filename = os.path.join(self.study_dir, "scatterplotmatrix_feature_weights_lda_svm_univ.%s" % PLOT_SUFFIX)
        self.spm(numpy.array([lda_feature_weights, svm_feature_weights, univariate_score]).T,
                 filename, colnames=['LDA', 'SVM', 'Univariate'],
                 color=(0.0, 0.0, 1.0))

        # plot a scatter plot matrix with the N most informative features
        N = 5
        #classnames = [COLORDICT.keys()[int(i)-1] for i in y]
        classnames = [self.CLASSNAMES[int(i)] for i in y]
        colorvec = [self.COLORDICT[name] for name in classnames]

        # for svm
        total_score.sort(key=operator.itemgetter(1), reverse=True)
        best_svm_features = [total_score[i][0] for i in range(N)]
        indices = [feature_names.index(x) for x in best_svm_features]
        subset_svm = X[:, indices]
        print
        print '*** SVM Weights'
        for i in range(N):
            print i, total_score[i][1], total_score[i]
        filename = os.path.join(self.study_dir, "scatterplotmatrix_SVM_%ifeatures.%s" % (N, PLOT_SUFFIX))
        self.spm(subset_svm, filename, colnames=best_svm_features,
                 color=colorvec)

        # for lda
        total_score.sort(key=operator.itemgetter(2), reverse=True)
        best_lda_features = [total_score[i][0] for i in range(N)]
        indices = [feature_names.index(x) for x in best_lda_features]
        subset_lda = X[:, indices]
        print
        print '*** LDA Weights'
        for i in range(N):
            print i, total_score[i][2], total_score[i]
        filename = os.path.join(self.study_dir, "scatterplotmatrix_LDA_%ifeatures.%s" % (N, PLOT_SUFFIX))
        self.spm(subset_lda, filename, colnames=best_lda_features,
                 color=colorvec)

        # for univariate
        total_score.sort(key=operator.itemgetter(3), reverse=True)
        best_univ_features = [total_score[i][0] for i in range(N)]
        indices = [feature_names.index(x) for x in best_univ_features]
        subset_univ = X[:, indices]
        print
        print '*** Univariate Feature Selection'
        for i in range(N):
            print i, indices[i], total_score[i][3], total_score[i]

        filename = os.path.join(self.study_dir, "scatterplotmatrix_UNIV_%ifeatures.%s" % (N, PLOT_SUFFIX))
        self.spm(subset_univ, filename, colnames=best_univ_features,
                 color=colorvec)

        return

    def makeCrossValidation(self, X, y, clf, fold=10):
        skf = StratifiedKFold(y, fold)
        nb_test = numpy.array([test.sum() for train, test in skf])
        score = cross_validation.cross_val_score(clf, X, y, cv=skf)
        nb_correct_classifications = numpy.dot(nb_test, score)
        nb_false_classifications = len(y) - nb_correct_classifications
        return nb_correct_classifications, nb_false_classifications

    def getSVMDecisionFeatures(self, X, y, training_classlabels):
        # get the trainings
        indices = filter(lambda i: y[i] in training_classlabels, range(len(y)))
        Xtrain = X[indices,:]
        ytrain = y[indices]

        # get SVM features
        clf = svm.SVC(kernel='linear', probability=True, shrinking=True)
        clf.fit(Xtrain, ytrain)

        dec = clf.decision_function(X)
        prob = clf.predict_proba(X)
        log_prob = clf.predict_log_proba(X)

        features = numpy.array([dec[:,0], prob[:,0], log_prob[:,0]]).T
        columns = ['svm_dec', 'svm_p0', 'svm_logp0']
        return features, columns

    def getLogisticRegressionDecisionFeatures(self, X, y, training_classlabels):
        # get the trainings
        indices = filter(lambda i: y[i] in training_classlabels, range(len(y)))
        Xtrain = X[indices,:]
        ytrain = y[indices]

        # get SVM features
        clf = LogisticRegression(C=1.0, penalty='l2')
        clf.fit(Xtrain, ytrain)

        dec = clf.decision_function(X)
        prob = clf.predict_proba(X)
        log_prob = clf.predict_log_proba(X)

        features = numpy.array([dec[:,0], prob[:,0], log_prob[:,0]]).T
        columns = ['logres_dec', 'logres_p0', 'logres_logp0']
        return features, columns


    def getLDADecisionFeatures(self, X, y, training_classlabels):
        nb_samples, nb_features = X.shape

        # get the trainings
        indices = filter(lambda i: y[i] in training_classlabels, range(len(y)))
        Xtrain = X[indices,:]
        ytrain = y[indices]

        # get the weights from LDA
        clf = lda.LDA()
        clf.fit(Xtrain,ytrain)

        prob = clf.predict_proba(X)
        log_prob = clf.predict_log_proba(X)
        dec = clf.decision_function(X)

        decval = dec[:, 1] - dec[:,0]
        #proj = clf.transform(X)
        #res = numpy.append(prob, dec, axis=1)
        #res = numpy.append(res, proj, axis=1)
        # dec, p0, logp0
        features = numpy.array([decval, prob[:,0], log_prob[:,0]]).T
        #res = numpy.append(res, log_prob[:,0].reshape((nb_samples, 1)), axis=1)
        #columns = ['lda_p0', 'lda_p1', 'lda_dec0', 'lda_dec1', 'lda_proj', 'lda_logprob']
        columns = ['lda_dec', 'lda_p0', 'lda_logp0']
        return features, columns


    def investigateFeatureSubset(self, feature_indices, feature_names, N):

        import_classnames = self.import_classnames

        X, y = self.readDataSet(phenoClasses = import_classnames)
        classnames = [self.CLASSNAMES[int(i)] for i in y]

        Xred = X[:, feature_indices[:N]]

        colorvec = [self.COLORDICT[name] for name in classnames]
        #colorvec = [(0.0, 1.0, 0.3), (0.9, 0.9, 0.0), (0.0, 0.1, 1.0)]

        filename = os.path.join(self.study_dir, "scatterplotmatrix_RFE-SVM-%ifeatures-%iclasses.%s" % (N, len(import_classnames), PLOT_SUFFIX))
        self.spm(Xred, filename, colnames=feature_names[:N],
                 color=colorvec)

        # first question: comparison of different classification features
        # for the unreduced feature set
        projection_comp_dir = os.path.join(self.study_dir, 'compare_projections')
        if not os.path.exists(projection_comp_dir):
            os.makedirs(projection_comp_dir)

        print 'PLOTS GO TO %s, %s' % (self.study_dir, projection_comp_dir)

        training_class_labels = [1.0, 3.0]

        res_lda, col_lda = self.getLDADecisionFeatures(X, y, training_class_labels)
        res_svm, col_svm = self.getSVMDecisionFeatures(X, y, training_class_labels)
        res_lr,  col_lr  = self.getLogisticRegressionDecisionFeatures(X, y, training_class_labels)

        filename = os.path.join(projection_comp_dir, 'scatterplotmatrix_unreduced_LDA_SVM_LogRes.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.append(res_lda, res_svm, axis=1)
        plot_matrix = numpy.append(plot_matrix, res_lr, axis=1)
        colnames = numpy.concatenate([col_lda, col_svm, col_lr])
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        res_red_lda, col_red_lda = self.getLDADecisionFeatures(Xred, y, training_class_labels)
        res_red_svm, col_red_svm = self.getSVMDecisionFeatures(Xred, y, training_class_labels)
        res_red_lr,  col_red_lr  = self.getLogisticRegressionDecisionFeatures(Xred, y, training_class_labels)

        filename = os.path.join(projection_comp_dir, 'scatterplotmatrix_reduced_LDA_SVM_LogRes.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.append(res_red_lda, res_red_svm, axis=1)
        plot_matrix = numpy.append(plot_matrix, res_red_lr, axis=1)
        #print plot_matrix[1]
        #print res_red_lda[1,[0,2,4]], res_red_svm, res_red_lr
        colnames = numpy.concatenate([col_red_lda, col_red_svm, col_red_lr])
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        # SCATTER PLOT MATRICES; ONE MATRIX PER CLASSIFICATION METHOD
        filename = os.path.join(projection_comp_dir, 'scatterplotmatrix_comparison_featureselection_LDA.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.append(res_red_lda, res_lda, axis=1)
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        colnames = ['reduced: %s' % x for x in col_red_lda] + \
                   ['full: %s' % x for x in col_red_lda]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'scatterplotmatrix_comparison_featureselection_SVM.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.append(res_red_svm, res_svm, axis=1)
        colnames = ['reduced: %s' % x for x in col_svm] + ['full: %s' % x for x in col_svm]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'scatterplotmatrix_comparison_featureselection_LogReg.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.append(res_red_lr, res_lr, axis=1)
        colnames = ['reduced: %s' % x for x in col_lr] + ['full: %s' % x for x in col_lr]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)


        # SCATTER PLOT MATRICES; ONE MATRIX PER FEATURE (ACROSS CLASSIFICATION METHODS)
        #columns = ['lda_p0', 'lda_p1', 'lda_dec0', 'lda_dec1', 'lda_proj', 'lda_logprob']
        # columns = ['logres_dec', 'logres_p0', 'logres_logp0']
        filename = os.path.join(projection_comp_dir, 'across_classifiers_decision_value.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_lda[:,0], res_svm[:,0], res_lr[:,0]]).T

        colname_matrix = numpy.array([col_lda, col_svm, col_lr])

        #plot_matrix = numpy.append(res_lda[:,0], res_svm[:,0], res_lr[:,0], axis=1)
        #colnames = ['lda_' + col_lda[0], 'svm_' + col_svm[0], 'logres_' + col_lr[0]]
        #colnames = ['reduced: %s' % x for x in col_lr] + ['full: %s' % x for x in col_lr]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        colnames = colname_matrix[:,0]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'across_classifiers_probability.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_lda[:,1], res_svm[:,1], res_lr[:,1]]).T
        #plot_matrix = numpy.append(res_lda[:,1], res_svm[:,1], res_lr[:,1], axis=1)
        #colnames = ['lda_' + col_lda[1], 'svm_' + col_svm[1], 'logres_' + col_lr[1]]
        #colnames = ['reduced: %s' % x for x in col_lr] + ['full: %s' % x for x in col_lr]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        colnames = colname_matrix[:,1]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'across_classifiers_logprobability.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_lda[:,2], res_svm[:,2], res_lr[:,2]]).T
        #colnames = ['lda_' + col_lda[2], 'svm_' + col_svm[2], 'logres_' + col_lr[2]]
        colnames = colname_matrix[:,2]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'across_classifiers_decision_value_reduced.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_red_lda[:,0], res_red_svm[:,0], res_red_lr[:,0]]).T
        #colnames = ['lda_' + col_lda[0], 'svm_' + col_svm[0], 'logres_' + col_lr[0]]
        #colnames = ['reduced: %s' % x for x in col_lr] + ['full: %s' % x for x in col_lr]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        colnames = colname_matrix[:,0]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'across_classifiers_probability_reduced.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_red_lda[:,1], res_red_svm[:,1], res_red_lr[:,1]]).T
        #colnames = ['lda_' + col_lda[1], 'svm_' + col_svm[1], 'logres_' + col_lr[1]]
        #colnames = ['reduced: %s' % x for x in col_lr] + ['full: %s' % x for x in col_lr]
        #colnames = numpy.concatenate([numpy.array(col_red_lda)[[0,2,4]], numpy.array(col_lda)[[0,2,4]]])
        colnames = colname_matrix[:,1]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        filename = os.path.join(projection_comp_dir, 'across_classifiers_logprobability_reduced.%s' % PLOT_SUFFIX)
        plot_matrix = numpy.array([res_red_lda[:,2], res_red_svm[:,2], res_red_lr[:,2]]).T
        #plot_matrix = numpy.append(res_lda_red[:,2], res_svm_red[:,2], res_lr_red[:,2], axis=1)
        #colnames = ['lda_' + col_lda[2], 'svm_' + col_svm[2], 'logres_' + col_lr[2]]
        colnames = colname_matrix[:,2]
        self.spm(plot_matrix, filename, colnames=colnames, color=colorvec,
                 histo_same_scale=False)

        #granu_open_volume_1
        #h2_IDM
        #ls0_CAREA_sample_mean
        #ls1_NCA_sample_sd
        #h1_2CON
        #h1_IDM
        return

    # HERE I AM
    def compareRFE(self, X, y, feature_names):

        FOLD = 16
        #X, y = self.readDataSet()
        #feature_names = self.ts.getFeatureNames()

        clf_lda = lda_helper.LDA() #lda.LDA()
        clf_lda.fit(X,y)

        clf_svm = svm.SVC(kernel='linear', probability=False, shrinking=False)
        clf_svm.fit(X, y)

        rfe_svm = MyRFE()
        rfe_svm(X, y, clf_svm)

        # RFE-SVM
        clf_name = 'svm'
        ranked_features_svm = numpy.array(feature_names)[rfe_svm.ranking]
        filename = os.path.join(self.study_dir, 'rfe-%s_cv_accuracy.%s' % (clf_name, PLOT_SUFFIX))
        plt.figure(1)
        ax=plt.subplot(1,1,1)
        yvec = numpy.array([i+1 for i in range(len(feature_names))])
        xvec = numpy.array(rfe_svm.accuracy)
        plt.plot(numpy.array([i+1 for i in range(len(feature_names))]),
                 numpy.array(rfe_svm.accuracy),
                 color='b')
        plt.title("RFE-%s: Nb of features vs. %i fold Cross Validation Score" % (clf_name.upper(), FOLD))
        plt.xlabel("number of features")
        plt.ylabel("accuracy")
        plt.savefig(filename)
        plt.close('all')

        print
        print '*******************'
        print 'SUMMARY SVM-RANKING'
        for i in range(len(feature_names)):
            print '%02i: %s\t%f' % (i, ranked_features_svm[i], xvec[i])

        fp = open(os.path.join(self.study_dir, 'RFE-SVM_indices.txt'), 'w')
        for i in rfe_svm.ranking:
            fp.write('%i\n' % i)
        fp.close()

        fp = open(os.path.join(self.study_dir, 'RFE-SVM_features.txt'), 'w')
        for feat in ranked_features_svm:
            fp.write('%s\n' % feat)
        fp.close()

        # RFE-LDA
        rfe_lda = MyRFE()
        rfe_lda(X, y, clf_lda)
        clf_name = 'lda'
        ranked_features_lda = numpy.array(feature_names)[rfe_lda.ranking]
        filename = os.path.join(self.study_dir, 'rfe-%s_cv_accuracy.%s' % (clf_name, PLOT_SUFFIX))
        plt.figure(1)
        ax=plt.subplot(1,1,1)
        yvec = numpy.array([i+1 for i in range(len(feature_names))])
        xvec = numpy.array(rfe_lda.accuracy)
        plt.plot(numpy.array([i+1 for i in range(len(feature_names))]),
                 numpy.array(rfe_lda.accuracy),
                 color='b')
        plt.title("RFE-%s: Nb of features vs. %i fold Cross Validation Score" % (clf_name.upper(), FOLD))
        plt.xlabel("number of features")
        plt.ylabel("accuracy")
        plt.savefig(filename)
        plt.close('all')

        # plot a scatter plot matrix with the N most informative features
        N = 6
        #classnames = [COLORDICT.keys()[int(i)-1] for i in y]
        classnames = [self.CLASSNAMES[int(i)] for i in y]
        colorvec = [self.COLORDICT[name] for name in classnames]

        clf_name = 'svm'
        indices = rfe_svm.ranking[:N]
        subset_rfe = X[:, indices]
        filename = os.path.join(self.study_dir, "scatterplotmatrix_RFE%s_%ifeatures.%s" % (clf_name, N, PLOT_SUFFIX))
        self.spm(subset_rfe, filename, colnames=ranked_features_svm[:N],
                 color=colorvec)
        print 'summary: %s' % (clf_name)
        for i in range(N):
            print '%i\t%s' % (i, ranked_features_svm[i])

        clf_name = 'lda'
        indices = rfe_lda.ranking[:N]
        subset_rfe = X[:, indices]
        filename = os.path.join(self.study_dir, "scatterplotmatrix_RFE%s_%ifeatures.%s" % (clf_name, N, PLOT_SUFFIX))
        self.spm(subset_rfe, filename, colnames=ranked_features_lda[:N],
                 color=colorvec)
        print 'summary: %s' % (clf_name)
        for i in range(N):
            print '%i\t%s' % (i, ranked_features_lda[i])

        for N in [3, 5, 10, 15, 20]:
            print 'comparison of weights between SVM and LDA: ', N
            feature_indices = rfe_svm.ranking[:N]
            clf_lda.fit(X[:, feature_indices], y)
            clf_svm.fit(X[:, feature_indices], y)

            filename = os.path.join(self.study_dir, "scatterplot_RFE-comparison_LDA-RFE_%ifeatures.%s" % (N, PLOT_SUFFIX))

            #print clf_lda.coef_
            #print clf_lda.coef_.shape
            clf_lda_coef = clf_lda.coef_**2 / numpy.max(clf_lda.coef_**2)
            clf_svm_coef = clf_svm.coef_**2 / numpy.max(clf_svm.coef_**2)
            #print clf_lda_coef
            self.sp.single(clf_lda_coef, #numpy.concatenate(rfe_lda.detailed_score[N]),
                           clf_svm_coef, #numpy.concatenate(rfe_svm.detailed_score[N]),
                           filename,
                           xlabel='LDA', ylabel='SVM',
                           title='Feature Weights: %i selected features' % N,
                           edgecolor=(0.2, 0.2, 0.2),
                           axis=[-0.05, 1.05, -0.05, 1.05])

        #print 'optimal number of features: %i' % nb_optimal_features
        #for k in range(nb_optimal_features):
        #    print '\t'.join([str(e) for e in rank_score[k]])

        return

    def getWilcoxonScore(self, X, y):

        #args = [X[y==k] for k in np.unique(y)]
        all_classes = numpy.unique(y)
        ud_pval = []
        ud_teststat = []
        class_pairs = []
        for k in range(len(all_classes)):
            cl = all_classes[k]
            Xc = X[y==cl]
            nb_samples_cl, nb_features = Xc.shape
            for cln in all_classes[(k+1):]:
                Xcn = X[y==cln]
                test_allfeatures = [scipy.stats.ranksums(Xc[:,f], Xcn[:,f])
                                    for f in range(nb_features)]
                ud_pval.append([x[1] for x in test_allfeatures])
                ud_teststat.append([x[0] for x in test_allfeatures])
                class_pairs.append((cl, cln))
        pval = numpy.array(ud_pval)

        return pval, class_pairs

    def getWilcoxonScore2(self, X, y):

        #args = [X[y==k] for k in np.unique(y)]
        all_classes = numpy.unique(y)
        ud_pval = []
        ud_teststat = []
        class_pairs = []
        for k in range(len(all_classes)):
            cl = all_classes[k]
            Xc = X[y==cl]
            nb_samples_cl, nb_features = Xc.shape
            for cln in all_classes[(k+1):]:
                Xcn = X[y==cln]
                test_allfeatures = [scipy.stats.ranksums(Xc[:,f], Xcn[:,f])
                                    for f in range(nb_features)]
                ud_pval.append([x[1] for x in test_allfeatures])
                ud_teststat.append([x[0] for x in test_allfeatures])
                class_pairs.append((cl, cln))
        pval = numpy.array(ud_pval).min(axis=0)
        teststat = numpy.array(ud_teststat).min(axis=0)
        return (teststat, pval)


    def getUnivariateFeatureRanking(self, X, y, feature_names=None):
        if feature_names is None:
            feature_names = self.ts.getFeatureNames()

        if X.shape[1] != len(feature_names):
            # reread data (feature_names are not correct
            X, y = self.readDataSet()
            feature_names = self.ts.getFeatureNames()

        # p-value threshold with correction for multiple testing.
        alpha = 0.01 / len(feature_names)

        pval, class_pairs = self.getWilcoxonScore(X, y)

        # get the minimum (if there is one class pair that is distinguished, the features are useful)
        pval_min = pval.min(axis=0)

        # relevant features
        relevant_feature_indices = filter(lambda i: wilcoxon_pval[0][i] < alpha, range(len(wilcoxon_pval[0])))
        relevant_features_wilcoxon = [feature_names[i] for i in relevant_feature_indices]

        # ranking
        score = zip(feature_names, pval_min)
        score.sort(key=operator.itemgetter(-1))

        return score

    def test_univariateFeatureRanking(self):

#        ################################################################################
#        # Univariate feature selection
#        from sklearn.feature_selection import SelectFpr, f_classif
#        # As a scoring function, we use a F test for classification
#        # We use the default selection function: the 10% most significant
#        # features
#
#        selector = SelectFpr(f_classif, alpha=0.1)
#        selector.fit(x, y)
#        scores = -np.log10(selector._pvalues)
#        scores /= scores.max()
#        pl.bar(x_indices-.45, scores, width=.3,
#                label=r'Univariate score ($-Log(p_{value})$)',
#                color='g')

        X, y = self.readDataSet()
        feature_names = self.ts.getFeatureNames()

        #import numpy
        #inds = numpy.argsort(ages)
        #sortedPeople = numpy.take(people, inds)

        alpha = 0.01 / len(feature_names)

        chi2_score = sklearn.feature_selection.univariate_selection.chi2(X, y)
        chi2_pval = chi2_score[1]
        relevant_feature_indices = filter(lambda i: chi2_pval[i] < alpha, range(len(chi2_pval)))
        relevant_features_chi2 = [feature_names[i] for i in relevant_feature_indices]

        anova_score = sklearn.feature_selection.univariate_selection.f_classif(X, y)
        anova_pval = anova_score[1]
        relevant_feature_indices = filter(lambda i: anova_pval[i] < alpha, range(len(anova_pval)))
        relevant_features_anova = [feature_names[i] for i in relevant_feature_indices]

        wilcoxon_pval, class_pairs = self.getWilcoxonScore(X,y)
        relevant_feature_indices = filter(lambda i: wilcoxon_pval[0][i] < alpha, range(len(wilcoxon_pval[0])))
        relevant_features_wilcoxon = [feature_names[i] for i in relevant_feature_indices]

        print 'chi2: %i features' % len(relevant_features_chi2)
        print 'anova: %i features' % len(relevant_features_anova)
        print 'wilcoxon: %i features' % len(relevant_features_wilcoxon)
        print 'intersection (chi2 - anova): %i features' % len(filter(lambda x: x in relevant_features_anova,
                                                                      relevant_features_chi2))
        print 'intersection (chi2 - wilcoxon): %i features' % len(filter(lambda x: x in relevant_features_wilcoxon,
                                                                         relevant_features_chi2))
        print 'intersection (wilcoxon - anova): %i features' % len(filter(lambda x: x in relevant_features_anova,
                                                                          relevant_features_wilcoxon))

        #sklearn.feature_selection.univariate_selection.SelectFdr(score_func, alpha=0.050000000000000003)
        return



class Moritz_study(feature_projection_study):
    def __init__(self):
        settings_filename = "/Users/twalter/workspace/cecog/pysrc/scripts/EMBL/settings_files/lamin/settings_lamin_analysis.py"
        feature_projection_study.__init__(self, settings_filename)

        self.study_dir = '/Users/twalter/data/Moritz_cecog/study'
        if not os.path.isdir(self.study_dir):
            os.makedirs(self.study_dir)

        self.import_classnames = ['assembled',
                                  'disassembling',
                                  'disassembled']

        self.CLASSNAMES = {
                           1    : 'assembled',
                           2    : 'disassembling',
                           3    : 'disassembled'
                           }

        self.CLASSLABELS = {
                            'assembled'      : 1,
                            'disassembling'  : 2,
                            'disassembled'    : 3,
                            }
        self.COLORDICT = OrderedDict(
                                     [
                                      ('assembled', '#00ff00'),
                                      ('disassembling', '#800080'),
                                      ('disassembled', '#ff8000'),
                                      ]
                                      )


    def investigateDecisionValues(self):

        X, y = self.readDataSet(phenoClasses = self.import_classnames)
        feature_names = self.ts.getFeatureNames()
        classnames = [self.CLASSNAMES[int(i)] for i in y]

        clf = lda.LDA()
        clf.fit(X,y)

        #prob = clf.predict_proba(X)
        #log_prob = clf.predict_log_proba(X)
        dec = clf.decision_function(X)

        colorvec = [self.COLORDICT[name] for name in classnames]
        filename = os.path.join(self.study_dir, "decisionvalues_LDA_unreduced.%s" % PLOT_SUFFIX)
        self.spm(dec, filename,
                 colnames=['dec: %s' % self.CLASSNAMES[i+1] for i in range(dec.shape[1])],
                 color=colorvec)


        return

    def compareRFE(self):

        X, y = self.readDataSet(phenoClasses = self.import_classnames)
        feature_names = self.ts.getFeatureNames()
        classnames = [self.CLASSNAMES[int(i)] for i in y]

        avg_mat = numpy.array([numpy.mean(X[y==k,:], axis=0) for k in numpy.unique(y)])
        sign_select = numpy.sign(avg_mat[0] - avg_mat[1]) == numpy.sign(avg_mat[1] - avg_mat[2])
        Xred = X[:,sign_select]
        feature_names_red = numpy.array(feature_names)[sign_select]

        pval, class_pairs = self.getWilcoxonScore(Xred, y)
        max_score = pval.max(axis=0)
        min_score = pval.min(axis=0)

        Xredsig = Xred[:,min_score<0.01]
        feature_names_redsig = feature_names_red[min_score<0.01]

        #print Xredsig.shape
        #print feature_names_redsig.shape
        #print feature_names_redsig

        #for subset in []:
        #indices = range(len(feature_names_redsig))
        N = 5
        for k in range(len(feature_names_redsig)/N):
            indices = range(k*N, min((k+1)*N, len(feature_names_redsig)))
            curfeat = feature_names_redsig[indices]
            curX = Xredsig[:,indices]
            colorvec = [self.COLORDICT[name] for name in classnames]
            filename = os.path.join(self.study_dir, "scatterplotmatrix_direction_significance-k%i_%ifeatures.%s" % (k, N, PLOT_SUFFIX))
            self.spm(curX, filename, colnames=curfeat,
                     color=colorvec)

        Xredsig2c = Xredsig[y!=2,:]
        y2c=y[y!=2]
        print 'after preselection (direction and significance): %i features' % len(feature_names_redsig)
        print 'number of classes: %i' % len(numpy.unique(y2c))
        print Xredsig2c.shape
        feature_projection_study.compareRFE(self, Xredsig2c, y2c, feature_names_redsig.tolist())

        #self.study_dir = '/Users/twalter/data/Moritz_cecog/study_alternative'
        #feature_projection_study.compareRFE(self, Xredsig, y, feature_names_redsig.tolist())

        return

    def investigateFeatureSubset(self):


        N = 6

        #00: princ_gyration_x    0.928889
        #01: h2_2SET    0.986667
        #02: granu_close_volume_2    0.988889
        #03: n_wiavg    1.000000
        #04: princ_gyration_y    1.000000
        #05: granu_open_volume_1    1.000000

        N = 6
        fp = open('/Users/twalter/data/Moritz_cecog/study/RFE-SVM_indices.txt', 'r')
        feature_indices = [int(x) for x in fp.readlines()]
        fp.close()

        fp = open('/Users/twalter/data/Moritz_cecog/study/RFE-SVM_features.txt', 'r')
        feature_names = [x.strip() for x in fp.readlines()]
        fp.close()
        feature_projection_study.investigateFeatureSubset(self, feature_indices, feature_names, N)

        #feature_indices = []
        #feature_names = ['princ_gyration_x', 'h2_2SET',
        #                 'granu_close_volume_2', 'n_wiavg',
        #                 'princ_gyration_y', 'granu_open_volume_1']
        feature_projection_study.investigateFeatureSubset(self, feature_indices,
                                                          feature_names, N)

        return

class JKH_study(feature_projection_study):
    def __init__(self):
        settings_filename = "/Users/twalter/workspace/cecog/pysrc/scripts/EMBL/settings_files/chromosome_condensation/chromosome_condensation_postprocessing.py"
        feature_projection_study.__init__(self, settings_filename)

        self.study_dir = '/Users/twalter/data/JKH/study'
        if not os.path.isdir(self.study_dir):
            os.makedirs(self.study_dir)

        self.import_classnames = ['interphase',
                                  'early_prophase',
                                  'mid_prophase']

        self.CLASSNAMES = {
                           1    : 'interphase',
                           2    : 'early_prophase',
                           3    : 'mid_prophase',
                           4    : 'prometaphase',
                           5    : 'metaphase',
                           6    : 'early_anaphase',
                           7    : 'late_anaphase',
                           8    : 'apoptosis',
                           9    : 'artefact',
                           10   : 'out-of-focus',
                           }

        self.CLASSLABELS = {
                            'interphase'      : 1,
                            'early_prophase'  : 2,
                            'mid_prophase'    : 3,
                            'prometaphase'    : 4,
                            'metaphase'       : 5,
                            'early_anaphase'  : 6,
                            'late_anaphase'   : 7,
                            'apoptosis'       : 8,
                            'artefact'        : 9,
                            'out-of-focus'    : 10,
                            }

        self.COLORDICT = OrderedDict(
                                     [
                                      ('interphase', '#fe761b'),
                                      #('early_prophase', '#a9e8ef'),
                                      ('early_prophase', '#00ff33'),
                                      ('mid_prophase', '#4e9dff'),
                                      ('prometaphase', '#00458a'),
                                      ('metaphase', '#3af33a'),
                                      ('early_anaphase', '#40c914'),
                                      ('late_anaphase', '#2d8f0c'),
                                      ('apoptosis', '#fe1710'),
                                      ('artefact', '#fe51c3'),
                                      ('out-of-focus', '#9321fe'),
                                      ]
                                     )

    def compareRFE(self):

        X, y = self.readDataSet()
        feature_names = self.ts.getFeatureNames()

        feature_projection_study.compareRFE(self, X, y, feature_names)
        return


    def investigateFeatureSubset(self):
        N = 6
        fp = open('/Users/twalter/data/JKH/study/RFE-SVM_indices.txt', 'r')
        feature_indices = [int(x) for x in fp.readlines()]
        fp.close()

        fp = open('/Users/twalter/data/JKH/study/RFE-SVM_features.txt', 'r')
        feature_names = [x.strip() for x in fp.readlines()]
        fp.close()
        feature_projection_study.investigateFeatureSubset(self, feature_indices, feature_names, N)

        return

