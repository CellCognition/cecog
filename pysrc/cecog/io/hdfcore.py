"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

#-------------------------------------------------------------------------------
# standard library imports:
#
import numpy
import matplotlib.pyplot as mpl
import h5py
import collections
import functools
import base64
import zlib
try:
    import vigra
except ImportError:
    print 'VIGRA is not installed. Please, install from source of download binary at http://www.lfd.uci.edu/~gohlke/pythonlibs/'

#-------------------------------------------------------------------------------
# Constants:
#

GALLERY_SIZE = 60    

#-------------------------------------------------------------------------------
# Functions:
# 
 
class memoize(object):
    """cache the return value of a method
    
    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.
    
    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object_):
        @memoize
        def add_to(self, arg):
            return self + arg
    Obj.add_to(1) # not enough arguments
    Obj.add_to(1, 2) # returns 3, result is not cached
    """
    def __init__(self, func):
        self.func = func
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return functools.partial(self, obj)
    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        if key in cache:
            res = cache[key]
        else:
            res = cache[key] = self.func(*args, **kw)
        return res
    
    
def hex_to_rgb(hex_string, truncate_to_one=False):
    """
    Converts the hex representation of a RGB value (8bit per channel) to
    its integer components.

    Example: hex_to_rgb('#559988') = (85, 153, 136)
             hex_to_rgb('559988') = (85, 153, 136)

    @param hexString: the RGB value
    @type hexString: string
    @return: RGB integer components (tuple)
    """
    if hex_string[:2] == '0x':
        hex_value = int(hex_string, 16)
    elif hex_string[0] == '#':
        hex_value = int('0x'+hex_string[1:], 16)
    else:
        hex_value = int('0x'+hex_string, 16)
    b = hex_value & 0xff
    g = hex_value >> 8 & 0xff
    r = hex_value >> 16 & 0xff
    
    if truncate_to_one:
        r = r / float(255)
        g = g / float(255)
        b = b / float(255)
    return (r, g, b)

#-------------------------------------------------------------------------------
# Classes:
#

