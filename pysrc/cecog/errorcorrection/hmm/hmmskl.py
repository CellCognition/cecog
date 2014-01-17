"""
skhmm.py

fixes some issues of sklearn.hmm

1) Epsilon value in the normalize function
2) check_input_symbols is disabled (returns always True)
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import numpy as np
from sklearn import hmm
from sklearn.utils.extmath import logsumexp

from cecog.tc3 import normalize

EPS = 1e-99
decoder_algorithms = ("viterbi", "map")


class MultinomialHMM(hmm.MultinomialHMM):

    def __init__(self, *args, **kw):
        super(MultinomialHMM, self).__init__(*args, **kw)

    def _get_startprob(self, *args, **kw):
        return super(MultinomialHMM, self)._get_startprob(*args, **kw)

    def _set_startprob(self, startprob):
        if startprob is None:
            startprob = np.tile(1.0 / self.n_components, self.n_components)
        else:
            startprob = np.asarray(startprob, dtype=np.float)

        if not np.alltrue(startprob):
            startprob = normalize(startprob, eps=EPS)

        if len(startprob) != self.n_components:
            raise ValueError('startprob must have length n_components')
        if not np.allclose(np.sum(startprob), 1.0):
            raise ValueError('startprob must sum to 1.0')

        self._log_startprob = np.log(np.asarray(startprob).copy())

    startprob_ = property(_get_startprob, _set_startprob)

    def _get_transmat(self, *args, **kw):
        return super(MultinomialHMM, self)._get_transmat(*args, **kw)

    def _set_transmat(self, transmat):

        if transmat is None:
            transmat = np.tile(1.0 / self.n_components,
                               (self.n_components, self.n_components))

        if not np.alltrue(transmat):
            transmat = normalize(transmat, axis=1, eps=EPS)

        if (np.asarray(transmat).shape \
            != (self.n_components, self.n_components)):
            raise ValueError('transmat must have shape '
                             '(n_components, n_components)')


        if not np.all(np.allclose(np.sum(transmat, axis=1), 1.0)):
            raise ValueError('Rows of transmat must sum to 1.0')

        self._log_transmat = np.log(np.asarray(transmat).copy())
        underflow_idx = np.isnan(self._log_transmat)
        self._log_transmat[underflow_idx] = -np.inf

    transmat_ = property(_get_transmat, _set_transmat)

    def _check_input_symbols(self, obs):
        return True

        # """Sanity checks on the emissions.."""
        # assert isinstance(obs, np.ndarray)

        # # input symbols must be integer
        # if symbols.dtype.kind != 'i':
        #     return False

        # # input too short
        # if len(symbols) < 2:
        #     return False

        # # input contains negative intigers
        # if np.any(symbols < 0):
        #     return False

        # return True

    def fit(self, obs):

        # same implementation as in sklearn, but returns the learning curve
        if self.algorithm not in decoder_algorithms:
            self._algorithm = "viterbi"

        self._init(obs, self.init_params)

        logprob = []
        for i in range(self.n_iter):
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
                break

            # Maximization step
            self._do_mstep(stats, self.params)

        return logprob
