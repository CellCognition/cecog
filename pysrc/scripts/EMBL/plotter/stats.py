import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy

import os, sys, time, re

import colors

from collections import OrderedDict

import types

from feature_timeseries_plotter import extendFigure

class Barplot(object):

    # dctData is an ordered dictionary (OrderedDict),
    # each entry is a list of values.
    def prepareDataForSingleBarplot(self, dctData):
        bartitles = dctData.keys()
        datavec = [numpy.mean(dctData[x]) for x in bartitles]
        errorvec = [numpy.std(dctData[x]) for x in bartitles]
        prep = {
                'bartitles': bartitles,
                'datavec': datavec,
                'errorvec': errorvec,
                }
        return prep

    def singleBarplot(self, datavec, filename,
                      color=None, errorvec=None,
                      width=0.7, bartitles=None,
                      title = 'Barplot', xlab='', ylab='',
                      xlim=None, ylim=None,
                      bottom = 0.2, grid=False):

        nb_bars = len(datavec)
        ind = numpy.array(range(nb_bars))

        if bartitles is None:
            bartitles = ind

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)
        ax.set_position(numpy.array([0.125, bottom, 0.8, 0.9 - bottom]))

        if color is None:
            color = (0.8, 0.05, 0.35)

        rects = plt.bar(ind, datavec, width=width, color=color,
                        yerr=errorvec, edgecolor='none')
        if xlim is None:
            xmin = min(ind)
            xmax = max(ind)
            xlim = (xmin - (xmax-xmin) * 0.05,
                    xmax + (xmax-xmin) * (0.05 + 1.0 / nb_bars) )

        if ylim is None:
            ymin = 0 #min(datavec)
            if errorvec is None:
                ymax = max(datavec)
            else:
                ymax = max(datavec + errorvec)
            ylim = (ymin, ymax + (ymax - ymin) * 0.05)

        axis = (xlim[0], xlim[1], ylim[0], ylim[1])
        plt.axis(axis)

        plt.xticks(ind+.5*width, bartitles, rotation="vertical",
                   fontsize='small', ha='center')
        plt.title(title, size='small')
        plt.xlabel(xlab, size='small')
        plt.ylabel(ylab, size='small')

        if grid:
            plt.grid(b=True, which='major', linewidth=1.5)

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

    def multiBarplot(self, datamatrix, filename,
                     colorvec=None, errorvec=None,
                     width=0.7, bartitles=None,
                     title = 'Barplot', xlab='', ylab='',
                     xlim=None, ylim=None, xticks=None,
                     dataset_names=None,
                     bottom=0.2, loc=0):

        nb_bars, nb_datasets = datamatrix.shape
        ind = numpy.array(range(nb_bars))

        if colorvec is None:
            cm = colors.ColorMap()
            colorvec = cm.makeDivergentColorRamp(nb_datasets)

        real_width = float(width) / float(nb_datasets)

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)
        ax.set_position(numpy.array([0.125, bottom, 0.8, 0.9 - bottom]))

        rects = {}
        for i in range(nb_datasets):
            datavec = datamatrix[:,i]
            color = colorvec[i]
            rects[i] = plt.bar(ind+ i * real_width, datavec, width=real_width, color=color,
                               edgecolor='none')

        if xlim is None:
            xmin = min(ind)
            xmax = max(ind)
            xlim = (xmin - (xmax-xmin) * 0.05,
                    xmax + 1 + (xmax-xmin) * 0.05)

        if ylim is None:
            ymin = 0 #numpy.min(datavec)
            ymax = numpy.max(datamatrix)
            ylim = (ymin, ymax + (ymax - ymin) * 0.05)


        axis = (xlim[0], xlim[1], ylim[0], ylim[1])
        plt.axis(axis)

        if not bartitles is None:
            plt.xticks(ind+.5*width, bartitles, rotation="vertical",
                       fontsize='small', ha='center')
        plt.title(title)
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        if not dataset_names is None:
            leg = ax.legend([rects[i][0] for i in range(len(dataset_names))],
                            dataset_names, loc=loc)
            ltext  = leg.get_texts()
            plt.setp(ltext, fontsize='small')

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return


