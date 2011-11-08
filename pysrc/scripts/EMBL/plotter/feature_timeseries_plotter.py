import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

import numpy

import os, sys, time, re
import colors

from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties

from collections import *

#import matplotlib.pyplot as plt
#import matplotlib.patches as mpatches
#
#xy = 0.3, 0.3,
#width, height = 0.2, 0.5
#
#p = mpatches.Rectangle(xy, width, height, facecolor="orange", edgecolor="red")
#
#plt.gca().add_patch(p)
#
#plt.draw()

#plt.savefig('test.png', bbox_inches='tight')
#plt.subplots_adjust(left=0.1, right=0.1, top=0.1, bottom=0.1)



def extendFigure(fig, ax,
                 new_fig_extension_inches=None,
                 new_fig_extension_percentage=None):

    if new_fig_extension_percentage is None and new_fig_extension_inches is None:
        raise ValueError("new figure extension has to be specified in either inches or percentage")
    if not new_fig_extension_percentage is None:
        current_ext = fig.get_size_inches()
        new_ext_calc = current_ext * new_fig_extension_percentage
        if new_fig_extension_inches is None:
            new_fig_extension_inches = new_ext_calc
        elif new_fig_extension_inches[0] != new_ext_calc[0] or new_fig_extension_inches[1] != new_ext_calc[1]:
            raise ValueError("conflicting values for width/height settings in inches and percentages.")

    if new_fig_extension_inches[0] <= 0 or new_fig_extension_inches[1] <= 0:
        raise ValueError("invalid values for figure extension (0 or negative)")

    width_points = fig.get_figwidth() * fig.get_dpi()
    height_points = fig.get_figheight() * fig.get_dpi()

    pos = ax.get_position()
    startx = pos.x0 * width_points
    starty = pos.y0 * height_points
    width = pos.width * width_points
    height = pos.height * height_points

    fig.set_size_inches(new_fig_extension_inches)
    ax.set_position([startx / (fig.get_dpi() * new_fig_extension_inches[0]),
                     starty / (fig.get_dpi() * new_fig_extension_inches[1]),
                     width  / (fig.get_dpi() * new_fig_extension_inches[0]),
                     height / (fig.get_dpi() * new_fig_extension_inches[1])])

    return


