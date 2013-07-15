"""
hmmreport.py

Data container and report class (for pdf generation)

"""

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'

__all__ = ['HmmBucket', 'HmmReport']


from collections import OrderedDict
import numpy as np

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from cecog import plots
from cecog.errorcorrection import PlateMapping


class HmmBucket(object):

    __slots__ = ['labels', 'hmm_labels', 'startprob', 'emismat', 'transmat',
                 'groups', 'ntracks', 'stepwidth', '_dwell_times']

    def __init__(self, labels, hmm_labels, startprob, emismat, transmat, groups,
                 ntracks, stepwidth=None):
        super(HmmBucket, self).__init__()
        self._dwell_times = None
        self.labels = labels
        self.hmm_labels = hmm_labels
        self.startprob = startprob
        self.emismat = emismat
        self.transmat = transmat
        self.groups = groups
        self.ntracks = ntracks
        self.stepwidth = stepwidth

    @property
    def dwell_times(self):
        """Determine the dwell time for each consecutive labels sequence.
        Returns an ordered dict with labels as keys and list of duration time as
        values."""

        # have it calculated only once
        if self._dwell_times is None:
            classes = np.unique(self.hmm_labels)
            counts = OrderedDict()
            for class_ in classes:
                counts.setdefault(class_, [])

            labels = self.hmm_labels.flatten()
            counter = 0
            for i, label in enumerate(labels):
                try:
                    if labels[i] == labels[i+1]:
                        counter += 1
                    else:
                        counts[label].append(counter)
                        counter = 1 # at least one frame
                except IndexError:
                    pass # no index i+1

            for key, value in counts.iteritems():
                counts[key]  = np.array(value)*self.stepwidth
            self._dwell_times = counts

        return self._dwell_times


class HmmReport(object):

    def __init__(self, data, ecopts, classdef, outdir):
        self.data = data
        self.ecopts = ecopts
        self.outdir = outdir
        self.classdef = classdef

    def overview(self, filename):
        pdf = PdfPages(filename)
        try:
            nrows, ncols =  5, len(self.data)
            fig, axarr = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6*ncols, 6*nrows))
            plt.subplots_adjust(hspace=0.3)
            for i, (name, data) in enumerate(self.data.iteritems()):
                try:
                    title = '%s, %s, (%d tracks)' %(name, data.groups[PlateMapping.GENE],
                                                    data.ntracks)
                except KeyError: # if not plate mapping is present
                    title = '%s, (%d tracks)' %(name, data.ntracks)

                # hmm network
                clcol = dict([(k, self.classdef.hexcolors[v])
                              for k, v in self.classdef.class_names.iteritems()])
                plots.hmm_network(data.transmat, clcol, title=title, axes=axarr[0][i])

                # trajectories
                plots.trajectories(data.labels,
                                   labels=self.ecopts.sorting_sequence,
                                   title=title,
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[1][i])

                plots.trajectories(data.hmm_labels,
                                   labels=self.ecopts.sorting_sequence,
                                   title=title,
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[2][i])

                # dwell box/barplots
                ylabel = "dwell time (%s)" %self.ecopts.timeunit
                xlabel = "class labels"

                plots.dwell_boxplot(data.dwell_times, title, ylabel=ylabel, xlabel=xlabel,
                                    cmap=self.classdef.colormap,
                                    ymax=self.ecopts.tmax,
                                    axes=axarr[3][i])


                plots.barplot(data.dwell_times, title, xlabel=xlabel, ylabel=ylabel,
                              cmap=self.classdef.colormap,
                              ymax=self.ecopts.tmax,
                              axes=axarr[4][i])
            pdf.savefig(fig)
        finally:
            pdf.close()

    def bars_and_boxes(self, filename):
        bars = []
        boxes = []

        fsize = (max(8, len(self.data)/8.), 6)
        for label in self.classdef.class_names.keys():
            dwell_times = OrderedDict([(k, np.array([])) for k in sorted(self.data.keys())])
            for name, data in self.data.iteritems():
                try:
                    dwell_times[name] = np.concatenate((dwell_times[name],
                                                        data.dwell_times[label]))
                except KeyError:
                    pass

            title = "class %d (%s)" %(label, self.classdef.class_names[label])
            ylabel = "dwell time (%s)" %self.ecopts.timeunit
            xlabel = self.ecopts.sortby.lower()

            fig = plt.figure(figsize=fsize)
            axes = fig.add_subplot(111)

            plots.barplot2(dwell_times, title, xlabel, ylabel,
                           color=self.classdef.colormap(label), axes=axes)

            fig.subplots_adjust(bottom=0.2)
            bars.append(fig)

            fig = plt.figure(figsize=fsize)
            axes = fig.add_subplot(111)

            plots.dwell_boxplot2(dwell_times, title, xlabel, ylabel,
                                 color=self.classdef.colormap(label),
                                 axes=axes)
            fig.subplots_adjust(bottom=0.2)
            boxes.append(fig)
        pdf = PdfPages(filename)
        # for the correct order in the file
        try:
            for fig in bars+boxes:
                pdf.savefig(fig)
        finally:
            pdf.close()
