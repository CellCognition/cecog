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

__all__ = ["dwell_boxplot", "dwell_boxplot2", "barplot", "barplot2"]


import os
import textwrap

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Polygon
from cecog.colors import DCMAP

def dwell_boxplot(data, title=None, xlabel='class label',
                  ylabel='dwell time (frames)', exclude_labels=None,
                  cmap=DCMAP, ymax=None, axes=None):

    # remove keys only in this scope
    data = data.copy()
    for k in data.keys():
        if exclude_labels is not None and k in exclude_labels:
            del data[k]

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(111)

    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    if title is not None:
        axes.set_title(title)

    bp = axes.boxplot(data.values())#, notch=0, sym='+', vert=1, whis=1.5)
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    # plt.setp(bp['fliers'],  markeredgecolor='black', marker='o',
    #          fillstyle='none', markerfacecolor=colors[i])

    colors = [cmap(l) for l in data.keys()]
    for i, flier in enumerate(bp['fliers']):
        try: # the cluster sucks!
            flier.set(marker='o', color=colors[i], markerfacecolor=colors[i])
        except IndexError:
            break

    yr = np.array(axes.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    if ymax not in (-1, None):
        yr[1] = ymax
    axes.set_ylim(yr)
    xlabels = [str(k) for k in data.keys()]
    xlabels = [os.linesep.join(textwrap.wrap(str(l), 12)) for l in xlabels]
    axes.set_xticklabels(xlabels, rotation=45, fontsize='small')

    pos = dict((k, v) for k, v in zip(data.keys(), axes.get_xticks()))
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
        axes.add_patch(polygon)

        # median values on the top of the plot
        median = "%.2f" %np.median(data[label])
        top = axes.get_ylim()[1]
        axes.text(pos[label], top-(top*0.05), median,
                  horizontalalignment='center', size='x-small')
    return axes.get_figure()


def dwell_boxplot2(data, title=None, xlabel='', ylabel='dwell time (frames)',
                   axes=None, color='k'):

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(111)

    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    if title is not None:
        axes.set_title(title)


    bp = axes.boxplot(data.values())#, notch=0, sym='+', vert=1, whis=1.5)
    plt.setp(bp['boxes'], color='black')
    plt.setp(bp['whiskers'], color='black')
    plt.setp(bp['fliers'],  markeredgecolor='black', marker='o',
             fillstyle='none', markerfacecolor=color)

    yr = np.array(axes.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    axes.set_ylim(yr)

    xlabels = [str(k) for k in data.keys()]
    xlabels = [os.linesep.join(textwrap.wrap(str(l), 12)) for l in xlabels]
    axes.set_xticklabels(xlabels, rotation=90, fontsize='small')


    pos = dict((k, v) for k, v in zip(data.keys(), axes.get_xticks()))
    # fill boxes with class color
    for box, label in zip(bp['boxes'], data.keys()):
        boxX = list()
        boxY = list()
        for j in range(5):
            boxX.append(box.get_xdata()[j])
            boxY.append(box.get_ydata()[j])
            coords = zip(boxX, boxY)
        polygon = Polygon(coords, facecolor=color)
        axes.add_patch(polygon)

            # median values on the top of the plot
        median = "%.2f" %np.median(data[label])
        top = axes.get_ylim()[1]
        axes.text(pos[label], top-(top*0.05), median,
                  horizontalalignment='center', size='small')
    return axes.get_figure()


def barplot(data,
            title=None, xlabel='class label', ylabel='dwell time (frames)',
            exclude_labels=None, cmap=DCMAP, ymax=None, axes=None):

    # remove keys only in this scop
    data = data.copy()
    for k in data.keys():
        if exclude_labels is not None and k in exclude_labels:
            del data[k]

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(111)

    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)

    if title is not None:
        axes.set_title(title)

    values = [np.average(v) for v in data.values()]
    colors = [cmap(k) for k in data.keys()]
    width = 2/3
    ind = np.arange(len(data))
    bp = axes.bar(ind-width/2, values, width=width, color=colors)
    axes.set_xlim((ind.min()-0.5, ind.max()+0.5))

    yr = np.array(axes.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    if ymax not in (-1, None):
        yr[1] = ymax
    axes.set_ylim(yr)
    axes.set_xticks(ind)

    xlabels = [str(k) for k in data.keys()]
    xlabels = [os.linesep.join(textwrap.wrap(str(l), 12)) for l in xlabels]
    axes.set_xticklabels(xlabels, rotation=45, fontsize='small')

    top = axes.get_ylim()[1]
    pos = dict((k, v) for k, v in zip(data.keys(), ind))
    for k, v in data.iteritems():
        # average values on the top of the plot
        average = "%.2f" %np.average(v)
        top = axes.get_ylim()[1]
        axes.text(pos[k], top-(top*0.05), average,
                  horizontalalignment='center', size='x-small')
    return axes.get_figure()


def barplot2(data,
             title=None, xlabel='class label', ylabel='dwell time (frames)',
             color='k', axes=None):

    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(111)

    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    axes.set_title(title)

    values = [np.average(v) for v in data.values()]
    colors = len(data)*[color]

    width = 2/3
    ind = np.arange(len(data))
    bp = axes.bar(ind-width/2, values, width=width, color=colors)
    axes.set_xlim((ind.min()-0.5, ind.max()+0.5))

    yr = np.array(axes.get_ylim())
    yr = yr+np.array((-1, 1))*0.05*yr.ptp()
    axes.set_ylim(yr)
    axes.set_xticks(ind)

    xlabels = [str(k) for k in data.keys()]
    xlabels = [os.linesep.join(textwrap.wrap(str(l), 12)) for l in xlabels]
    axes.set_xticklabels(xlabels, rotation=90, fontsize='small')

    top = axes.get_ylim()[1]
    pos = dict((k, v) for k, v in zip(data.keys(), ind))
    for k, v in data.iteritems():
        # average values on the top of the plot
        average = "%.2f" %np.average(v)
        top = axes.get_ylim()[1]
        axes.text(pos[k], top-(top*0.05), average,
                  horizontalalignment='center', size='small')
    return axes.get_figure()
