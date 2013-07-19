"""
hmmreport.py

Data container and report class (for pdf generation)

"""
from __future__ import division

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'

__all__ = ['HmmBucket', 'HmmReport']


from collections import OrderedDict
import numpy as np

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
#from matplotlib.figure import SubplotParams

from cecog import plots
from cecog.errorcorrection import PlateMapping


class HmmBucket(object):

    __slots__ = ['labels', 'hmm_labels', 'startprob', 'emismat', 'transmat',
                 'groups', 'ntracks', 'stepwidth', '_dwell_times', 'fileinfo',
                 'gallery_files']

    def __init__(self, labels, hmm_labels, startprob, emismat, transmat, groups,
                 ntracks, stepwidth=None, gallery_files=None):
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
        self.gallery_files = gallery_files

    def iter_gallery(self, n=None):
        """Iterator over gallery images and tracks."""

        idx = np.arange(0, self.gallery_files.size, 1)
        if n is not None:
            np.random.shuffle(idx)
            idx = idx[:n]

        for track, gallery_file in zip(self.hmm_labels[idx], self.gallery_files[idx]):
            yield gallery_file, track

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

    def overview(self, filename, figsize=(25, 20)):
        pdf = PdfPages(filename)
        sp_props = dict(top=0.95, bottom=0.05, hspace=0.2, wspace=0.2, left=0.03, right=0.97)
        try:
            nrows, ncols =  5, len(self.data)
            fig, axarr = plt.subplots(nrows=5, ncols=6, figsize=figsize)
            fig.subplots_adjust(**sp_props)
            for j, (name, data) in enumerate(self.data.iteritems()):
                i = j%6
                if not i and j:
                    pdf.savefig(fig)
                    fig, axarr = plt.subplots(nrows=5, ncols=6, dpi=300, figsize=figsize)
                    fig.subplots_adjust(**sp_props)
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
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[1][i])

                plots.trajectories(data.hmm_labels,
                                   labels=self.ecopts.sorting_sequence,
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[2][i])

                # dwell box/barplots
                ylabel = "dwell time (%s)" %self.ecopts.timeunit
                xlabel = "class labels"

                plots.dwell_boxplot(data.dwell_times, ylabel=ylabel, xlabel=xlabel,
                                    cmap=self.classdef.colormap,
                                    ymax=self.ecopts.tmax,
                                    axes=axarr[3][i])


                plots.barplot(data.dwell_times, xlabel=xlabel, ylabel=ylabel,
                              cmap=self.classdef.colormap,
                              ymax=self.ecopts.tmax,
                              axes=axarr[4][i])
            pdf.savefig(fig)
        finally:
            pdf.close()

    def bars_and_boxes(self, filename):
        bars = []
        boxes = []

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

            if len(dwell_times) > 8:
                fsize = (len(dwell_times)*0.8, 6)
            else:
                fsize = (8, 6)

            sp_props = dict(bottom=0.2, top=0.9, left=0.1*8/(len(dwell_times)*0.8),
                            right=1-0.1*8/len(dwell_times))

            fig = plt.figure(figsize=fsize)
            axes = fig.add_subplot(111)

            plots.barplot2(dwell_times, title, xlabel, ylabel,
                           color=self.classdef.colormap(label), axes=axes)

            fig.subplots_adjust(**sp_props)
            bars.append(fig)

            fig = plt.figure(figsize=fsize)
            axes = fig.add_subplot(111)

            plots.dwell_boxplot2(dwell_times, title, xlabel, ylabel,
                                 color=self.classdef.colormap(label),
                                 axes=axes)
            fig.subplots_adjust(**sp_props)

            boxes.append(fig)
        pdf = PdfPages(filename)
        # for the correct order in the file
        try:
            for fig in bars+boxes:
                pdf.savefig(fig)
        finally:
            pdf.close()

    def image_gallery(self, filename, n_galleries=50):
        pdf = PdfPages(filename)
        try:
            for name, data in self.data.iteritems():
                image = np.array([])
                tracks = list()
                for file_, track in data.iter_gallery(n_galleries):
                    tracks.append(track)
                    try:
                        image = np.vstack((image, np.mean(plt.imread(file_), axis=2)))
                    except ValueError:
                        image = np.mean(plt.imread(file_), axis=2)

                    aspect = image.shape[0]/image.shape[1]
                    if aspect >= 1.0:
                        fig = self._trj_figure(image, tracks, (6, 6), name)
                        pdf.savefig(fig)
                        image = np.array([])
                        tracks = list()

                fig = self._trj_figure(image, tracks, (6, 6), name)
                pdf.savefig(fig)
        finally:
            pdf.close()

    def _trj_figure(self, image, tracks, size, name):
        fig = plt.figure(dpi=300, figsize=size)
        axes = fig.add_subplot(111, frameon=False)
        plots.trj_gallery(image, np.array(tracks),
                          title=name, cmap=self.classdef.colormap, axes=axes,
                          linewidth=1.5, offset=-5)
        fig.subplots_adjust(top=0.95, bottom=0.01, right=0.99, left=0.01)
