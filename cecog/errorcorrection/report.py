"""
hmmreport.py

Data container and report class (for pdf generation)

"""
from __future__ import division

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'

__all__ = ['HmmBucket', 'HmmReport']

import os
import csv
import textwrap
from collections import OrderedDict
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from skimage import img_as_float
from skimage.transform import rescale
from skimage.io import imsave

from cellh5 import CH5Const
from cecog import plots
from cecog.colors import hex2rgb, grey2rgb


class HmmBucket(object):
    """Container class to store and operate on 'cell trajectories'."""

    __slots__ = ['labels', 'hmm_labels', 'startprob', 'emismat', 'transmat',
                 'groups', 'ntracks', 'stepwidth', '_dwell_times', 'startids',
                 'coordinates', 'nframes', '_states']

    def __init__(self, labels, hmm_labels, startprob, emismat, transmat, groups,
                 ntracks, startids, coordinates, stepwidth=None):
        super(HmmBucket, self).__init__()
        self._dwell_times = None
        self.labels = labels
        self.hmm_labels = hmm_labels
        self.startprob = startprob
        self.emismat = emismat
        self.transmat = transmat
        self.groups = groups
        self.ntracks = ntracks
        self.nframes = labels.shape[1]
        self.stepwidth = stepwidth
        self.startids = startids
        self.coordinates = coordinates
        self._states = None

    @property
    def states(self):
        if self._states is None:
            self._states = np.unique(self.labels)
        return self._states

    def itertracks(self, n=None, idx=None):
        """Iterator over gallery images and tracks."""

        if n is not None and idx is not None:
            raise RuntimeError(('you can not provide idx and n. '
                                'arguments are exclusive'))

        if idx is None:
            idx = np.arange(0, self.ntracks, 1)
            if n not in (None, -1):
                np.random.shuffle(idx)
                idx = idx[:n]

        for track, startid, coords in zip(self.hmm_labels[idx],
                                          self.startids[idx],
                                          self.coordinates[idx]):
            yield startid, track, coords

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

            for track in self.hmm_labels:
                for class_ in classes:
                    counts[class_].append(len(track[track == class_]))

            for key, value in counts.iteritems():
                counts[key]  = np.array(value)*self.stepwidth
            self._dwell_times = counts

        return self._dwell_times


