"""
hmmreport.py

Data container and report class (for pdf generation)

"""

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'

__all__ = ['HmmBucket', 'HmmReport']


from os.path import join
from collections import namedtuple, OrderedDict
import numpy as np

from cecog import plots
from cecog.errorcorrection import PlateMapping
from matplotlib.backends.backend_pdf import PdfPages

HmmBucket = namedtuple('HmmBucket', ['labels', 'hmm_labels',
                                     'startprob', 'emismat', 'transmat',
                                     'groups', 'ntracks'])

def dwell_times(labels, stepwidth):
    """Determine the dwell time for each consecutive labels sequence.
    Returns an ordered dict with labels as keys and list of duration time as
    values."""

    classes = np.unique(labels)
    counts = OrderedDict()
    for class_ in classes:
        counts.setdefault(class_, [])

    labels = labels.flatten()
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
        counts[key]  = np.array(value)*stepwidth

    return counts

class HmmReport(object):

    def __init__(self, data, ecopts, classdef, outdir):
        self.data = data
        self.ecopts = ecopts
        self.outdir = outdir
        self.classdef = classdef

    def __call__(self):

        sby = self.ecopts.sortby.replace(" ", "_")
        ofile = join(self.outdir, 'hmm-report-%s.pdf' %sby)
        pdf = PdfPages(ofile)
        try:
            for name, data in self.data.iteritems():
                title = '%s, %s, (%d tracks)' %(name, data.groups[PlateMapping.GENE],
                                        data.ntracks)

                # trajectories
                fig = plots.trajectories(data.labels,
                                         labels=self.ecopts.sorting_sequence,
                                         title=title,
                                         cmap=self.classdef.colormap,
                                         norm=self.classdef.normalize)
                pdf.savefig(fig)

                fig = plots.trajectories(data.hmm_labels,
                                         labels=self.ecopts.sorting_sequence,
                                         title=title,
                                         cmap=self.classdef.colormap,
                                         norm=self.classdef.normalize)
                pdf.savefig(fig)

                # hmm network
                clcol = dict([(k, self.classdef.hexcolors[v])
                              for k, v in self.classdef.class_names.iteritems()])
                fig = plots.hmm_network(data.transmat, clcol, title=title)
                pdf.savefig(fig)

                # dwell box/barplots
                ylabel = "dwell time (%s)" %self.ecopts.timeunit
                xlabel = "class labels"

                times = dwell_times(data.hmm_labels, self.ecopts.timelapse)
                fig = plots.dwell_boxplot(times, title, ylabel=ylabel, xlabel=xlabel,
                                          cmap=self.classdef.colormap,
                                          ymax=self.ecopts.tmax)
                pdf.savefig(fig)
                fig = plots.barplot(times, title, xlabel=xlabel, ylabel=ylabel,
                                    cmap=self.classdef.colormap,
                                    ymax=self.ecopts.tmax)
                pdf.savefig(fig)
        finally:
            pdf.close()
