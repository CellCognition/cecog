"""
hmm.py

Subclassing sklearn MultinomialHMM

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import warnings
import numpy as np
import sklearn.hmm as hmm
from sklearn.utils.extmath import logsumexp


decoder_algorithms = hmm.decoder_algorithms

class MultinomialHMM(hmm.MultinomialHMM):

    def __init__(self, *args, **kw):
        hmm.MultinomialHMM.__init__(self, *args, **kw)

    def fit(self, obs, **kwargs):

        converged = False

        if kwargs:
            warnings.warn("Setting parameters in the 'fit' method is"
                          "deprecated and will be removed in 0.14. Set it on "
                          "initialization instead.", DeprecationWarning,
                          stacklevel=2)
            # initialisations for in case the user still adds parameters to fit
            # so things don't break
            if 'n_iter' in kwargs:
                self.n_iter = kwargs['n_iter']
            if 'thresh' in kwargs:
                self.thresh = kwargs['thresh']
            if 'params' in kwargs:
                self.params = kwargs['params']
            if 'init_params' in kwargs:
                self.init_params = kwargs['init_params']

        if self.algorithm not in decoder_algorithms:
            self._algorithm = "viterbi"

        self._init(obs, self.init_params)

        logprob = []
        for i in xrange(self.n_iter):
            # Expectation step
            stats = self._initialize_sufficient_statistics()
            curr_logprob = 0
            for seq in obs:
                framelogprob = self._compute_log_likelihood(seq)
                lpr, fwdlattice = self._do_forward_pass(framelogprob)
                bwdlattice = self._do_backward_pass(framelogprob)
                gamma = fwdlattice + bwdlattice
                posteriors = np.exp(gamma.T - logsumexp(gamma, axis=1)).T
                curr_logprob += lpr
                self._accumulate_sufficient_statistics(
                    stats, seq, framelogprob, posteriors, fwdlattice,
                    bwdlattice, self.params)
            logprob.append(curr_logprob)

            # Check for convergence.
            if i > 0 and abs(logprob[-1] - logprob[-2]) < self.thresh:
                converged = True
                break

            # Maximization step
            self._do_mstep(stats, self.params)

        return converged, i