class HmmReport(object):

    GALLERY_DPI = 200

    def __init__(self, data, ecopts, classdef, outdir):
        self.data = data
        self.ecopts = ecopts
        self.outdir = outdir
        self.classdef = classdef

    def close_figures(self):
        plt.close("all")

    def _frame_off(self, axarr, icol, nrows):
        while True:
            try:
                icol += 1
                for irow in xrange(nrows):
                    plots.empty_figure(axarr[irow, icol], text=None)
            except IndexError:
                break

    def _empty_figure(self, axarr, name, i, nrows=5):
        for k in xrange(nrows):
            if k == 0:
                plots.empty_figure(axarr[k][i], title="%s (0 tracks)" %name)
            else:
                plots.empty_figure(axarr[k][i])


    def overview(self, filename, figsize=(25, 20)):
        pdf = PdfPages(filename)
        sp_props = dict(top=0.95, bottom=0.05, hspace=0.2, wspace=0.2,
                        left=0.03, right=0.97)
        try:
            # nrows, _ =  5, len(self.data)
            fig, axarr = plt.subplots(nrows=5, ncols=6, figsize=figsize)
            fig.subplots_adjust(**sp_props)
            for j, name in enumerate(sorted(self.data.keys())):
                data = self.data[name]
                i = j%6
                if not i and j:
                    pdf.savefig(fig)
                    fig, axarr = plt.subplots(nrows=5, ncols=6, dpi=300,
                                              figsize=figsize)
                    fig.subplots_adjust(**sp_props)

                if data is None:
                    self._empty_figure(axarr, name, i, nrows=5)
                    continue

                title = '%s, (%d tracks)' %(name, data.ntracks)
                # hmm network
                clcol = dict([(k, self.classdef.colors[v])
                             for k, v in self.classdef.names.iteritems()
                              if k in data.states])

                plots.hmm_network(data.transmat, clcol, title=title,
                                  axes=axarr[0][i])

                # trajectories
                plots.trajectories(data.labels,
                                   labels=self.ecopts.sorting_sequence,
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[1][i],
                                   stepwidth=data.stepwidth)

                plots.trajectories(data.hmm_labels,
                                   labels=self.ecopts.sorting_sequence,
                                   cmap=self.classdef.colormap,
                                   norm=self.classdef.normalize,
                                   axes = axarr[2][i],
                                   stepwidth=data.stepwidth)

                # dwell box/barplots
                ylabel = "dwell time (%s)" %self.ecopts.timeunit
                xlabel = "class labels"

                plots.dwell_boxplot(data.dwell_times,
                                    ylabel=ylabel,
                                    xlabel=xlabel,
                                    cmap=self.classdef.colormap,
                                    ymax=self.ecopts.tmax,
                                    axes=axarr[3][i])


                plots.barplot(data.dwell_times, xlabel=xlabel, ylabel=ylabel,
                              cmap=self.classdef.colormap,
                              ymax=self.ecopts.tmax,
                              axes=axarr[4][i])
            self._frame_off(axarr, i, 5)
            pdf.savefig(fig)
        finally:
            pdf.close()

    def bars_and_boxes(self, filename):
        bars = []
        boxes = []

        for label in self.classdef.names.keys():
            dwell_times = OrderedDict([(k, np.array([]))
                                       for k in sorted(self.data.keys())])
            for name, data in self.data.iteritems():
                try:
                    dwell_times[name] = np.concatenate( \
                        (dwell_times[name], data.dwell_times[label]))
                except (KeyError, AttributeError):
                    pass

            title = "class %d (%s)" %(label, self.classdef.names[label])
            ylabel = "dwell time (%s)" %self.ecopts.timeunit
            xlabel = self.ecopts.sortby.lower()

            if len(dwell_times) > 8:
                fsize = (len(dwell_times)*0.8, 6)
            else:
                fsize = (8, 6)

            sp_props = dict(bottom=0.2, top=0.9,
                            left=0.1*8/(len(dwell_times)*0.8),
                            right=1-0.1*8/len(dwell_times))

            if sp_props['left'] > sp_props['right']:
                del sp_props['left']
                del sp_props['right']

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

    def _trj_figure(self, image, tracks, size, name):
        fig = plt.figure(dpi=self.GALLERY_DPI, figsize=size)
        axes = fig.add_subplot(111, frameon=False)
        plots.trj_gallery(image, np.array(tracks),
                          title=name, cmap=self.classdef.colormap, axes=axes,
                          linewidth=1.5, offset=-5)
        fig.subplots_adjust(top=0.95, bottom=0.01, right=0.99, left=0.01)
        return fig

    def export_hmm(self, filename, grouping="Position"):
        """Export two files. One contains the labels after hmm. The other
        contains the object indices of the ch5 files.
        """

        try:
            fp1 = open(filename, "wb")
            fp2 = open(filename.replace(".csv", "_indices.csv"), "wb")

            writer1 = csv.writer(fp1, delimiter=",")
            writer2 = csv.writer(fp2, delimiter=",")
            # first bucket that contains an hmm
            nframes = [v for v in self.data.values()
                       if v is not None][0].nframes
            header = ["# %s" %grouping] + range(1, nframes+1, 1)
            writer1.writerow(header)
            writer2.writerow(header)

            for name, bucket in self.data.iteritems():
                if bucket is None:
                    continue
                for objidx, hmm_labels, _  in bucket.itertracks():
                    writer1.writerow([name]+hmm_labels.tolist())
                    writer2.writerow([name]+objidx.tolist())
        finally:
            fp1.close()
            fp2.close()


    def hmm_model(self, filename, figsize=(20, 12)):
        pdf = PdfPages(filename)
        sp_props = dict(top=0.85, bottom=0.05, hspace=0.28, wspace=0.28,
                        left=0.05, right=0.95)
        try:
            fig, axarr = plt.subplots(nrows=3, ncols=6, figsize=figsize)
            fig.subplots_adjust(**sp_props)

            for j, name in enumerate(sorted(self.data.keys())):
                data = self.data[name]
                i = j%6
                if not i and j:
                    pdf.savefig(fig)
                    fig, axarr = plt.subplots(nrows=3, ncols=6,
                                              figsize=figsize)
                    fig.subplots_adjust(**sp_props)

                if data is None:
                    self._empty_figure(axarr, name, i, nrows=3)
                    continue

                title = '%s, (%d tracks)' %(name, data.ntracks)
                title = os.linesep.join(textwrap.wrap(title, 35))
                classnames = [self.classdef.names[k]
                              for k in sorted(self.classdef.names.keys())]
                plots.hmm_matrix(data.startprob.reshape(-1, 1).T,
                                 xticks=classnames,
                                 xlabel='start prob.', text=title,
                                 axes=axarr[0, i])
                plots.hmm_matrix(data.transmat, xticks=classnames,
                                 yticks=classnames,
                                 xlabel='transition matrix', axes=axarr[1, i])
                plots.hmm_matrix(data.emismat, xticks=classnames,
                                 yticks=classnames,
                                 xlabel='emission matrix', axes=axarr[2, i])
            self._frame_off(axarr, i, 3)
            pdf.savefig(fig)
        finally:
            pdf.close()

    # XXX perhaps this method should be part of the cellh5 module
    def _load_gallery(self, pos, objidx, region, size):
        """Load a gallery image color coded  i.e. grey for
        single channels, rgb colors for merged channels"""

        path = 'definition/object/%s' %region
        rtype = [t for t in pos.definitions.get_file_handle()[path].value[0]]

        if rtype[1] == CH5Const.REGION:
            img = grey2rgb(pos.get_gallery_image(objidx, region, size))
        else:
            # for merged channels we merged singe region to rgb
            for reg in rtype[2:]:
                color = pos.channel_color_by_region(reg)
                try:
                    img += grey2rgb(pos.get_gallery_image(objidx, reg, size),
                                    color)
                except NameError:
                    img = grey2rgb(pos.get_gallery_image(objidx, reg, size),
                                   color)
        return img


    def image_gallery_png(self, ch5, ofile, n_galleries=50, rsfactor=0.4,
                          gsize=100):
        """Resolution of png gallerie can be adjusted by the resampling factor
        (default=0.4). File size is large"""

        for name in sorted(self.data.keys()):
            data = self.data[name]
            if data is None:
                continue
            image = np.array([])
            for objidx, track, coords in data.itertracks(n_galleries):
                pos = ch5.get_position(coords.well, coords.position)
                img = self._load_gallery(pos, objidx, coords.region, gsize)
                img = self._draw_labels(img, track)
                try:
                    image = np.vstack((image, img))
                except ValueError:
                    image = img

            fn = ofile.replace('_gallery.png', '-%s_gallery.png' %name)
            vimage = rescale(image, rsfactor)
            imsave(fn, img_as_float(vimage))

    def _draw_labels(self, image, track, markersize=0.20):
        nframes = len(track)
        size = int(round(image.shape[1]/nframes, 0)), image.shape[0]
        msize = int(round(size[0]*markersize, 0))
        image[size[1]-int(msize/4):size[1], :] = hex2rgb("#FFFFFF")

        for i, label in enumerate(track):
            name = self.classdef.names[label]
            color = np.array(hex2rgb(self.classdef.colors[name], mpl=False),
                             dtype=int)
            image[size[1]-msize:size[1], i*size[0]:i*size[0]+msize] = color
        return image
