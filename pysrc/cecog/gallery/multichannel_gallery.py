"""
multichannel_gallery.py

Image Gallery for cell trajectories showing the class labels of all channels
color encoded as little squares.
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

import numpy as np
import vigra

from cecog.colors import hex2rgb

__all__ = ['MultiChannelGallery']

class MultiChannelGallery(object):

    def __init__(self, classdefs, data, imagefrom,
                 n_galleries=50, resampling_factor=0.4):
        self.classdefs = classdefs
        self.n_galleries = n_galleries
        self.rsfactor = resampling_factor
        self._imagefrom = imagefrom
        self.data = data

    def _read_image(self, file_):
        """try different file extensio to read."""
        try:
            image = vigra.readImage(file_)
        except RuntimeError:
            file_ = file_.replace('png', 'jpg')
            image = vigra.readImage(file_)
        return np.squeeze(image.swapaxes(0, 1).view(np.ndarray))

    def __call__(self, filename, channels):
        imagedata = self.data[self._imagefrom]

        for name in sorted(imagedata.keys()):
            data = imagedata[name]
            if data is None:
                continue

            # collect filenames to load and tracks for all channels
            idx = np.arange(0, data.ntracks, 1)
            if self.n_galleries > 0:
                np.random.shuffle(idx)
                idx = idx[:self.n_galleries]

            files = data.gallery_files[idx]
            # preserve the order of the channels
            tracks = [self.data[c][name].hmm_labels[idx] for c in channels]
            classdefs = [self.classdefs[c] for c in channels]

            image = np.array([])
            for ft in zip(files, *tracks):
                file_ = ft[0]
                tracks = ft[1:]
                try:
                    img = self._read_image(file_)
                    img = self._draw_labels(img, tracks, classdefs)
                    image = np.vstack((image, img))
                except ValueError:
                    img = self._read_image(file_)
                    img = self._draw_labels(img, tracks, classdefs)
                    image = img

            fn = filename.replace('.png', '-%s.png' %name)
            vimage = vigra.RGBImage(image.swapaxes(1, 0))
            vimage = vigra.sampling.resampleImage(vimage, self.rsfactor)
            vimage.writeImage(fn)

    def _draw_labels(self, image, tracks, classdefs, markersize=0.12):
        nframes = len(tracks[0])
        size = image.shape[1]/nframes, image.shape[0]
        msize = int(round(size[0]*markersize, 0))
        image[size[1]-int(msize/4):size[1], :] = hex2rgb("#FFFFFF")

        for k, track in enumerate(tracks):
            for i, label in enumerate(track):
                name = classdefs[k].class_names[label]
                color = hex2rgb(classdefs[k].hexcolors[name], mpl=False)
                istart = i*size[0] + k*msize
                iend = i*size[0] + (k+1)*msize
                image[size[1]-msize:size[1], istart:iend] = color
        return image
