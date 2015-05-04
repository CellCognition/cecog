"""
matrix.py

Matrix plots for e.g. hmm transitons, emission matrices
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["hmm_matrix"]


from matplotlib import cm
from matplotlib import pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator


def hmm_matrix(matrix, xticks=None, yticks=None, text=None, axes=None,
               cmap=None, xlabel=None):

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(1, 1 ,1)

    axes.set_aspect('equal')
    axes.set_frame_on(True)

    if xlabel is not None:
        axes.set_xlabel(xlabel)

    if text is not None:
        axes.text(matrix.shape[1]/2.0,
                  -3, text, fontsize=12, horizontalalignment='center')

    axes.matshow(matrix, cmap=cm.Greens)

    if xticks is not None:
        axes.xaxis.set_major_locator(FixedLocator(range(matrix.shape[1])))
        axes.set_xticklabels(xticks, rotation=45, size=8)
    else:
        axes.xaxis.set_major_locator(NullLocator())

    if yticks is not None:
        axes.yaxis.set_major_locator(FixedLocator(range(matrix.shape[0])))
        axes.set_yticklabels(yticks, rotation=45, size=8)
    else:
        axes.yaxis.set_major_locator(NullLocator())
    axes.grid(False)

    def color(value):
        if value < 0.5:
            return (0.0, 0.0, 0.0, 1.0)
        else:
            return (1.0, 1.0, 1.0, 1.0)

    idx = ((i, j) for i in xrange(matrix.shape[1])
           for j in xrange(matrix.shape[0]))
    for i, j in idx:
        axes.text(i, j, '%.2f' %(matrix[j, i]), horizontalalignment='center',
        verticalalignment='center', fontsize=7, color=color(matrix[j, i]))

    return axes.get_figure()