class CH5Position(object):
    def __init__(self, plate, well, pos, grp_pos, parent):
        self.plate = plate
        self.well = well
        self.pos = pos
        self.grp_pos = grp_pos
        self.definitions = parent
        
    def __getitem__(self, key):
        return self.grp_pos[key]
    
    def get_tracking(self):
        return self.grp_pos['object']['tracking'].value
    
    def get_class_prediction(self, object_='primary__primary'):
        return self['feature'] \
                   [object_] \
                   ['object_classification'] \
                   ['prediction'].value
                   
    def has_classification(self, object_):
        return 'object_classification' in self['feature'][object_] 
                   
    def get_crack_contour(self, index, object_='primary__primary', bb_corrected=True):
        if not isinstance(index, (list, tuple)):
            index = (index,)
        crack_list = []
        for ind in index:
            crack_str = self['feature'][object_]['crack_contour'][ind]
            crack = numpy.asarray(zlib.decompress( \
                             base64.b64decode(crack_str)).split(','), \
                             dtype=numpy.float32).reshape(-1,2)
            
            if bb_corrected:
                bb = self['feature'][object_]['center'][ind]
                crack[:,0] -= bb[0] - GALLERY_SIZE/2
                crack[:,1] -= bb[1] - GALLERY_SIZE/2 
                crack.clip(0, GALLERY_SIZE)
                
            crack_list.append(crack)
 
        return crack_list
    
    def get_object_features(self, object_='primary__primary'):
        return self['feature'] \
                   [object_] \
                   ['object_features'].value
                   
                   
    def get_image(self, t, c, z=0):
        return self['image'] \
                    ['channel'] \
                    [c, t, z, :, :]
                   
    def get_gallery_image(self, index, object_='primary__primary'):
        if not isinstance(index, (list, tuple)):
            index = (index,)
        image_list = []
        for ind in index:
            time_idx = self['object'][object_][ind]['time_idx']
            cen1 = self['feature'][object_]['center'][ind]
            image = numpy.zeros((GALLERY_SIZE,GALLERY_SIZE))
            channel_idx = self.definitions.image_definition['region']['channel_idx'][self.definitions.image_definition['region']['region_name'] == 'region___%s' % object_]
            tmp_img = self['image'] \
                             ['channel'] \
                             [channel_idx, time_idx, 0,
                              max(0, cen1[1]-GALLERY_SIZE/2):min(1040,cen1[1]+GALLERY_SIZE/2), 
                              max(0, cen1[0]-GALLERY_SIZE/2):min(1389,cen1[0]+GALLERY_SIZE/2)]
            image[:tmp_img.shape[0],:tmp_img.shape[1]] = tmp_img
            image_list.append(image)
        return numpy.concatenate(image_list, axis=1)
    
    def get_gallery_image_rgb(self, index, object_=('primary__primary',)):
        if len(object_) == 1:
            img_ = self.get_gallery_image(index, object_[0])
            rgb_shape = img_.shape + (3,)
            img = numpy.zeros(rgb_shape, img_.dtype)
            for c in range(3): img[:,:,c] = img_
            return img
        
        for c in range(3):
            if c == 0:
                img_ = self.get_gallery_image(index, object_[c])
                rgb_shape = img_.shape + (3,)
                img = numpy.zeros(rgb_shape, img_.dtype)
                img[:,:, 0] = img_
            if 0 < c < len(object_):
                img[:,:,c] = self.get_gallery_image(index, object_[c])
                
        return img
                
        
        
        
    def get_gallery_image_contour(self, index, object_=('primary__primary',), color=None):
        img = self.get_gallery_image_rgb(index, object_)
        for obj_id in object_:
            crack = self.get_crack_contour(index, obj_id)
            
            
            if color is None:
                class_color = self.get_class_color(index, obj_id)
                if class_color is None:
                    class_color = ['#FFFFFF']*len(crack)
                    
                if not isinstance(class_color, (list, tuple)):
                    class_color = [class_color]
            else:
                class_color = [color]*len(crack)
                
            for i, (cr, col) in enumerate(zip(crack, class_color)):
                col_tmp = hex_to_rgb(col)
                for x, y in cr:
                    for c in range(3):
                        img[y, x + i* GALLERY_SIZE, c] = col_tmp[c] 
                    
        return img
            
    
    def get_class_label(self, index, object_='primary__primary'):
        if not isinstance(index, (list, tuple)):
            index = [index]
        return self.get_class_prediction(object_)['label_idx'][[x for x in index]] + 1
    
    def get_class_color(self, index, object_='primary__primary'):
        if not self.has_classification(object_):
            return
        res = map(str, self.class_color_def(tuple(self.get_class_label(index, object_)), object_))
        if len(res) == 1:
            return res[0]
        return res
    
    def get_time_idx(self, index, object_='primary__primary'):
        return self['object'][object_][index]['time_idx']
    
    def get_class_name(self, index, object_='primary__primary'):
        res = map(str, self.class_name_def(tuple(self.get_class_label(index)), object_))
        if len(res) == 1:
            return res[0]
        return res
          
    def class_color_def(self, class_labels, object_):
        class_mapping = self.definitions.class_definition(object_)
        return [class_mapping['color'][col-1] for col in class_labels]
    
    def class_name_def(self, class_labels, object_):
        class_mapping = self.definitions.class_definition(object_)
        return [class_mapping['name'][col-1] for col in class_labels]
    
    def object_feature_def(self, object_='primary__primary'):
        return map(lambda x: str(x[0]), self.definitions.feature_definition['%s/object_features' % object_].value)
    
    def get_object_table(self, object_):
        return self['object'][object_].value
    
    def get_feature_table(self, object_, feature):
        return self['feature'][object_][feature].value
    
    def get_events(self, output_second_branch=False):
        dset_event = self.get_object_table('event')
        events = []
        for event_id in range(dset_event['obj_id'].max()):
            idx = numpy.where(dset_event['obj_id'] == event_id)
            idx1 = dset_event[idx]['idx1']
            idx2 = dset_event[idx]['idx2']
            second_branch_found = False
            event_list = []
            for p1, _ in zip(idx1, idx2):
                if p1 in event_list:
                    # branch ends
                    second_branch_found = True
                    break
                else:
                    event_list.append(p1)
            
            if second_branch_found and output_second_branch:
                a = list(idx1).index(p1)
                b = len(idx1) - list(idx1)[-1:0:-1].index(p1) - 1
                event_list2 = list(idx1[0:a]) + list(idx1[b:])
                events.append([event_list, event_list2])
            else:
                #events.append([event_list])
                events.append(event_list)
                
        return events
    
    def _track_single(self, start_idx, type):
        if type == 'first':
            sel = 0
        elif type == 'last':
            sel = -1
        else:
            raise NotImplementedError('type not supported')
            
        
        ### follow last cell
        idx_list = []
        dset_tracking = self.get_tracking()

        idx = start_idx
        while True:
            next_p_idx = (dset_tracking['obj_idx1']==idx).nonzero()[0]
            if len(next_p_idx) == 0:
                break
            idx = dset_tracking['obj_idx2'][next_p_idx[sel]]
            idx_list.append(idx)
        return idx_list
    
    def track_first(self, start_idx):
        return self._track_single(start_idx, 'first')
    
    def track_last(self, start_idx):
        return self._track_single(start_idx, 'last')
        
    def track_all(self, start_idx):
        dset_tracking = self.get_tracking()
        next_p_idx = (dset_tracking['obj_idx1']==start_idx).nonzero()[0]
        if len(next_p_idx) == 0:
            return [None]
        else:
            def all_paths_of_tree(id):
                found_ids = dset_tracking['obj_idx2'][(dset_tracking['obj_idx1']==id).nonzero()[0]]
                
                if len(found_ids) == 0:
                    return [[id]]
                else:
                    all_paths_ = []
                    for out_id in found_ids:
                        for path_ in all_paths_of_tree(out_id):
                            all_paths_.append([id] + path_)
        
                    return all_paths_ 
                
            head_ids = dset_tracking['obj_idx2'][(dset_tracking['obj_idx1']==start_idx).nonzero()[0]]
            res = []
            for head_id in head_ids:
                res.extend(all_paths_of_tree(head_id)   )
            return res

