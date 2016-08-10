"""
trjgallery.py

"""
from __future__ import division
from __future__ import absolute_import
from six.moves import range

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['trj_gallery']


from matplotlib import pyplot as plt
from matplotlib.cm import gray

def trj_gallery(image, matrix, title, cmap, axes=None,
                offset=1.5, linewidth=1.5, dpi=300, figsize=(6, 9)):
    """Plot an image gallery with class colors at the bottom of each row."""

    n_trj, n_frames =  matrix.shape
    imgsize = image.shape[0]/n_trj

    if axes is None:
        fig = plt.figure(dpi=dpi, figsize=figsize)
        axes = fig.add_subplot(111, frameon=False)
    axes.imshow(image, aspect='equal', cmap=gray)

    for ti in range(n_trj):
        for fi in range(n_frames):
            axes.axhline(y=(ti+1)*imgsize+offset,
                       xmin=fi/n_frames,
                       xmax=(fi+1)/n_frames, color=cmap(matrix[ti, fi]),
                       linewidth=linewidth)

    axes.set_xlim((0, image.shape[1]))
    axes.set_ylim((0, image.shape[0]))
    axes.get_xaxis().set_visible(False)
    axes.get_yaxis().set_visible(False)
    axes.set_title(title)
    return axes.get_figure()
