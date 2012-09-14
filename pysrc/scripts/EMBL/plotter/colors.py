import os, time, re
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy

class ColorMap(object):
    def __init__(self):
        # divergent color maps
        self.div_basic_colors_intense = ["#E41A1C",
                                         "#377EB8",
                                         "#4DAF4A",
                                         "#984EA3",
                                         "#FF7F00" ]
        self.div_basic_colors_soft = ["#7FC97F",
                                      "#BEAED4",
                                      "#FDC086",
                                      "#FFFF99",
                                      "#386CB0" ]


    def getRGBValues(self, hexvec):
        single_channel = {}
        for c in range(3):
            single_channel[c] = [int(x[(1 + 2*c):(3+2*c)], base=16) / 256.0 for x in hexvec]
        rgbvals = zip(single_channel[0], single_channel[1], single_channel[2])
        return rgbvals

    def makeDivergentColorRamp(self, N, intense=True, hex_output=False):
        if intense:
            basic_colors = self.div_basic_colors_intense
        if not intense:
            basic_colors = self.div_basic_colors_soft

        cr = self.makeColorRamp(N, basic_colors, hex_output)
        return cr

    def makeColorRamp(self, N, basic_colors, hex_output=False):

        if N<1:
            return []
        if N==1:
            return [basic_colors[0]]

        xvals = numpy.linspace(0, len(basic_colors)-1, N)

        single_channel = {}
        for c in range(3):
            xp = range(len(basic_colors))
            yp = [int(x[(1 + 2*c):(3+2*c)], base=16) for x in basic_colors]

            single_channel[c] = [x / 256.0 for x in numpy.interp(xvals, xp, yp)]

        if hex_output:
#            colvec = ['#' + hex(numpy.int32(min(16**4 * single_channel[0][i], 16**6 - 1) +
#                                            min(16**2 * single_channel[1][i], 16**4 - 1) +
#                                            min(single_channel[2][i], 16**2 -1) )).upper()[2:]
#                      for i in range(N)]
            colvec = ['#' + hex(numpy.int32(
                                            (((256 * single_channel[0][i]  ) +
                                              single_channel[1][i]) * 256 +
                                              single_channel[2][i]) * 256
                                              ))[2:]
                      for i in range(N)]

        else:
            colvec = zip(single_channel[0], single_channel[1], single_channel[2])

        return colvec

# make all colormaps and write them to a output folder
def makeAllColorMaps(colormap_folder):

    filename = os.path.join(colormap_folder, 'autumn.png')
    matplotlib.pyplot.autumn()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'bone.png')
    matplotlib.pyplot.bone()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'cool.png')
    matplotlib.pyplot.cool()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'copper.png')
    matplotlib.pyplot.copper()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'flag.png')
    matplotlib.pyplot.flag()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'gray.png')
    matplotlib.pyplot.gray()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'hot.png')
    matplotlib.pyplot.hot()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'hsv.png')
    matplotlib.pyplot.hsv()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'jet.png')
    matplotlib.pyplot.jet()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'pink.png')
    matplotlib.pyplot.pink()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'prism.png')
    matplotlib.pyplot.prism()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'spring.png')
    matplotlib.pyplot.spring()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'summer.png')
    matplotlib.pyplot.summer()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'winter.png')
    matplotlib.pyplot.winter()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()

    filename = os.path.join(colormap_folder, 'spectral.png')
    matplotlib.pyplot.spectral()
    plt.figure(1)
    plt.subplot(1,1,1)
    plt.imshow(numpy.array([[1,2,3], [4,5,6], [7,8,9]]))
    plt.title(filename)
    plt.savefig(filename)
    plt.close()


