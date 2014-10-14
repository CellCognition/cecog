"""
hmm.py

Plot a Hidden Markov Model given the transition matrix

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ["hmm_network"]

import os
import textwrap

from matplotlib import patches
from matplotlib import pyplot as plt
from matplotlib.colors import hex2color
import numpy as np


def _arrow_coords(x0, y0, i, j, rad):
    phi = np.arctan2(y0[j]- y0[i],  x0[j]- x0[i])
    cosp = np.cos(phi)
    sinp = np.sin(phi)

    x = x0[i] + rad*cosp
    y = y0[i] + rad*sinp
    dx = x0[j] - x0[i] - 2*rad*cosp
    dy = y0[j] - y0[i] - 2*rad*sinp

    return x, y, dx, dy

def _alpha(x, c=3.5):
    # Sometimes the probabilietes are almost zero
    # --> make them a bit more visible, just for convenience
    return max(1-np.exp(-x*c), 0.001)

def _connectionsstyle(phi, rad=30):
    phi = np.degrees(phi)
    return "arc,angleA=%d,angleB=%d,armA=50,armB=50,rad=%d" %(phi+90, phi, rad)

def hmm_network(transmat, classes, rad=0.15, title='hmm network', axes=None):
    """Plot a network of a hidden markov model providing the transition matrix
    and the classes (dict of labels, hexcolors).
    """
    n = len(classes)
    phi = np.linspace(0, 2*np.pi, n, endpoint=False)
    x = (np.cos(phi) - np.sin(phi))/np.sqrt(2)
    y = (np.sin(phi) + np.cos(phi))/np.sqrt(2)

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(1, 1 ,1)

    axes.set_aspect('equal')
    axes.set_frame_on(False)

    title = os.linesep.join(textwrap.wrap(title, 35))
    axes.set_title(title)

    # add arrows
    for i in xrange(n):
        for j in xrange(n):
            # arrows btw. different classes

            if i != j:
                x_, y_, dx, dy = _arrow_coords(x, y, i, j, rad)
                axes.arrow(x_, y_, dx, dy, width=0.015, fc='k', ec='k',
                           head_length=0.15, length_includes_head=True,
                           head_width=0.075, alpha=_alpha(transmat[i, j]))
            else:
                # arrow loop
                phi2 = phi[i] + np.pi/4.
                x1 = (x[i] + rad*np.cos(phi2-np.pi/4.), y[i]+rad*np.sin(phi2-np.pi/4.))
                x2 = (x[i] + rad*np.cos(phi2+np.pi/4.), y[i]+rad*np.sin(phi2+np.pi/4.))
                aprops = dict(arrowstyle="<|-|>",
                              connectionstyle=_connectionsstyle(phi[i]),
                              lw=2, ec='k', fc='k', alpha=_alpha(transmat[i, j]))

                axes.annotate("", x1, x2, arrowprops=aprops)

    # add circles and labels
    for label, xi, yi in zip(classes.keys(), x, y):
        axes.add_patch(patches.Circle((xi, yi), rad,
                                      color=hex2color(classes[label])))
        axes.text(xi, yi, str(label), horizontalalignment='center',
                  verticalalignment='center', fontsize=14, )

    axes.set_xlim((-2, 2))
    axes.set_ylim((-2, 2))
    axes.get_xaxis().set_visible(False)
    axes.get_yaxis().set_visible(False)
    return axes.get_figure()
