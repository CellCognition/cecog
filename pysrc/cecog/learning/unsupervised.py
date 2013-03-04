'''
Created on Nov 24, 2011

@author: zhongq
'''

import numpy as np
import scipy.misc as sm
import scipy.spatial.distance as ssd
import math
import warnings
import sklearn.mixture as mixture
import util
import sklearn.hmm as hmm
import collections

class TemporalClustering:

    def __init__(self, dim, n_clusters, subgraph=[]):
        self.n_frames = dim[0]
        self.n_tracks = dim[1]
        self.n_clusters = n_clusters
        self.subgraph = subgraph

    def ntc3(self, t, k, m):
        """
        t - number of frames
        k - number of clusters
        m - minimal cluster size
        returns: The number of all possible ways to cluster using TC3
        """
        if t > 100 : exit('Number of frames should be no larger than 100');
        if k > t : return 0 #exit('Number of clusters is larger than frames');
        # Relation between TC3 and binomial coefficients
        return  sm.comb(t-(m-1)*k-1, k-1, exact=True)

    def get_interval_matrix(self, t, k, m):
        """
        t - number of frames
        k - number of clusters
        m - minimal cluster size
        returns: A matrix that represents all possible ways to assign t frames into k clusters
        """
        intervalMatrix = [];
        if k == 1 : intervalMatrix = np.array([[t]])
        else :
            if (k*m > t) : m = t//k
            for i in range(m,t-(k-1)*m+1):
                tmp = np.hstack((np.tile(i,(self.ntc3(t-i, k-1, m),1)), self.get_interval_matrix(t-i,k-1,m)))
                if len(intervalMatrix) == 0 : intervalMatrix = tmp
                else : intervalMatrix = np.vstack((intervalMatrix, tmp))
        return intervalMatrix

    def _tc3_per_track(self, data, k, m):
        """
        data - data sequence
        k - number of clusters
        m - minimal cluster size
        returns: Final cluster assignment is found by TC3. Clusters are mapped to class labels.
        """
        t = data.shape[0]
        if (t < k) : # When t is smaller than k
            intLabels = 0;
            # warnings.warn('TC3:ImproperCluster','t < k: Number of frames is smaller than the number of clusters. Only one label is returned.')

        intervalMatrix = self.get_interval_matrix(t,k,m)
        r,c = intervalMatrix.shape
        obj = []
        intLabels = []

        for i in range(0,r) :
            iM1 = 0;
            iM2 = 0;
            d = 0;
            for j in range(0,c) :
                if j > 0 : iM1 = iM1 + intervalMatrix[i,j-1]
                iM2 = iM2 + int(intervalMatrix[i,j])
                iM1 = int(iM1)
                intv = range(iM1,iM2)
                d =  d + sum(ssd.cdist(data[intv,:],np.array([np.mean(data[intv,:], axis = 0)])))
            obj.append(d)

        objN = np.asarray(obj)
        ind = objN.argmin()

        for j in range(0,k) :
            intLabels = np.append(intLabels, np.kron(np.ones((1,intervalMatrix[ind,j])),j))
        return intLabels

    def tc3_clustering(self, data, m) :
        """
        data - data sequence, [nCells x nFeaures], which can be reshaped to
        [nTracks x nFrames x nFeaures], where nCells = nTracks x nFrames.
        m - minimal cluster size
        returns: TC3 label sequences formed by reshaping X according to data.dim. They are
                 estimated by TC3 per cell trajectory. Due to boundary of binary clustering
                 and limited frames of prophase, one pattern is 1|23...k|1 and the other
                 is 12|34...k|1, where |34...k| is the mitotic subgraph defined in the
                 paper, and |23...k| is the alternative. When considering both cases, then
                 the algorithm is more general. The preference of either subgraph assignments
                 can be determined by AIC or BIC in an unsupervised way.
        """
        k = self.n_clusters
        labelMatrix = np.zeros((self.n_tracks, self.n_frames));
        # estimate class labels using TC3
        for i in range(0,self.n_tracks) :
            Rdata = data[i*self.n_frames:(i+1)*self.n_frames, :]

            # subgraph
            if len(self.subgraph) == 0 :
                intLabels = self._tc3_per_track(Rdata,k+1,constraint=True) # k+1 -> data is cyclic
                intLabels[intLabels == k+1] = 0
                labelMatrix[i, :] = intLabels
                indRange = []
            else :
                indRange = np.nonzero(self.subgraph[i, :] == 1)

            if (len(indRange) == 0) and i > 1 :
                labelMatrix[i, :] = labelMatrix[i-1, :]
            else :
                ###########
                # 12|3456|1
                ###########
                # interphase and prometaphase/Aster
                k1 = 2;
                intV = range(0,indRange[0][0])
                # only 2 classes, no mcs constraint
                intLabels = self._tc3_per_track(Rdata[intV,:],k1,1)
                labelMatrix[i,intV] = intLabels

                # mitosis: prometa, meta, ana, telo
                k2 = k-k1;
                intV = np.arange(indRange[0][0],indRange[-1][-1]+1)
                intLabels = self._tc3_per_track(Rdata[intV,:],k2,m) + k1;
                labelMatrix[i, intV] = intLabels;

        # matrix format [num_tracks x num_frames]
        labels_tc3_matrix = labelMatrix
        # vector format [1 x num_tracks * num_frames]
        labels_tc3_vec = labels_tc3_matrix.flatten()
        tc3 = {'label_matrix': labels_tc3_matrix,
               'labels': labels_tc3_vec,
               'name': 'TC3'}
        return tc3

    def tc3_gmm(self, data, labels, covariance_type='full', sharedcov=True) :

        g = mixture.GMM(n_components=self.n_clusters,
                        covariance_type=covariance_type,
                        init_params='',
                        n_iter=1)
        g.means_, g.covars_, g.weights_ = \
            self._gmm_int_parameters(data, labels, sharedcov=sharedcov)
        # restrict EM to only one iteration
        g.fit(data)
        # vector format [1 x num_tracks * num_frames]
        labels_tc3gmm_vec = g.predict(data)
        # matrix format [num_tracks x num_frames]
        labels_tc3gmm_matrix = labels_tc3gmm_vec.reshape(self.n_tracks, self.n_frames)
        tc3_gmm = {'label_matrix': labels_tc3gmm_matrix,
                   'labels': labels_tc3gmm_vec,
                   'model': g, 'name': 'TC3+GMM'}
        return tc3_gmm

    def tc3_gmm_dhmm(self, labels):

        # a small error term
        eps = 1e-6
        # estimate initial transition matrix
        trans = np.zeros((self.n_clusters,self.n_clusters))
        hist, bin_edges = np.histogram(labels, bins=self.n_clusters)
        for i in range(0,self.n_clusters) :
            if (i<self.n_clusters-1) :
                trans[i,i:i+2] += [hist[i]/(hist[i]+hist[i+1]), hist[i+1]/(hist[i]+hist[i+1])]
            else :
                trans[i,0] += hist[i]/(hist[i]+hist[0])
                trans[i,-1] += hist[0]/(hist[i]+hist[0])
        trans = trans + eps
        trans /= trans.sum(axis=1)[:, np.newaxis]
        # start probability: [1, 0, 0, ...]
        sprob = np.zeros((1,self.n_clusters)).flatten()+eps/(self.n_clusters-1)
        sprob[0] = 1-eps
        # initialize DHMM
        dhmm = hmm.MultinomialHMM(n_components=self.n_clusters,
                                  transmat=trans,
                                  startprob=sprob,
                                  init_params ='')
        # emission probability, identity matrix with predefined small errors.
        emis = np.eye(self.n_clusters) + eps/(self.n_clusters-1)
        emis[range(self.n_clusters),range(self.n_clusters)] = 1-eps;
        dhmm.emissionprob_ = emis;
        # learning the DHMM parameters
        # default n_iter=10, thresh=1e-2
        dhmm.fit([labels.flatten()])
        # with EM update
        dhmm.emissionprob_ = emis
        # vector format
        labels_tc3gmmdhmm_vec = dhmm.predict(labels.flatten())
        # matrix format
        labels_tc3gmmdhmm_matrix = labels_tc3gmmdhmm_vec.reshape(self.n_tracks,self.n_frames)
        para = collections.namedtuple('para', ['transmat', 'emissionprob'])
        tc3_gmm_dhmm = {'label_matrix': labels_tc3gmmdhmm_matrix,
                        'labels': labels_tc3gmmdhmm_vec,
                        'model': para(dhmm.transmat_, dhmm.emissionprob_),
                        'name': 'TC3+GMM+DHMM'}
        return tc3_gmm_dhmm

    def tc3_gmm_chmm(self, data, gmm_model, dhmm_model):
        eps = np.spacing(1)
        sprob = np.zeros((1,self.n_clusters)).flatten()+eps/(self.n_clusters-1)
        sprob[0] = 1-eps
        chmm = hmm.GaussianHMM(n_components=self.n_clusters,
                               transmat=dhmm_model.transmat,
                               startprob=sprob,
                               covariance_type='full',
                               init_params ='',
                               n_iter=1)
        chmm.means_ = gmm_model.means_
        chmm.covars_ = gmm_model.covars_
        # restrict EM to only one iteration
        chmm.fit([data])
        # vector format [1 x num_tracks * num_frames]
        labels_tc3gmmchmm_vec = chmm.predict(data)
        # matrix format [num_tracks x num_frames]
        labels_tc3gmmchmm_matrix = labels_tc3gmmchmm_vec.reshape( \
            self.n_tracks,self.n_frames)
        para = collections.namedtuple('para', ['transmat', 'covars','means'])
        tc3_gmm_chmm = {'label_matrix': labels_tc3gmmchmm_matrix,
                        'labels': labels_tc3gmmchmm_vec,
                        'chmm_model': para( chmm.transmat_,
                                            chmm.covars_, chmm.means_),
                        'name': 'TC3+GMM+CHMM'}
        return tc3_gmm_chmm

    def __repr__(self):
        return "TC3(n_frames=%s, n_tracks=%s, n_clusters=%s)" \
            %(self.n_frames,self.n_tracks, self.n_clusters)

    @property
    def n_frames(self):
        """Number of frames."""
        return self.n_frames

    def n_tracks(self):
        """Number of tracks."""
        return self.n_tracks

    def _get_n_clusters(self):
        """Number of clusters."""
        return self.n_clusters

    def _set_n_clusters(self, n_clusters):
        if n_clusters < 1:
            raise ValueError('Number of clusters must be greater than one')
        self.n_clusters = n_clusters

    n_clusters = property(_get_n_clusters, _set_n_clusters)

    def _gmm_int_parameters(self,data,labels,sharedcov=False) :

        n = data.shape[0]
        n_features =  data.shape[1]
        mu = np.zeros((self.n_clusters, n_features))
        Sigma = np.zeros((n_features, n_features, self.n_clusters))
        p = np.zeros((self.n_clusters))

        for i in range(self.n_clusters) :
            X = data[labels==i, :]
            mu[i,:] = np.mean(X,0)
            if sharedcov :
                Sigma[:,:,i] = np.cov(data.T)
            else :
                Sigma[:,:,i] = np.cov(X.T)
            pts = X.shape[0]
            p[i] = pts/float(n)
        return [mu, Sigma.T, p]

    @staticmethod
    def mk_stochastic(k):
        """function [T,Z] = mk_stochastic(T)
        MK_STOCHASTIC ensure the matrix is a stochastic matrix,
        i.e., the sum over the last dimension is 1.
        """
        raw_A = np.random.uniform( size = k * k ).reshape( ( k, k ) )
        return ( raw_A.T / raw_A.T.sum( 0 ) ).T