class TimeseriesPlotter(object):

    def __init__(self):
        self.cm = colors.ColorMap()

    def makeSingleTimeseriesPlot(self, timevec,
                                 datavec,
                                 filename,
                                 linewidth=2,
                                 title='Time Series',
                                 ylabel='Feature Value',
                                 xlabel='Time in Frames',
                                 color='x0000EEBB',
                                 axis=None,
                                 grid=True,
                                 vertical_lines=None,
                                 colorvec=None,
                                 classificationvec=None,
                                 color_code=None,
                                 title_fontsize=10):


        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        # plot
        plt.plot(timevec, datavec, linewidth=linewidth,
                 color=color)
        plt.grid(b=True, which='major', linewidth=1.5)
        if not axis is None:
            #axis = [min(timevec), max(timevec), min(datavec), max(datavec)]
            plt.axis(axis)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title, fontsize=title_fontsize)

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

                plt.axvline(ymin, ymax=1.0,
                            x=vertical_lines[line_title]['x'],
                            color=color,
                            linewidth=linewidth,
                            ls=ls)
                #linestyle or ls: [ '-' | '--' | '-.' | ':' | 'steps' | 'None' | ' ' | '' ]


        if colorvec is None and not color_code is None and not classificationvec is None:
            colorvec = [color_code[x] for x in classificationvec]

        print colorvec
        if not colorvec is None:

            # get y-coordinate/modify axis
            current_axis = plt.axis()
            xrange = current_axis[1] - current_axis[0]
            yrange = current_axis[3] - current_axis[2]
            y_coord = current_axis[2] - 0.05 * yrange
            plt.axis((current_axis[0], current_axis[1],
                      current_axis[2] - 0.1 * yrange, current_axis[3]))

            # get dimensions of the squares:
            width_points = 0.775 * fig.get_figwidth() * fig.get_dpi()
            height_points = 0.8 * fig.get_figheight() * fig.get_dpi()

            a = numpy.floor(width_points  / xrange)
            if a > 0.1 * height_points:
                a = numpy.floor(0.1 * height_points)
            print width_points, a

            # make plot
            plt.scatter(timevec, [y_coord for i in timevec],
                        s=a*a, marker='s', color=colorvec, edgecolors='none')

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

    def makeTimeseriesPlot(self, timevec,
                           datamatrix,
                           filename,
                           linewidth=2,
                           title='Time Series',
                           ylabel='Feature Value',
                           xlabel='Time in Frames',
                           linecolors=None,
                           axis=None,
                           grid=True,
                           vertical_lines=None,
                           colorvals=None,
                           classification_results=None,
                           color_code=None,
                           title_fontsize=10,
                           classification_legends=None,
                           legend_titles=None):

        # check dimensions
        nb_timeseries, len_timeseries = datamatrix.shape
        if not len(timevec) == len_timeseries:
            raise ValueError("time vector has length %i but data has length %i" %
                             (len(timevec), len_timeseries))

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        # plot
        if linecolors is None:
            linecolors = self.cm.makeDivergentColorRamp(nb_timeseries)

        lines = ax.plot(timevec, numpy.transpose(datamatrix), linewidth=linewidth)
        for i in range(len(lines)):
            plt.setp(lines[i], color=linecolors[i], label='_nolegend_')

        plt.grid(b=True, which='major', linewidth=1.5)
        if axis is None:
            delta_x = 0.08 * (numpy.max(timevec) - numpy.min(timevec))
            delta_y = 0.15 * (numpy.max(datamatrix) - numpy.min(datamatrix))
            axis = [numpy.min(timevec) - delta_x,
                    numpy.max(timevec) + delta_x,
                    numpy.min(datamatrix) - delta_y,
                    numpy.max(datamatrix) + delta_y]
        plt.axis(axis)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title, fontsize=title_fontsize)

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

                plt.axvline(#ymin, ymax=1.0,
                            x=vertical_lines[line_title]['x'],
                            color=color,
                            linewidth=linewidth,
                            ls=ls,
                            label='_nolegend_')
                #linestyle or ls: [ '-' | '--' | '-.' | ':' | 'steps' | 'None' | ' ' | '' ]


        if colorvals is None and not color_code is None and not classification_results is None:
            colorvals = {}
            for key in classification_results.keys():
                colorvals[key] = [color_code[key][x] for x in classification_results[key]]

        if not colorvals is None:

            nb_rows = len(colorvals)
            pos = ax.get_position()
            width_points = pos.width * fig.get_figwidth() * fig.get_dpi()
            height_points = pos.height * fig.get_figheight() * fig.get_dpi()

            # get y-coordinate/modify axis
            current_axis = plt.axis()
            xrange = current_axis[1] - current_axis[0]
            yrange = current_axis[3] - current_axis[2]

            #plt.axis((current_axis[0], current_axis[1],
            #          current_axis[2] - 0.1 * yrange, current_axis[3]))

            small_delta = 0.5
            a = 0.8 * numpy.floor(width_points  / xrange)
            if a > 0.1 * height_points:
                a = numpy.floor(0.1 * height_points)

