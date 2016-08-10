"""
colors.py

Defines some colors and mappings
"""
from __future__ import absolute_import
from __future__ import print_function

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['Colors', 'rgb2hex', 'DCMAP', 'hex2rgb', 'BINARY_CMAP',
           'DiscreteColormap', 'unsupervised_cmap']

import numpy as np

from matplotlib.colors import ListedColormap
from matplotlib.colors import hex2color
from matplotlib.colors import rgb2hex as mpl_rgb2hex
from matplotlib import cm


def unsupervised_cmap(n):
    return ListedColormap([cm.Accent(i) for i in np.linspace(0, 1, n)])

# DCMAP is a fallback
DCMAP = unsupervised_cmap(10)
BINARY_CMAP = ListedColormap(["#DEDEDE","#FA1D2F"], name='binary_cmap')

def rgb2hex(color, mpl=True):
    """Converts an rgb-tuple into the corresponding hexcolor. if mpl is True,
    the rgb-tuple has to follow the matplotlib convention i.e. values must
    range from 0-1 otherwise from 0-255."""

    if mpl:
        fac = 1.0
    else:
        fac = 255.0

    return mpl_rgb2hex((color[0]/fac, color[1]/fac, color[2]/fac))

def hex2rgb(color, mpl=False):
    """Return the rgb color as python int in the range 0-255."""
    assert color.startswith("#")
    if mpl:
        fac = 1.0
    else:
        fac = 255.0
    rgb = [int(i*fac) for i in hex2color(color)]
    return tuple(rgb)


class Colors(object):

    red = '#FF0000'
    green = '#00FF00'
    blue = '#0000FF'
    yellow = '#FFFF00'
    magenta ='#FF00FF'
    cyan = '#00FFFF'
    white = '#FFFFFF'
    fallback = '#FFFFFF'
    fallback_str = "white"

    colors = ['white', 'red', 'green', 'blue', 'yellow', 'magenta', 'cyan']

    channel_table = {'rfp': 'red',
                     'gfp': 'green',
                     'yfp': 'yellow',
                     'cfp': 'cyan',
                     'cy5': 'cyan',
                     'Cherry': 'red',
                     'eGFP': 'green',
                     'FRET': 'magenta'}

    @classmethod
    def channel_color(cls, name):
        if name not in list(cls.channel_table.keys()):
            if __debug__:
                print("color %s not defined. Using fallback")
            return cls.fallback_str
        return cls.channel_table[name]

    @classmethod
    def channel_hexcolor(cls, name):
        if name not in list(cls.channel_table.keys()):
            if __debug__:
                print("channel color (%s) not defined. Using fallback" %name)
            return cls.fallback
        return getattr(cls, cls.channel_table[name])

    @classmethod
    def channel_rgb(cls, name):
        if name not in list(cls.channel_table.keys()):
            if __debug__:
                print("channel color (%s) not defined. Using fallback" %name)
            return hex2color(cls.fallback)
        return hex2color(getattr(cls, cls.channel_table[name]))


if __name__ == "__main__":
    print('by attribute:', Colors.red)
    print('colors: ', Colors.colors)
    print('channel color: ', Colors.channel_color('rfp'))
    print('color table: ', dict((c, getattr(Colors, c)) for c in Colors.colors))