class CH5CachedPosition(CH5Position):
    def __init__(self, *args, **kwargs):
        super(CH5CachedPosition, self).__init__(*args, **kwargs)
        
    @memoize
    def get_events(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_events(*args, **kwargs)
    
    @memoize
    def get_object_table(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_object_table(*args, **kwargs)
    
    @memoize
    def get_feature_table(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_feature_table(*args, **kwargs)
    
    @memoize
    def get_tracking(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_tracking(*args, **kwargs)
    
    @memoize
    def get_class_prediction(self, object_='primary__primary'):
        return super(CH5CachedPosition, self).get_class_prediction(object_)

    @memoize
    def get_object_features(self, object_='primary__primary'):
        return super(CH5CachedPosition, self).get_object_features(object_)
    
    @memoize
    def get_gallery_image(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_gallery_image(*args, **kwargs)
    
    @memoize
    def class_name_def(self, class_labels, object_='primary__primary'):
        return super(CH5CachedPosition, self).class_name_def(class_labels, object_)
    
    @memoize
    def class_color_def(self, class_labels, object_='primary__primary'):
        return super(CH5CachedPosition, self).class_color_def(class_labels, object_)
    
    @memoize
    def object_feature_def(self, object_='primary__primary'):
        return super(CH5CachedPosition, self).object_feature_def(object_)
    
    @memoize
    def get_class_name(self, class_labels, object_='primary__primary'):
        return super(CH5CachedPosition, self).get_class_name(class_labels, object_)
        
    @memoize
    def get_class_color(self, class_labels, object_='primary__primary'):
        return super(CH5CachedPosition, self).get_class_color(class_labels, object_)
    
    def clear_cache(self):
        if hasattr(self, '_memoize__cache'):
            self._memoize__cache = {}
    
class CH5File(object):
    POSITION_CLS = CH5CachedPosition
    def __init__(self, filename):
        self._file_handle = h5py.File(filename, 'r')
        self.plate = self._get_group_members('/sample/0/plate/')[0]
        self.wells = self._get_group_members('/sample/0/plate/%s/experiment/' % self.plate)
        self.positions = collections.OrderedDict()
        for w in sorted(self.wells):
            self.positions[w] = self._get_group_members('/sample/0/plate/%s/experiment/%s/position/' % (self.plate, w))
                                                        
#        print 'Plate', self.plate
#        print 'Positions', self.positions
        self._position_group = {}
        for w, pos_list in self.positions.items():
            for p in pos_list:
                #print '/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)
                self._position_group[(w,p)] = CH5File.POSITION_CLS(self.plate, w, p, self._file_handle['/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)], self)
        self.current_pos = self._position_group.values()[0]
        
    def get_position(self, well, pos):
        return self._position_group[(well, pos)]
    
    def set_current_pos(self, well, pos):
        self.current_pos = self.get_position(well, pos)
        
    def _get_group_members(self, path):
        return map(str, self._file_handle[path].keys())
    
    @memoize
    def class_definition(self, object_):
        return self._file_handle['/definition/feature/%s/object_classification/class_labels' % object_].value
    
    @property
    def feature_definition(self):
        return self._file_handle['/definition/feature']
    
    @property
    def image_definition(self):
        return self._file_handle['/definition/image']
    
    def close(self):
        self._file_handle.close()    
    
    
import unittest

class CH5TestBase(unittest.TestCase):
    def setUp(self):
        self.fh = CH5File('0038-cs.h5')
        self.well_str = '0'
        self.pos_str = self.fh.positions[self.well_str][0]
        self.pos = self.fh.get_position(self.well_str, self.pos_str)
        
    def tearDown(self):
        self.fh.close()
class TestCH5Basic(CH5TestBase): 
    def testGallery(self):
        a1 = self.pos.get_gallery_image(1)
        b1 = self.pos.get_gallery_image(2)
        a2 = self.pos.get_gallery_image(1)
        
        self.assertTrue(a1.shape == (GALLERY_SIZE, GALLERY_SIZE))
        self.assertTrue(b1.shape == (GALLERY_SIZE, GALLERY_SIZE))
        self.assertTrue(numpy.all(a1 == a2))
        self.assertFalse(numpy.all(a1 == b1))
        
    def testGallery2(self):
        event = self.pos.track_first(5)
        a1 = self.pos.get_gallery_image(tuple(event))
        a2 = self.pos.get_gallery_image(tuple(event), 'secondary__expanded')
#        vigra.impex.writeImage(a1.swapaxes(1,0), 'c:/Users/sommerc/Desktop/bla.png')
#        vigra.impex.writeImage(a2.swapaxes(1,0), 'c:/Users/sommerc/Desktop/foo.png')
        
    def testGallery3(self):
        event = self.pos.get_events()[42][0]
        tracks = self.pos.track_all(event)
        w = numpy.array(map(len, tracks)).max()*GALLERY_SIZE
        img = numpy.zeros((GALLERY_SIZE * len(tracks), w), dtype=numpy.uint8)
        
        for k, t in enumerate(tracks):
            a = self.pos.get_gallery_image(tuple(t))
            img[k*GALLERY_SIZE:(k+1)*GALLERY_SIZE, 0:a.shape[1]] = a
#        vigra.impex.writeImage(img.swapaxes(1,0), 'c:/Users/sommerc/Desktop/foo.png')
        
    def testGallery4(self):
        event = self.pos.get_events()[42]
        a1 = self.pos.get_gallery_image(tuple(event))
#        vigra.impex.writeImage(a1.swapaxes(1,0), 'c:/Users/sommerc/Desktop/blub.png')   
              
    def testClassNames(self):
        for x in ['inter', 'pro', 'earlyana']:
            self.assertTrue(x in self.pos.class_name_def((1,2,5)))
     
    def testClassColors(self):
        for x in ['#FF8000', '#D28DCE', '#FF0000']:
            self.assertTrue(x in self.pos.class_color_def((3,4,8)))   
            
    def testClassColors2(self):
        self.pos.get_class_color((1,221,3233,44244)) 
        self.pos.get_class_name((1,221,3233,44244)) 
         
    def testEvents(self):
        self.assertTrue(len(self.pos.get_events()) > 0)
        self.assertTrue(len(self.pos.get_events()[0]) > 0)
        
    def testTrack(self):
        self.assertTrue(len(self.pos.track_first(42)) > 0)
        
    def testTrackFirst(self):
        self.assertListEqual(self.pos.track_first(42), 
                             self.pos.track_all(42)[0])
        
    def testTrackLast(self):  
        self.assertListEqual(self.pos.track_last(1111), 
                             self.pos.track_all(1111)[-1])
        
    def testObjectFeature(self):
        self.assertTrue('n2_avg' in  self.pos.object_feature_def())
        self.assertTrue(self.pos.get_object_features().shape[1] == 239)
 
class TestCH5Examples(CH5TestBase):   
    def testReadAnImage(self):
        """Read an raw image an write a sub image to disk"""
        # read the images at time point 1
        h2b = self.pos.get_image(0, 0)
        tub = self.pos.get_image(0, 1)

        # Print part of the images
        # prepare image plot
        fig = mpl.figure(frameon=False)
        ax = mpl.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        ax.imshow(h2b[400:600, 400:600], cmap='gray')
        fig.savefig('img1.png', format='png')
        ax.imshow(tub[400:600, 400:600], cmap='g2ay')
        #fig.savefig('img2.png', format='png')
        
#        vigra.impex.writeImage(h2b[400:600, 400:600].swapaxes(1,0), 'img1.png')   
#        vigra.impex.writeImage(tub[400:600, 400:600].swapaxes(1,0), 'img2.png')   
        
#    unittest.skip('ploting so many lines is very slow in matplotlib')
    def testPrintTrackingTrace(self):
        """Show the cell movement over time by showing the trace of each cell colorcoded 
           overlayed on of the first image"""
        h2b = self.pos.get_image(0, 0)
        
        tracking = self.pos.get_object_table('tracking')
        nucleus = self.pos.get_object_table('primary__primary')
        center = self.pos.get_feature_table('primary__primary', 'center')
        
        
        # prepare image plot
        fig = mpl.figure(frameon=False)
        ax = mpl.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        ax.imshow(h2b, cmap='gray')
        
        # on top of the image a white circle is plotted for each center of nucleus.
        I = numpy.nonzero(nucleus[tracking['obj_idx1']]['time_idx'] == 0)[0]
        for x, y in center[I]:
            ax.plot(x,y,'w.', markersize=7.0, scaley=False, scalex=False)
            
        ax.axis([0, h2b.shape[1], h2b.shape[0], 0])
        
        # a line is plotted between nucleus center of each pair of connected nuclei. The color is the mitotic phase
        for idx1, idx2 in zip(tracking['obj_idx1'], 
                              tracking['obj_idx2']):
            color = self.pos.get_class_color(idx1)
            (x0, y0), (x1, y1) = center[idx1], center[idx2]
            ax.plot([x0, x1],[y0, y1], color=color)
            
        fig.savefig('tracking.png', format='png')
        
    def testComputeTheMitoticIndex(self):
        """Read the classification results and compute the mitotic index"""
        
        nucleus = self.pos.get_object_table('primary__primary')
        predictions = self.pos.get_class_prediction('primary__primary')
        
        colors = self.pos.definitions.class_definition('primary__primary')['color']
        names = self.pos.definitions.class_definition('primary__primary')['name']
        
        n_classes = len(names)
        time_max = nucleus['time_idx'].max()
        
        # compute mitotic index by counting the number cell per class label over all times
        mitotic_index =  numpy.array(map(lambda x: [len(numpy.nonzero(x==class_idx)[0]) for class_idx in range(n_classes)], 
            [predictions[nucleus['time_idx'] == time_idx]['label_idx'] for time_idx in range(time_max)]))
        
        # plot it
        fig = mpl.figure()
        ax = fig.add_subplot(111)
        
        for i in range(1, n_classes):
            ax.plot(mitotic_index[:,i], color=colors[i], label=names[i])
            
        ax.set_xlabel('time')
        ax.set_ylabel('number of cells')
        ax.set_title('Mitotic index')
        ax.set_xlim(0, time_max)
        ax.legend(loc='upper left')
        fig.savefig('mitotic_index.pdf', format='pdf')
             
    def testShowMitoticEvents(self):
        """Extract the mitotic events and write them as gellery images"""
        events = self.pos.get_events()
        
        image = []
        for event in events[:5]:
            image.append(self.pos.get_gallery_image(tuple(event)))
        #vigra.impex.writeImage(numpy.concatenate(image, axis=0).swapaxes(1,0), 'mitotic_events.png')

if __name__ == '__main__':
    unittest.main()