#            print 'pos.width: ', pos.width
#            print 'fig.get_figwidth: ', fig.get_figwidth()
#            print 'fig.get_dpi: ', fig.get_dpi()
#            print 'wdith_points: ', width_points
#            print 'xrange: ', xrange
#            print 'a: ', a
#            print 'fig.get_size_inches: ', fig.get_size_inches()

            a_yc = a / height_points * yrange

            plt.axis((current_axis[0], current_axis[1],
                      current_axis[2] - a_yc * (1.0 + (1 + small_delta) * nb_rows),
                      current_axis[3]))

            #plt.axis((current_axis[0], current_axis[1],
            #          current_axis[2] - a * (1.25 + (1 + small_delta) * nb_rows),
            #          current_axis[3]))


            cur_row = 0
            for key in colorvals.keys():
                colorvec = colorvals[key]
                #y_coord = current_axis[2] - ((1 + small_delta) * cur_row + 0.5) * a
                y_coord = current_axis[2] - ((1 + small_delta) * cur_row + 0.5) * a_yc

                # make plot
                all_colors = set(colorvec)
                for col in all_colors:
                    if not classification_legends is None:
                        cc = dict(zip(classification_legends[key][1], classification_legends[key][0]))
                        label = cc[col]
                    else:
                        label=None

                    indices = filter(lambda x: colorvec[x]==col, range(len(colorvec)))
                    timevec_red = [timevec[i] for i in indices]

                    plt.plot(timevec_red, [y_coord for i in timevec_red], 's',
                             markerfacecolor=col, markeredgecolor='none',
                             markersize=a, clip_on=False, label=label,
                             )

                if not classification_legends is None:
                    #############################################
                    # PLOT ANNOTATION (only if there is a legend)
                    plt.text(timevec[0] - 2, y_coord, str(cur_row),
                             fontsize=9,
                             horizontalalignment='left', verticalalignment='center',
                             )

                cur_row += 1

            ##########
            # LEGEND
            if not classification_legends is None:

                # increase figure size
                default_size = fig.get_size_inches()

                # extend the figure by 20%
                extendFigure(fig, ax,
                             new_fig_extension_percentage=numpy.array([1.2, 1.0]))
                prop = FontProperties(size='small')

                # classification_legends has the following structure:
                # classification_legends[classifier] = (["label1", "label2", ...], ["color1", "color2", ...])
                legend_handlers = []
                ind = 0
                for key in classification_legends.keys():

                    #plt.text(timevec[0] - 1, y_coord, str(cur_row))
                    if not legend_titles is None and key in legend_titles:
                        title = '%i: %s' % (ind, legend_titles[key])
                    else:
                        title = '%i: %s' % (ind, str(key))

                    labels = classification_legends[key][0]

                    # dummy plot (to get all labels)
                    plotted_obj = {}
                    for label, col in zip(labels, classification_legends[key][1]):
                        plotted_obj[label], = \
                            plt.plot([current_axis[1] * 2],[current_axis[3] * 2], 's',
                                     markerfacecolor=col, markeredgecolor='none',
                                     markersize=a, clip_on=True, label=label,
                                     )

                    plotted_markers = [plotted_obj[label] for label in
                                       filter(lambda x: x in plotted_obj, labels)]

                    legend_handlers.append(ax.legend(plotted_markers,
                                                     filter(lambda x: x in plotted_obj, labels),
                                                     title=title,
                                                     loc=2,
                                                     bbox_to_anchor=(1.0, 1.0-ind*(1.0/len(classification_legends))),
                                                     prop=prop,
                                                     numpoints=1,
                                                     scatterpoints=1,
                                                     markerscale=0.75,
                                                     ))
                    ind += 1

                for leg in legend_handlers[:-1]:
                    # this is necessary to show all legends
                    # if omitted, the attached legends are always replaced.
                    plt.gca().add_artist(leg)

        # write and close
        fig.savefig(filename, dpi=fig.get_dpi())
        plt.close(1)

        return

    def __makeTimeseriesPlot(self, timevec,
                           datamatrix,
                           filename,
                           linewidth=2,
                           title='Time Series',
                           ylabel='Feature Value',
                           xlabel='Time in Frames',
                           linecolors=None,
                           axis=None,
                           grid=True,
                           vertical_lines=None,
                           colorvals=None,
                           classification_results=None,
                           color_code=None,
                           title_fontsize=10,
                           classification_legends=None):

        # check dimensions
        nb_timeseries, len_timeseries = datamatrix.shape
        if not len(timevec) == len_timeseries:
            raise ValueError("time vector has length %i but data has length %i" %
                             (len(timevec), len_timeseries))

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        # plot
        if linecolors is None:
            linecolors = self.cm.makeDivergentColorRamp(nb_timeseries)

        lines = plt.plot(timevec, numpy.transpose(datamatrix), linewidth=linewidth,
                         color="blue")
        for i in range(len(lines)):
            plt.setp(lines[i], color=linecolors[i])

        plt.grid(b=True, which='major', linewidth=1.5)
        if axis is None:
            delta_x = 0.08 * (numpy.max(timevec) - numpy.min(timevec))
            delta_y = 0.15 * (numpy.max(datamatrix) - numpy.min(datamatrix))
            axis = [numpy.min(timevec) - delta_x,
                    numpy.max(timevec) + delta_x,
                    numpy.min(datamatrix) - delta_y,
                    numpy.max(datamatrix) + delta_y]
        plt.axis(axis)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title, fontsize=title_fontsize)

        # vertical lines
        # example: vertical_lines = {'event': {'linewidth': 2, 'color': 'gold',
        #                                      'ls': '-', 'x': 10}}
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

                print 'updated'
                plt.axvline(#ymin, ymax=1.0,
                            x=vertical_lines[line_title]['x'],
                            color=color,
                            linewidth=linewidth,
                            ls=ls)
                #linestyle or ls: [ '-' | '--' | '-.' | ':' | 'steps' | 'None' | ' ' | '' ]


        if colorvals is None and not color_code is None and not classification_results is None:
            colorvals = {}
            for key in classification_results.keys():
                colorvals[key] = [color_code[key][x] for x in classification_results[key]]

        if not colorvals is None:
            nb_rows = len(colorvals)

            # get dimensions of the squares:
            width_points = 0.775 * fig.get_figwidth() * fig.get_dpi()
            height_points = 0.8 * fig.get_figheight() * fig.get_dpi()

            # get y-coordinate/modify axis
            current_axis = plt.axis()
            xrange = current_axis[1] - current_axis[0]
            yrange = current_axis[3] - current_axis[2]

            #plt.axis((current_axis[0], current_axis[1],
            #          current_axis[2] - 0.1 * yrange, current_axis[3]))

            small_delta = 1.0
            a = numpy.floor(width_points  / xrange)
            if a > 0.1 * height_points:
                a = numpy.floor(0.1 * height_points)

            plt.axis((current_axis[0], current_axis[1],
                      current_axis[2] - a * (1.25 + (1 + small_delta) * nb_rows), current_axis[3]))
            #plt.axis((current_axis[0], current_axis[1]))

            cur_row = 0
            for key in colorvals.keys():
                colorvec = colorvals[key]
                y_coord = current_axis[2] - ((1 + small_delta) * cur_row + 0.5) * a

                # make plot
                plt.scatter(timevec, [y_coord for i in timevec],
                            s=a*a, marker='s', color=colorvec, edgecolors='none')
                cur_row += 1

            if not classification_legends is None:
                # Shrink current axis by 20%
                box = ax.get_position()
                ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
                prop = FontProperties(size='small')

                # classification_legends has the following structure:
                # classification_legends[classifier] = (["label1", "label2", ...], ["color1", "color2", ...])
                legend_handlers = []
                ind = 0
                for key in classification_legends.keys():
                    squares = [Rectangle((0, 0), 1, 1, fc=col) for
                               col in classification_legends[key][1]]
                    title = key
                    labels = classification_legends[key][0]

                    legend_handlers.append(ax.legend(squares,
                                                     labels,
                                                     title=title,
                                                     loc=2,
                                                     bbox_to_anchor=(1.0, 1.0-ind*(1.0/len(classification_legends))),
                                                     prop=prop,
                                                     numpoints=1,
                                                     scatterpoints=1,
                                                     markerscale=1.0,
                                                     ))
                    ind += 1
                    ind = min(ind, 3)

                for leg in legend_handlers[:-1]:
                    plt.gca().add_artist(leg)

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

    def subplot_test_makeTimeseriesPlot(self, timevec,
                           datamatrix,
                           filename,
                           linewidth=2,
                           title='Time Series',
                           ylabel='Feature Value',
                           xlabel='Time in Frames',
                           linecolors=None,
                           axis=None,
                           grid=True,
                           vertical_lines=None,
                           colorvals=None,
                           classification_results=None,
                           color_code=None,
                           title_fontsize=10,
                           classification_legends=None):

