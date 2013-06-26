"""
tc3.py

Implementation of temporal constraint combinatorial clustering

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ =['normalize', 'TemporalClustering', 'TC3Error']

import numpy as np
import scipy
import scipy.spatial.distance as ssd
import sklearn.mixture as mixture
import sklearn.hmm as hmm

from cecog.tc3 import TC3Container
from cecog.tc3 import TC3Params, GmmParams, DHmmParams, CHmmParams

np.set_printoptions(precision=2)
EPS = np.spacing(1)

# recycled from sklearn.hmm be able to control the eps parameter!
def normalize(A, axis=None, eps=EPS):
    A += eps
    Asum = A.sum(axis)
    if axis and A.ndim > 1:
        # Make sure we don't divide by zero.
        Asum[Asum == 0] = 1
        shape = list(A.shape)
        shape[axis] = 1
        Asum.shape = shape
    return A / Asum


class TC3Error(Exception):
    pass


class TemporalClustering(object):

    # 100 might be a problem if one images only e.g. 5 wells on a plate
    MAX_TRACK_LENGTH = 100

    def __init__(self, n_frames, n_tracks, n_clusters, binary_tracks):
        super(TemporalClustering, self).__init__()
        self.n_frames = n_frames
        self.n_tracks = n_tracks
        self.n_clusters = n_clusters
        self.btracks = binary_tracks

        if n_frames > self.MAX_TRACK_LENGTH:
            raise TC3Error("Number of frames must not be larger than %d"
                           %self.MAX_TRACK_LENGTH)
        if n_clusters <= 1:
            raise TC3Error("Number of clusters must be larger than 1")

    @classmethod
    def set_max_track_lenght(cls, max_lenght):
        cls.MAX_TRACK_LENGTH = max_lenght

    def __repr__(self):
        return "TC3(n_frames=%s, n_tracks=%s, n_clusters=%s)" \
            %(self.n_frames,self.n_tracks, self.n_clusters)

    @property
    def startprob(self, eps=EPS):
        """Estimate start probabilities for the hidden markov models as
        (1-eps, eps/n, eps/n,..), where n is the number of states.
        """
        sprob = np.ones(self.n_clusters)*eps/(self.n_clusters-1)
        sprob[0] = 1 - eps
        return sprob

    def ntc3(self, nframes, nclusters, min_cluster_size):
        """Calculates the number of all possible ways to cluster using TC3."""

        # Relation between TC3 and binomial coefficients
        if nclusters > nframes:
            return 0
        else:
            return scipy.misc.comb(nframes-(min_cluster_size-1)*nclusters-1,
                                   nclusters-1, exact=True)

    def get_interval_matrix(self, t, k, m):
        """
        t - number of frames
        k - number of clusters
        m - minimal cluster size
        returns: A matrix that represents all possible ways to assign t frames
        into k clusters
        """
        intervalMatrix = []
        if k == 1:
            intervalMatrix = np.array([[t]])
        else:
            if (k*m > t) : m = t//k
            for i in range(m,t-(k-1)*m+1):
                tmp = np.hstack((np.tile(i,(self.ntc3(t-i, k-1, m),1)),
                                 self.get_interval_matrix(t-i,k-1,m)))
                if len(intervalMatrix) == 0:
                    intervalMatrix = tmp
                else:
                    intervalMatrix = np.vstack((intervalMatrix, tmp))
        return intervalMatrix

    def _tc3_per_track(self, data, k, m):
        """
        data - data sequence
        k - number of clusters
        m - minimal cluster size
        returns: Final cluster assignment is found by TC3. Clusters are
        mapped to class labels.
        """
        t = data.shape[0]
        if (t < k) : # When t is smaller than k
            intLabels = 0

        intervalMatrix = self.get_interval_matrix(t, k, m)
        r, c = intervalMatrix.shape
        obj = []
        intLabels = []

        for i in range(0, r):
            iM1 = 0
            iM2 = 0
            d = 0
            for j in range(0, c):
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

    def tc3_clustering(self, data, min_cluster_size) :
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

        assert data.ndim == 2

        if data.size == 0:
            raise TC3Error('Can not perform tc3 on empty array')

        k = self.n_clusters
        labels = np.zeros((self.n_tracks, self.n_frames), dtype=int)
        # estimate class labels using TC3
        for i in range(0,self.n_tracks) :
            Rdata = data[i*self.n_frames:(i+1)*self.n_frames, :]

            indRange = np.nonzero(self.btracks[i, :]==1)

            if (len(indRange) == 0) and i > 1 :
                labels[i, :] = labels[i-1, :]
            else :
                k1 = 2
                intV = range(0,indRange[0][0])
                # only 2 classes, no mcs constraint
                intLabels = self._tc3_per_track(Rdata[intV,:],k1,1)
                labels[i, intV] = intLabels

                # mitosis: prometa, meta, ana, telo
                k2 = k-k1
                intV = np.arange(indRange[0][0],indRange[-1][-1]+1)
                intLabels = self._tc3_per_track(Rdata[intV,:], k2,
                                                min_cluster_size) + k1
                labels[i, intV] = intLabels

        return TC3Container('TC3', TC3Params(self.n_clusters), labels)

    def tc3_gmm(self, data, labels, covariance_type='full', sharedcov=True) :

        gmm = mixture.GMM(n_components=self.n_clusters,
                          covariance_type=covariance_type,
                          init_params='',
                          n_iter=1)
        # restricting EM to only one iteration does not make sense at all!
        # No covergence criteria is met and no arrangement against convergence
        # against local minima. Just changing tc3 labels to have labels
        # a little different.

        # initialize gmm separatly hopefully not loosing the
        # label anntotation
        gmm.means_, gmm.covars_, gmm.weights_ = \
            self._estimate_gmm_startparams(data, labels, sharedcov=sharedcov)
        gmm.fit(data)
        prob = gmm.predict_proba(data)

        labels = gmm.predict(data)
        labels = labels.reshape(self.n_tracks, self.n_frames)

        model_params = GmmParams(gmm.means_, gmm.covars_, gmm.weights_, prob)
        return TC3Container('GMM', model_params, labels)

    def _estimate_gmm_startparams(self, data, labels, sharedcov=False):
        """Estimate inital parameter for a Gaussian Mixture Model given the data
        and a inital label matrix.
        """

        n_samples, n_features = data.shape

        mu = np.zeros((self.n_clusters, n_features))
        covar = np.zeros((n_features, n_features, self.n_clusters))
        weights = np.zeros((self.n_clusters))

        for i in range(self.n_clusters) :
            X = data[labels==i, :]
            mu[i,:] = np.mean(X,0)
            if sharedcov :
                covar[:, :, i] = np.cov(data.T)
            else :
                covar[:, :, i] = np.cov(X.T)
            pts = X.shape[0]
            weights[i] = pts/float(n_samples)

        return mu, covar.T, weights

    def _estimate_emission_matrix(self, eps=EPS):
        """Estimates the emission matrix for a Hidden Markov Model as 1-eps for
        diagonal elements and eps/(nclusters-1) for off diagonal elements i.e.

        It is assumed to have the same number of states and signals and that a state
        almost certainly emits one destinct signal.
        """
        emis = np.eye(self.n_clusters) + eps/(self.n_clusters-1)
        emis[range(self.n_clusters), range(self.n_clusters)] = 1.0 - eps
        return emis

    def _estimate_transmat(self, tracks, left2right):
        """Estimates the transition probaility according to all observations.

        If left2right is True, all matrix element, except the diagonal and the
        first off diagonal are zero.
        """
        states = np.unique(tracks)
        states.sort()
        transmat = np.zeros((states.size, states.size), dtype="float64")
        _tracks = tracks.flatten()
        for i, label in enumerate(_tracks):
            for state in states:
                try:
                    if (_tracks[i+1] == state) and (label >= state):
                        transmat[state, label] += 1
                except IndexError:
                    pass

        # make transisition cyclic
        transmat[-1, 0] = transmat[0,-1]

        # enforce a pure left-to-right model
        if left2right:
            ti = np.eye(states.size)
            idx = np.arange(0, states.size)
            ti[-1, 0] = 1
            ti[idx[:-1], idx[:-1]+1] = 1
            transmat *= ti

        return normalize(transmat, axis=1)

    def tc3_gmm_dhmm(self, tracks, left2right=False):
        assert np.issubdtype(tracks.dtype, int)

        trans = self._estimate_transmat(tracks, left2right)
        emis = self._estimate_emission_matrix()

        dhmm = hmm.MultinomialHMM(n_components=self.n_clusters,
                                  transmat=trans,
                                  startprob=self.startprob,
                                  # init_params = '',
                                  n_iter=100)
        dhmm.emissionprob_ = emis

        tracks2 = []
        for track in tracks:
            tracks2.append(dhmm.predict(track))
        labels = np.array(tracks2)

        model_params = DHmmParams(dhmm.emissionprob_, dhmm.transmat_)
        data = TC3Container('DHMM', model_params, labels)
        return data

    def tc3_gmm_chmm(self, data, means, covars, transmat):
        """Setup a Hidden Markov Model with Gausian emissions and predict all tracks
        at once for the whole data set."""

        chmm =  hmm.GaussianHMM(n_components=self.n_clusters,
                               transmat=transmat,
                               startprob=self.startprob,
                               covariance_type='full',
                               n_iter=1000)
        chmm.means_ = means
        chmm.covars_ = covars

        # Predict all tracks at once. The difference seems to be negligible
        labels = chmm.predict(data)
        labels = labels.reshape(self.n_tracks, self.n_frames)
        model_params = CHmmParams(chmm.means_, chmm.covars_, chmm.transmat_)
        data = TC3Container('CHMM', model_params, labels)
        return data
