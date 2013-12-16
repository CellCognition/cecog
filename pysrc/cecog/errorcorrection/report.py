"""
hmmreport.py

Data container and report class (for pdf generation)

"""
from __future__ import division

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'

__all__ = ['HmmBucket', 'HmmReport']

import csv
from os.path import splitext, basename
from collections import OrderedDict
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from cecog import plots
from cecog.colors import hex2rgb
import vigra


class HmmBucket(object):
    """Container class to store and operate on 'cell trajectories'."""

    __slots__ = ['labels', 'hmm_labels', 'startprob', 'emismat', 'transmat',
                 'groups', 'ntracks', 'stepwidth', '_dwell_times', 'fileinfo',
                 'gallery_files', '_states']

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
        self._states = None

    @property
    def states(self):
        if self._states is None:
            self._states = np.unique(self.labels)
        return self._states

    def iter_gallery(self, n=None, idx=None):
        """Iterator over gallery images and tracks."""

        if n is not None and idx is not None:
            raise RuntimeError(('you can not provide idx and n. '
                                'arguments are exclusive'))

        if idx is None:
            idx = np.arange(0, self.gallery_files.size, 1)
            if n is not None:
                np.random.shuffle(idx)
                idx = idx[:n]

        for track, gallery_file in zip(self.hmm_labels[idx],
                                       self.gallery_files[idx]):
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
                clcol = dict([(k, self.classdef.hexcolors[v])
                             for k, v in self.classdef.class_names.iteritems()
                              if k in data.states])

                plots.hmm_network(data.transmat, clcol, title=title,
                                  axes=axarr[0][i])

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

        for label in self.classdef.class_names.keys():
            dwell_times = OrderedDict([(k, np.array([]))
                                       for k in sorted(self.data.keys())])
            for name, data in self.data.iteritems():
                try:
                    dwell_times[name] = np.concatenate( \
                        (dwell_times[name], data.dwell_times[label]))
                except (KeyError, AttributeError):
                    pass

            title = "class %d (%s)" %(label, self.classdef.class_names[label])
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

    def _read_image(self, file_):
        """try different file extensio to read."""
        try:
            image = vigra.readImage(file_)
        except RuntimeError:
            file_ = file_.replace('png', 'jpg')
            image = vigra.readImage(file_)
        return np.squeeze(image.swapaxes(0, 1).view(np.ndarray))

    def image_gallery_pdf(self, filename, n_galleries=50):
        """Pdf gallery has smaller file size, less resolution of cource but
        is easier to print."""
        pdf = PdfPages(filename)
        try:
            for name in sorted(self.data.keys()):
                data = self.data[name]
                if data is None:
                    continue
                image = np.array([])
                tracks = list()
                for file_, track in data.iter_gallery(n_galleries):
                    tracks.append(track)
                    try:
                        img = self._read_image(file_)
                        image = np.vstack((image, np.mean(img, axis=2)))
                    except ValueError:
                        img = self._read_image(file_)
                        image = np.mean(img, axis=2)

                    aspect = image.shape[0]/image.shape[1]
                    if aspect >= 0.99:
                        fig = self._trj_figure(image, tracks, (6, 6), name)
                        pdf.savefig(fig, dpi=self.GALLERY_DPI)
                        image = np.array([])
                        tracks = list()

                if len(tracks) > 0:
                    fig = self._trj_figure(image, tracks, (6, 6), name)
                    pdf.savefig(fig, dpi=self.GALLERY_DPI)

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

    def image_gallery_png(self, filename, n_galleries=50, rsfactor=0.4):
        """Resolution of png gallerie can be adjusted by the resampling factor
        (default=0.4). File size is large"""

        for name in sorted(self.data.keys()):
            data = self.data[name]
            if data is None:
                continue
            image = np.array([])
            for file_, track in data.iter_gallery(n_galleries):
                try:
                    img = self._read_image(file_)
                    img = self._draw_labels(img, track)
                    image = np.vstack((image, img))
                except ValueError:
                    img = self._read_image(file_)
                    img = self._draw_labels(img, track)
                    image = img

            fn = filename.replace('_gallery.png', '-%s_gallery.png' %name)
            vimage = vigra.RGBImage(image.swapaxes(1, 0))
            vimage = vigra.sampling.resampleImage(vimage, rsfactor)
            vimage.writeImage(fn)

    def _draw_labels(self, image, track, markersize=0.20):
        nframes = len(track)
        size = int(round(image.shape[1]/nframes, 0)), image.shape[0]
        msize = int(round(size[0]*markersize, 0))
        image[size[1]-int(msize/4):size[1], :] = hex2rgb("#FFFFFF")

        for i, label in enumerate(track):
            name = self.classdef.class_names[label]
            color = hex2rgb(self.classdef.hexcolors[name], mpl=False)
            image[size[1]-msize:size[1], i*size[0]:i*size[0]+msize] = color
        return image

    def export_hmm(self, filename, align_in_lines=False):
        """Export a table of tracks names and hmm_labels"""

        with open(filename, "w") as fp:
            if align_in_lines:
                writer = csv.writer(fp, delimiter=",")
                for name, bucket in self.data.iteritems():
                    if bucket is None:
                        continue
                    for fname, hmm_labels in bucket.iter_gallery():
                        writer.writerow([basename(splitext(fname)[0])] + \
                                            hmm_labels.tolist())
            # transpose lines and columns
            else:
                fields = []
                tracks = []
                for name, bucket in self.data.iteritems():
                    if bucket is None:
                        continue
                    for fname, hmm_labels in bucket.iter_gallery():
                        fields.append(basename(splitext(fname)[0]))
                        tracks.append(hmm_labels)

                writer = csv.writer(fp, fields, delimiter=",")
                writer.writerow(fields)
                for line in zip(*tracks):
                    writer.writerow(line)

    def hmm_model(self, filename, figsize=(20, 12)):
        from cecog import plots
        reload(plots)
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
                classnames = [self.classdef.class_names[k]
                              for k in sorted(self.classdef.class_names.keys())]
                plots.hmm_matrix(data.startprob.reshape(-1, 1).T,
                                 xticks=classnames,
                                 xlabel='start prob.', text=title,
                                 axes=axarr[0, i])
                plots.hmm_matrix(data.transmat, xticks=classnames, yticks=classnames,
                                 xlabel='transition matrix', axes=axarr[1, i])
                plots.hmm_matrix(data.emismat, xticks=classnames, yticks=classnames,
                                 xlabel='emission matrix', axes=axarr[2, i])
            self._frame_off(axarr, i, 3)
            pdf.savefig(fig)
        finally:
            pdf.close()
