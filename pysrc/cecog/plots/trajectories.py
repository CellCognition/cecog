"""
plots.py

module for cell-trajectory plots

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['trajectories_dict', 'trajectories', 'sort_tracks']


import numpy as np
import pylab as pl
from matplotlib import mpl
from cecog.colors import DCMAP

def sort_tracks(label_matrix, labels, reverse=False):

    if label_matrix.ndim == 1:
        label_matrix.shape = 1, -1
    # return if nothing to sort
    if label_matrix.ndim == 1 or label_matrix.shape[0] <= 1 :
        return label_matrix
    keyfunc = lambda track: len([t for t in track if t in labels])
    slm = np.array(sorted(label_matrix, key=keyfunc, reverse=reverse))
    return slm

def trajectories_dict(data, labels=None, reverse=False, window_title=None,
                      cmap=DCMAP):
    """Plot a dictionary of tracks"""

    fig = pl.figure(figsize=(len(data)*4, 4.1))
    fig.subplots_adjust(top=0.8, left=0.05, right=0.95)

    if window_title is not None:
        fig.canvas.set_window_title(window_title)

    nplots = len(data)
    for i, title in enumerate(sorted(data), start=1):
        tracks = data[title]
        ax =  fig.add_subplot(1, nplots, i, aspect='equal')

        if labels is not None:
            tracks = sort_tracks(tracks, labels, reverse)

        ax.matshow(tracks, cmap=cmap)
        if tracks.shape[0] > tracks.shape[1]:
            ax.set_aspect("auto")
        ax.set_title(title)
        ax.set_xlabel("frames")
        if i == 1:
            ax.set_ylabel("# trajectories")
        ax.tick_params(labeltop=False, labelbottom=True)
    return fig

def trajectories(tracks, labels=None, reverse=False, title=None,
                 window_title=None, cmap=DCMAP,
                 norm=None, axes=None):

    if axes is None:
        fig = pl.figure()
        axes =  fig.add_subplot(1, 1, 1, frameon=False, aspect='equal')

    if window_title is not None:
        axes.get_figure().canvas.set_window_title(window_title)

    if labels is not None:
        tracks = sort_tracks(tracks, labels, reverse)

    axes.matshow(tracks, cmap=cmap, norm=norm)

    if title is not None:
        axes.set_title(title)

    axes.set_xlabel("frames")
    axes.set_ylabel("trajectories")
    axes.tick_params(labeltop=False, labelbottom=True)

    if tracks.shape[0] > tracks.shape[1]:
            axes.set_aspect("auto")

    return axes.get_figure()
