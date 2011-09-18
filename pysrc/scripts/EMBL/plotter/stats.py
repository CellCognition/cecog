import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy

import os, sys, time, re

import colors

class Histogram(object):
    def __call__(self, datamatrix, filename,
                 colorvec=None, alpha=0.8,
                 xlabel='data', ylabel='frequency', title='Histogram',
                 axis=None, vertical_lines=None,
                 bins=30, normed=True,
                 side_by_side=True):

        #hist(x, bins=30, range=None, normed=False, cumulative=False,
        #     bottom=None, histtype='bar', align='mid',
        #     orientation='vertical', rwidth=None, log=False, **kwargs)

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)


        if colorvec is None:
            nb_data_sets = len(datamatrix)
            cm = colors.ColorMap()
            colorvec = cm.makeDivergentColorRamp(nb_data_sets)

        #if not xlim is None:

        histo = plt.hist(datamatrix, color=colorvec, alpha=alpha,
                         normed=normed,
                         bins=bins)
        ymin = numpy.min(histo[0])
        ymax = numpy.max(histo[0])
        xmin = numpy.min(histo[1])
        xmax = numpy.max(histo[1])

        if not side_by_side:
            plt.clf()
            bins = histo[1]
            for i in range(len(datamatrix)):
                h = plt.hist(datamatrix[i], color=colorvec[i],
                             alpha=alpha, normed=normed,
                             bins=bins)

        plt.grid(b=True, which='major', linewidth=1.5)


        if not axis is None:
            plt.axis(axis)
        else:
            axis = [xmin - (xmax-xmin)*0.05,
                    xmax+(xmax-xmin) * 0.05,
                    ymin,
                    ymax + (ymax - ymin) * 0.05]
            plt.axis(axis)


        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)

        # vertical lines
        if not vertical_lines is None:
            for line_title in vertical_lines:
                if 'linewidth' in vertical_lines[line_title]:
                   linewidth = vertical_lines[line_title]['linewidth']
                else:
                    linewidth = 2

                if 'color' in vertical_lines[line_title]:
                    color = vertical_lines[line_title]['color']
                else:
                    color = (1.0, 0.8, 0.0, 0.6)

                if 'ls' in vertical_lines[line_title]:
                    ls = vertical_lines[line_title]['ls']
                else:
                    ls = '-'

                plt.axvline(ymin, ymax=ymax,
                            x=vertical_lines[line_title]['x'],
                            color=color,
                            linewidth=linewidth,
                            ls=ls)


        # write and close
        plt.savefig(filename)
        plt.close(1)

        return