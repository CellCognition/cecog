"""
exporter.py

Exporters for numerical data to text/csv files
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

__all__ = ['TC3Exporter']

import numpy as np
from  numpy.lib._iotools import NameValidator
from os.path import join
from collections import OrderedDict
from matplotlib.backends.backend_pdf import PdfPages

from cecog import plots
from cecog.colors import unsupervised_cmap

class TC3Exporter(object):
    """Export and plot tc3 data. That include trajectory plots,
    label matrices as csv files and box plots.
    """

    def __init__(self, data, outputdir, nclusters,
                 stepwidth=1.0, timeunit='frames', position=''):
        assert isinstance(data, dict)
        self._nclusters = nclusters
        self._data = data
        self._odir = outputdir
        self.stepwidth = stepwidth
        self.timeunit = timeunit
        self._position = position

    def dwell_times(self, labels):
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
            counts[key]  = np.array(value)*self.stepwidth

        return counts

    def __call__(self, labels=(2,3), filename='trajectory_plots.pdf',
                 exclude_labels=(0, )):

        cmap = unsupervised_cmap(self._nclusters)
        try:
            pdf = PdfPages(join(self._odir, filename))
            for title_, tracks in self._data.iteritems():
                title = '%s (%s)' %(self._position, title_.lower())

                # checking for binary matrix
                if np.unique(tracks).size == 2:
                    is_binary = True
                    labels_ = (1, )
                else:
                    is_binary = False
                    labels_ = labels

                # trajectory plots
                fig = plots.trajectories(tracks, labels_, title=title, cmap=cmap)
                pdf.savefig(fig)

                delchars = NameValidator.defaultdeletechars.copy()
                delchars.remove('-')
                validator = NameValidator(case_sensitive='lower',
                                          deletechars=delchars)
                fname = validator.validate(title)[0]+'.csv'
                np.savetxt(join(self._odir, fname), tracks, fmt='%d',
                           delimiter=',')

                # boxplots
                if not is_binary:
                    ylabel = "dwell time (%s)" %self.timeunit
                    xlabel = "class labels"

                    dwell_times = self.dwell_times(tracks)
                    fig1 = plots.dwell_boxplot(dwell_times, title,
                                               ylabel=ylabel, xlabel=xlabel,
                                               exclude_labels=exclude_labels,
                                               cmap=cmap)
                    fig2 = plots.barplot(dwell_times, title, xlabel=xlabel,
                                         ylabel=ylabel,
                                         exclude_labels=exclude_labels,
                                         cmap=cmap)
                    pdf.savefig(fig1)
                    pdf.savefig(fig2)
        finally:
            pdf.close()
