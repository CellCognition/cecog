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
# from cecog.tc3 import normalize

EPS = 1e-99

class GaussianHMM(hmm.GaussianHMM):
    """Dummy class to stay compatible.  """
    pass

class MultinomialHMM(hmm.MultinomialHMM):

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