class Histogram(object):
    def __call__(self, datamatrix, filename,
                 colorvec=None, alpha=0.8,
                 xlabel='data', ylabel='frequency', 
                 title='Histogram',
                 axis=None, vertical_lines=None,
                 bins=50, normed=True,
                 side_by_side=True, 
                 dataset_names=None):

        #hist(x, bins=30, range=None, normed=False, cumulative=False,
        #     bottom=None, histtype='bar', align='mid',
        #     orientation='vertical', rwidth=None, log=False, **kwargs)

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)
        
        nb_datasets = len(datamatrix)
        if colorvec is None:
            cm = colors.ColorMap()
            colorvec = cm.makeDivergentColorRamp(nb_datasets)

        #if not xlim is None:

        histo = plt.hist(datamatrix, color=colorvec, alpha=alpha,
                         normed=normed,
                         bins=bins, 
                         label=dataset_names)
        ymin = numpy.min(histo[0])
        ymax = numpy.max(histo[0])
        xmin = numpy.min(histo[1])
        xmax = numpy.max(histo[1])

        if not side_by_side:
            plt.clf()
            bins = histo[1]
            h = {}
            for i in range(len(datamatrix)):
                h[i] = plt.hist(datamatrix[i], color=colorvec[i],
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


        #print nb_datasets
        #if not dataset_names is None and nb_datasets > 1:
        #    print 'i am legened'
        #    leg = ax.legend([h[i] for i in range(nb_datasets)], 
        #                    dataset_names, loc=1)

        plt.legend()
        
        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

class Scatterplot(object):

    def multi(self,
              xvecs,
              yvecs,
              filename,
              title='Scatterplot',
              xlabel='',
              ylabel='',
              axis=None,
              colorvec=None,
              markervec=None,
              edgecolor='none',
              dataset_names=None,
              ):

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        nb_data_sets = len(xvecs)

        xmin = numpy.min([numpy.min(xvec) for xvec in xvecs])
        xmax = numpy.max([numpy.max(xvec) for xvec in xvecs])
        ymin = numpy.min([numpy.min(yvec) for yvec in yvecs])
        ymax = numpy.max([numpy.max(yvec) for yvec in yvecs])
        
        if colorvec is None:
            cm = colors.ColorMap()
            colorvec = cm.makeDivergentColorRamp(nb_data_sets)

        if markervec is None:
            markervec = ['o' for i in range(nb_data_sets)]

        # adjust axis
        if not axis is None:
            plt.axis(axis)
        else:
            axis = [xmin - (xmax-xmin)*0.05,
                    xmax + (xmax-xmin) * 0.05,
                    ymin - (ymax - ymin) * 0.05,
                    ymax + (ymax - ymin) * 0.05]
            plt.axis(axis)

        sobj = {}
        for i in range(nb_data_sets):
            sobj[i] = plt.scatter(xvecs[i], yvecs[i],
                                  color = colorvec[i],
                                  marker=markervec[i],
                                  edgecolor=edgecolor,
                                  label=dataset_names[i])

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)

        if not dataset_names is None:
            plt.legend()
            #leg = ax.legend([sobj[i][0] for i in range(nb_data_sets)],
            #                dataset_names)

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

    def single(self,
               xvec,
               yvec,
               filename,
               title='Scatterplot',
               xlabel='',
               ylabel='',
               axis=None,
               color=(0.2, 0.0, 0.9),
               marker='o',
               edgecolor='none',
               grid=True,
               ):

        # new figure
        fig = plt.figure(1)
        ax = plt.subplot(1,1,1)

        xmin = numpy.min(xvec)
        xmax = numpy.max(xvec)
        ymin = numpy.min(yvec)
        ymax = numpy.max(yvec)


#        if colorvec is None:
#            nb_data_sets = len(datamatrix)
#            cm = colors.ColorMap()
#            colorvec = cm.makeDivergentColorRamp(nb_data_sets)

        # adjust axis
        if not axis is None:
            plt.axis(axis)
        else:
            axis = [xmin - (xmax-xmin)*0.05,
                    xmax + (xmax-xmin) * 0.05,
                    ymin - (ymax - ymin) * 0.05,
                    ymax + (ymax - ymin) * 0.05]
            plt.axis(axis)

        plt.scatter(xvec, yvec, color=color,
                    marker=marker, edgecolor=edgecolor)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)

        # add grid
        if grid:
            plt.grid(b=True, which='major', linewidth=1.5)

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

