"""
emptyfigure.py
"""
from __future__ import absolute_import

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['empty_figure']

from matplotlib import pyplot as plt

def empty_figure(axes=None, title=None, text="no data"):
    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(111)

    axes.set_frame_on(False)
    if title is not None:
        axes.set_title(title)
    if text is not None:
        axes.text(0, 0, text, fontsize=40,
                  verticalalignment='center',
                  horizontalalignment='center',
                  alpha= 0.6)
    axes.set_xlim((-0.5, 0.5))
    axes.set_ylim((-0.5, 0.5))

    axes.get_xaxis().set_visible(False)
    axes.get_yaxis().set_visible(False)
    return axes.get_figure()
