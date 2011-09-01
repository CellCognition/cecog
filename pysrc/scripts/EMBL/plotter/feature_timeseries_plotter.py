import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy

import os, sys, time, re

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



class TimeseriesPlotter(object):

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


        if not colorvec is None or (not color_code is None and
                                    not classificationvec is None):

            if colorvec is None:
                colorvec = [self.settings.class_color_code[x]
                            for x in classificationvec]

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

            # make plot
            plt.scatter(timevec, [y_coord for i in timevec],
                        s=a*a, marker='s', color=colorvec, edgecolors='none')

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return