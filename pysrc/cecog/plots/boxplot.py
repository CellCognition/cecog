"""
boxplots.py

Boxplots for show dwell times for each class label.
"""

from __future__ import division

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ["dwell_boxplot", "barplot"]

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon
from cecog.colors import DCMAP

def dwell_boxplot(data, title, xlabel='class label',
                  ylabel='dwell time (frames)', exclude_labels=None,
                  cmap=DCMAP, ymax=None):

    # remove keys only in this scope
    data = data.copy()
    for k in data.keys():
        if exclude_labels is not None and k in exclude_labels:
            del data[k]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    bp = plt.boxplot(data.values())#, notch=0, sym='+', vert=1, whis=1.5)
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    plt.setp(bp['fliers'],  markeredgecolor='black', marker='o',
             fillstyle='none')

    yr = np.array(ax.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    if ymax is not None and ymax < yr[1]:
        yr[1] = ymax
    ax.set_ylim(yr)
    ax.set_xticklabels(data.keys(), rotation=45)

    pos = dict((k, v) for k, v in zip(data.keys(), ax.get_xticks()))
    # fill boxes with class color
    for box, label in zip(bp['boxes'], data.keys()):
        boxX = list()
        boxY = list()
        for j in range(5):
            boxX.append(box.get_xdata()[j])
            boxY.append(box.get_ydata()[j])
            coords = zip(boxX, boxY)
        color = cmap(label)
        polygon = Polygon(coords, facecolor=color)
        ax.add_patch(polygon)

            # median values on the top of the plot
        median = "%.2f" %np.median(data[label])
        top = ax.get_ylim()[1]
        ax.text(pos[label], top-(top*0.05), median,
                horizontalalignment='center', size='medium',
                color=color)

    return fig

def barplot(data, title, xlabel='class label', ylabel='dwell time (frames)',
            exclude_labels=None, cmap=DCMAP, ymax=None):

    # remove keys only in this scop
    data = data.copy()
    for k in data.keys():
        if exclude_labels is not None and k in exclude_labels:
            del data[k]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    values = [np.average(v) for v in data.values()]
    colors = [cmap(k) for k in data.keys()]
    width = 2/3
    ind = np.arange(len(data))
    bp = plt.bar(ind-width/2, values, width=width, color=colors)
    ax.set_xlim((ind.min()-0.5, ind.max()+0.5))

    yr = np.array(ax.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    if ymax is not None and ymax < yr[1]:
        yr[1] = ymax
    ax.set_ylim(yr)
    ax.set_xticks(ind)
    ax.set_xticklabels(data.keys(), rotation=45)

    top = ax.get_ylim()[1]
    pos = dict((k, v) for k, v in zip(data.keys(), ind))
    for k, v in data.iteritems():
        # average values on the top of the plot
        average = "%.2f" %np.average(v)
        top = ax.get_ylim()[1]
        ax.text(pos[k], top-(top*0.05), average,
                horizontalalignment='center', size='medium',
                color=cmap(k))
    return fig