#import pylab
#   2
#   3 figprops = dict(figsize=(8., 8. / 1.618), dpi=128)                                          # Figure properties
#   4 adjustprops = dict(left=0.1, bottom=0.1, right=0.97, top=0.93, wspace=0.2 hspace=0.2)       # Subplot properties
#   5
#   6 fig = pylab.figure(**figprops)                                                              # New figure
#   7 fig.subplots_adjust(**adjustprops)                                                          # Tunes the subplot layout
#   8
#   9 ax = fig.add_subplot(3, 1, 1)
#  10 bx = fig.add_subplot(3, 1, 2, sharex=ax, sharey=ax)
#  11 cx = fig.add_subplot(3, 1, 3, sharex=ax, sharey=ax)
#  12
#  13 ax.plot([0,1,2], [2,3,4], 'k-')
#  14 bx.plot([0,1,2], [2,3,4], 'k-')
#  15 cx.plot([0,1,2], [2,3,4], 'k-')
#  16
#  17 pylab.setp(ax.get_xticklabels(), visible=False)
#  18 pylab.setp(bx.get_xticklabels(), visible=False)
#  19
#  20 bx.set_ylabel('This is a long label shared among more axes', fontsize=14)
#  21 cx.set_xlabel('And a shared x label', fontsize=14)

        # check dimensions
        nb_timeseries, len_timeseries = datamatrix.shape
        if not len(timevec) == len_timeseries:
            raise ValueError("time vector has length %i but data has length %i" %
                             (len(timevec), len_timeseries))

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        # plot
        if linecolors is None:
            linecolors = self.cm.makeDivergentColorRamp(nb_timeseries)

        lines = ax.plot(timevec, numpy.transpose(datamatrix), linewidth=linewidth)
        for i in range(len(lines)):
            plt.setp(lines[i], color=linecolors[i], label='_nolegend_')

        plt.grid(b=True, which='major', linewidth=1.5)
        if axis is None:
            delta_x = 0.08 * (numpy.max(timevec) - numpy.min(timevec))
            delta_y = 0.15 * (numpy.max(datamatrix) - numpy.min(datamatrix))
            axis = [numpy.min(timevec) - delta_x,
                    numpy.max(timevec) + delta_x,
                    numpy.min(datamatrix) - delta_y,
                    numpy.max(datamatrix) + delta_y]
        plt.axis(axis)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title, fontsize=title_fontsize)

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

                plt.axvline(#ymin, ymax=1.0,
                            x=vertical_lines[line_title]['x'],
                            color=color,
                            linewidth=linewidth,
                            ls=ls,
                            label='_nolegend_')
                #linestyle or ls: [ '-' | '--' | '-.' | ':' | 'steps' | 'None' | ' ' | '' ]


        if colorvals is None and not color_code is None and not classification_results is None:
            colorvals = {}
            for key in classification_results.keys():
                colorvals[key] = [color_code[key][x] for x in classification_results[key]]

        if not colorvals is None:

            nb_rows = len(colorvals)
            pos = ax.get_position()
            width_points = pos.width * fig.get_figwidth() * fig.get_dpi()
            height_points = pos.height * fig.get_figheight() * fig.get_dpi()

            # get y-coordinate/modify axis
            current_axis = plt.axis()
            xrange = current_axis[1] - current_axis[0]
            yrange = current_axis[3] - current_axis[2]

            #plt.axis((current_axis[0], current_axis[1],
            #          current_axis[2] - 0.1 * yrange, current_axis[3]))

            small_delta = 1.0
            a = numpy.floor(width_points  / xrange)
            if a > 0.1 * height_points:
                a = numpy.floor(0.1 * height_points)

            # HERE I AM
            new_width = fig.get_figwidth()
            new_height = fig.get_figheight() + nb_rows * a / fig.get_dpi()
            extendFigure(fig, ax,
                         new_fig_extension_inches=numpy.array([new_width, new_height]))

            #ax = fig.add_subplot(3, 1, 1)
            big_ax_pos = ax.get_position()
            bx = fig.add_axes([big_ax_pos.x0,
                               big_ax_pos.y0 - a / (new_height * fig.get_dpi()),
                               big_ax_pos.width,
                               nb_rows * a / (fig.get_dpi() * fig.get_figheight())])


            #plt.axis((current_axis[0], current_axis[1],
            #          current_axis[2] - a * (1.25 + (1 + small_delta) * nb_rows),
            #          current_axis[3]))

            cur_row = 0

            for key in colorvals.keys():
                colorvec = colorvals[key]
                #y_coord = current_axis[2] - ((1 + small_delta) * cur_row + 0.5) * a
                #y_coord = 0
                y_coord = 0 - ((1 + small_delta) * cur_row + 0.5) * a

                # make plot
                all_colors = set(colorvec)
                for col in all_colors:
                    if not classification_legends is None:
                        cc = dict(zip(classification_legends[key][1], classification_legends[key][0]))
                        label = cc[col]
                    else:
                        label=None

                    indices = filter(lambda x: colorvec[x]==col, range(len(colorvec)))
                    timevec_red = [timevec[i] for i in indices]

                    bx.plot(timevec_red, [y_coord for i in timevec_red], 's',
                             markerfacecolor=col, markeredgecolor='none',
                             markersize=a, clip_on=False, label=label,
                             )
                cur_row += 1

            if not classification_legends is None:

                # increase figure size
                default_size = fig.get_size_inches()

                # extend the figure by 20%
                extendFigure(fig, ax,
                             new_fig_extension_percentage=numpy.array([1.2, 1.0]))
                prop = FontProperties(size='small')

                # classification_legends has the following structure:
                # classification_legends[classifier] = (["label1", "label2", ...], ["color1", "color2", ...])
                legend_handlers = []
                ind = 0
                for key in classification_legends.keys():

                    title = str(key)
                    labels = classification_legends[key][0]

                    # dummy plot (to get all labels)
                    plotted_obj = {}
                    for label, col in zip(labels, classification_legends[key][1]):
                        plotted_obj[label], = \
                            plt.plot([current_axis[1] * 2],[current_axis[3] * 2], 's',
                                     markerfacecolor=col, markeredgecolor='none',
                                     markersize=a, clip_on=True, label=label,
                                     )

                    plotted_markers = [plotted_obj[label] for label in
                                       filter(lambda x: x in plotted_obj, labels)]

                    legend_handlers.append(bx.legend(plotted_markers,
                                                     filter(lambda x: x in plotted_obj, labels),
                                                     title=title,
                                                     loc=2,
                                                     bbox_to_anchor=(1.0, 1.0-ind*(1.0/len(classification_legends))),
                                                     prop=prop,
                                                     numpoints=1,
                                                     scatterpoints=1,
                                                     markerscale=1.0,
                                                     ))
                    ind += 1

                for leg in legend_handlers[:-1]:
                    # this is necessary to show all legends
                    # if omitted, the attached legends are always replaced.
                    plt.gca().add_artist(leg)

        # write and close
        fig.savefig(filename)
        plt.close(1)

        return