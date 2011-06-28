import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

class TimeseriesPlotter(object):
    def __init__(self, plotDir):
        self.plotDir = plotDir

    def makeSingleTimeseriesPlot(self, timevec, datavec,
                                 filename,
                                 linewidth=2,
                                 title='time series',
                                 ylabel='Feature Value',
                                 xlabel='Time in Frames',
                                 color='x0000EE',
                                 axis=None):

        # new figure
        plt.figure(1)
        plt.subfigure(1,1,1)

        # plot
        plt.plot(timevec, datavec, linewidth=linewidth,
                 color=color)
        plt.grid(b=True, which='major', linewidth=1.5)
        if axis is None:
            axis = [min(timevec), max(timevec), min(datavec), max(datavec)]
        plt.axis(axis)

        # add labels/title
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)

        # write and close
        plt.savefig(os.path.join(self.plotDir, filename))
        plt.close(1)

        return