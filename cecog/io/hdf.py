"""
hdf.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


__all__ = ('Ch5File', )


import os
import collections
import filelock


import h5py
import glob
import numpy as np
from itertools import izip

Plate = "/data/"
Well = "/data/{}"
Site = "/data/{}/{}/{}"


LayoutDtype = np.dtype(
    [('File', 'S10'), ('Well', 'S3'), ('Site', '<i8'),
     ('Row', 'S1'), ('Column', '<i8'), ('GeneSymbol', 'S6'),
     ('siRNA', 'S8'), ('Group', 'S10')])


def mergeHdfFiles(target, source_dir, remove_source=True, mode="a"):

    hdffiles = glob.glob(os.path.join(source_dir, '*.ch5'))
    target = Ch5File(target, mode=mode)

    for i, h5 in enumerate(hdffiles):
        source = Ch5File(os.path.abspath(h5), 'r')

        if i == 0:
            target.copy(source['/layout'], '/layout')
            target.copy(source['/definition'], "/definition")

        first_item = lambda view: next(iter(view))
        plate = first_item(source[Plate].keys())
        well = first_item(source[Well.format(plate)].keys())
        position = first_item(source[Site.format(plate, well, "")].keys())

        path = str(Site.format(plate, well, position))
        target.copy(source[path], path)

        source.close()

        if remove_source:
            try:
                os.remove(h5)
            except Exception as e:
                pass

            try:
                os.remove(h5.replace(".ch5", ".tmp"))
            except Exception as e:
                pass

    target.close()


class FileLock(filelock.FileLock):

    def release(self, *args, **kw):

        # XXX Dirty work around for the cluster
        try:
            super(FileLock, self).release(*args, **kw)
        except IOError as e:
            pass

        if not self.is_locked:
            try:
                os.remove(self.lock_file)
            except OSError:
                pass


class SiteCoordinate(object):

    def __init__(self, plate, well, site, mask=None):

        self.site = site
        self.well = well
        self.plate = plate
        self.mask = None

    def __str__(self):
        return "/data/{}/{}/{}".format(self.plate, self.well, self.site)

    def join(self, *args):
        return "{}/{}".format(str(self), "/".join(args))

# some methods are copied from the original cellh5
class Ch5File(h5py.File):

    Layout = "/layout"
    Defintion = "/defintion"
    Region = "region"

    def __init__(self, filename, timeout=60, mode='a', cached=False):
        self.lock = FileLock(filename.replace("ch5", "lock"))
        self.lock.acquire(timeout=timeout)
        super(Ch5File, self).__init__(filename, mode)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        super(Ch5File, self).close()
        self.lock.release()

    def plates(self):
        """Return a tuple of plate names."""
        return tuple(self[Plate])

    def wells(self, plate):
        return self[Well.format(plate)].keys()

    def sites(self, plate, well):
        return self[Site.format(plate, well, "")].keys()

    def iterSites(self, as_path=False):
        for plate in self[Plate].keys():
            for well in self.wells(plate):
                for site in self.sites(plate, well):
                    yield SiteCoordinate(plate, well, site)

    def existingSites(self, plate):
        """Returns a dictionary with well names as keys and list of site
        names as values."""

        wsites = dict()

        try:
            wells = self[Well.format(plate)].keys()
            for well in wells:
                sites = self[Site[:-2].format(plate, well)]
                # remove empty sites from list
                sites = [k for k, s in sites.items()]
                wsites[well] = sites
        except (KeyError, AttributeError):
            pass

        return wsites

    def numberSites(self, plate):
        """Count sites that are not empty hdf groups."""
        return sum([len(site) for site in self.existingSites(plate).values()])

    def hasClassifier(self, mask):
        path = 'definition/feature/%s/object_classification' %mask
        return path in self

    def classDefinition(self, mask):
        return self["/definition/feature/{}/object_classification/class_labels".format(mask)].value

    def hasDefinition(self):
        """Check if file contains a experimental layout for a specific plate."""
        return self.Defintion in self

    def layout(self, plate):
        path = "{}/{}".format(self.Layout, plate)

        return self[path].value

    def hasLayout(self, plate):
        """Check if file contains a experimental layout for a specific plate."""
        return "{}/{}" %(self.Layout, plate) in self

    def savePlateLayout(self, layout, platename):
        """Save experimental layout for using the platename."""

        if isinstance(layout, basestring):
            layout = Ch5File.layoutFromTxt(layout)

        grp = self.require_group(self.Layout)

        if platename not in grp:
            dset = grp.create_dataset(platename, data=layout)

    @staticmethod
    def layoutFromTxt(filename):
        """Read plate layout from text file and return a structured array."""

        if not os.path.isfile(filename):
            msg = "No Plate Layout provided. File not found {}".format(filename)
            raise IOError(msg)

        try:
            rec = np.recfromtxt(filename, dtype=LayoutDtype, skip_header=True)
        except ValueError:
            rec = np.recfromtxt(filename, dtype=LayoutDtype, delimiter="\t",
                                skip_header=True)

        return rec

    def hasEvents(self, path):
        # either group is emtpy or key does not exist
        try:
            path = "{}/object/event".format(path)
            return bool(self[path].size)
        except KeyError:
            return False

    def events(self, site, output_second_branch=False):

        if not self.hasEvents(site):
            return numpy.array([])
        else:
            evtable = self[site.join("object", "event")].value

        ids = np.unique(evtable['obj_id'])

        tracks = list()
        for id_ in ids:
            i = np.where(evtable['obj_id'] == id_)[0]
            idx1 = evtable['idx1'][i]
            idx2 = evtable['idx2'][i]

            # find the index of the common elements in the array
            mc, occurence = collections.Counter(idx1).most_common(1)[0]

            if occurence == 1:
                track = np.hstack((idx1, idx2[-1]))
                tracks.append(track)
            elif occurence == 2:
                i1, i2 = np.where(idx1 == mc)[0]
                track = np.hstack((idx1[:i2], idx2[i2 - 1]))
                tracks.append(track)

                if output_second_branch:
                    track = np.hstack((idx1[:(i1 + 1)], idx2[i2:]))
                    tracks.append(track)
            else:
                raise RuntimeError(("Split events with two daughter cells are not supported."))

        return np.array(tracks)

    def predictions(self, site, mask, type="label"):
        path = site.join("feature", mask, "object_classification", "prediction")

        cldef = self.classDefinition(mask)

        # in case that no objects are found
        try:
            prediction = self[path].value["label_idx"]
        except KeyError:
            predciton = list()

        if type == "label":
            return [cldef["label"][i] if i >= 0 else -99
                    for i in prediction]
        elif type == "name":
            return [cldef["name"][i].decode() if i >= 0 else "Unclassified"
                    for i in prediction]

    def probabilities(self, site, mask):
        path = site.join("feature", mask, "object_classification", "probability")
        return self[path].value

    def maskColor(self, mask):
        """Hex color of a segmenation mask."""

        rdef = self['/definition/image/region'].value
        i = rdef['channel_idx'][rdef['region_name'] == 'region___{}'.format(mask)][0]
        return self['/definition/image/channel']['color'][i]

    def galleryImage(self, index, site, mask, size=60):

        if isinstance(index, np.ndarray):
            index = index.tolist()
        elif isinstance(index, int):
            index = np.array([index])

        images = list()

        path = '/definition/image/region'
        idx = self[path]['channel_idx'][self[path]['region_name'] == 'region___{}'.format(mask)][0]
        width, height = self[site.join("image", "channel")].shape[3:5]

        path = site.join("feature", mask, "center")
        centers = self[path][index]
        hsize = size/2

        for i, cen in izip(index, centers):
            p1 = site.join("object", mask)
            p2 = site.join("image", "channel")

            tidx = self[p1][i]['time_idx']
            xmin = max(0, cen[1] - hsize)
            xmax = min(width, cen[1] + hsize)
            ymin = max(0, cen[0] - hsize)
            ymax =  min(height, cen[0] + hsize)

            thumbnail = self[p2][idx, tidx, 0, xmin:xmax, ymin:ymax]

            if thumbnail.shape != (size, size):
                image = np.zeros((size, size), dtype=np.uint8)
                image[(image.shape[0] - thumbnail.shape[0]):, :thumbnail.shape[1]] = thumbnail
                images.append(image)
            else:
                images.append(thumbnail)

        if len(index) > 1:
            return np.concatenate(images, axis=1)
        else:
            return images[0]