class ScatterplotMatrix(object):
    """Example:
    
    sm = ScatterplotMatrix()
    sm(X)     
    """
    def __call__(self,
                 datamatrix,
                 filename,
                 title='',
                 color=(0.2, 0.0, 0.9),
                 marker='o',
                 edgecolor='none',
                 colnames=None,
                 bins=30,
                 histo_alpha=0.75,
                 histo_normed=True,
                 histo_same_scale=True,
                 ):
        if type(color) == types.StringType or \
           type(color[0]) in [types.FloatType, types.IntType]:
            nb_data_sets=1
            first_color = color
            allcolors = [color]
        else:
            allcolors = list(set(color))
            nb_data_sets = len(allcolors)
            first_color = color[0]

        nb_rows, nb_cols = datamatrix.shape

        # new figure
        fig = plt.figure(1, figsize=(1.6*nb_cols, 1.6*nb_cols))
        ax = plt.subplot(1,1,1)

        # generation of the datamatrix list
        index_list = []
        for sc in allcolors:
            index_list.append(filter(lambda i: color[i] == sc, range(len(color))))

        # maximum histogram value
        ymax = 0
        for i in range(nb_cols):
            histo = ax.hist(datamatrix[:,i],
                            normed=histo_normed,
                            bins=bins)
            #ymin = numpy.min(histo[0])
            ymin = 0
            ymax = max(ymax, numpy.max(histo[0]))
            #print 'histo-max(%i/%i): %f' %(i, nb_cols,numpy.max(histo[0]))

        ymin_histo = 0
        if ymax < 5.0:
            ymax_histo = numpy.ceil(1.1 * ymax * 10) / 10
        else:
            ymax_histo = numpy.ceil(1.1 * ymax)
        #print '   ', ymax, ymax_histo

        #ymax_histo = 1.0
        plt.clf()

        for i in range(nb_cols):
            for j in range(nb_cols):
                xmin = numpy.min(datamatrix[:,j])
                xmax = numpy.max(datamatrix[:,j])

                #print i, j, i*nb_cols+j+1
                ax = fig.add_subplot(nb_cols,nb_cols,i*nb_cols+j+1)
                ax.clear()

                #ax.set_ticklabels
                if i == j:
                    ymin = ymin_histo
                    ymax = ymax_histo
                    histo = ax.hist(datamatrix[:,i],
                                    color=first_color,
                                    normed=histo_normed,
                                    alpha=histo_alpha,
                                    bins=bins,
                                    edgecolor='none')
                    #print histo[0]
                    #print numpy.max(histo[0])
                    total_bins = histo[1]
                        
                    if nb_data_sets > 1:
                        ax.clear()
                        #print 'bins: ', bins

                        for k in range(nb_data_sets):
                            h = plt.hist(datamatrix[index_list[k],i],
                                         color=allcolors[k],
                                         alpha=histo_alpha,
                                         normed=histo_normed,
                                         bins=total_bins,
                                         edgecolor='none')

                else:
                    ymin = numpy.min(datamatrix[:,i])
                    ymax = numpy.max(datamatrix[:,i])
                    ax.scatter(datamatrix[:,j], datamatrix[:,i], color=color,
                               alpha = histo_alpha, s=4,
                               edgecolor=edgecolor, marker=marker)

                if j == 0: ax.set_ylabel(colnames[i],size='8')
                if i == 0: ax.set_title(colnames[j],size='8')
                if i < nb_cols - 1:
                    ax.xaxis.set_ticklabels([])
                if (j > 0 and j < nb_cols-1) or (j==0 and i==0) or (j==nb_cols-1 and i==nb_cols-1):
                    ax.yaxis.set_ticklabels([])

                if (j == nb_cols-1 and i < nb_cols-1):
                    #ax.yaxis.set_ticks_position('right')
                    ax.yaxis.tick_right()

                # set the axis
                if i!=j or histo_same_scale:
                    axis = [xmin - (xmax-xmin) * 0.05,
                            xmax + (xmax-xmin) * 0.05,
                            ymin,
                            ymax + (ymax - ymin) * 0.05]
                    plt.axis(axis)
                ax.tick_params(labelsize=7)

        plt.title(title)

        # write and close
        plt.savefig(filename)
        plt.close(1)

        return

