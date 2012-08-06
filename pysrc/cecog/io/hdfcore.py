import numpy
import matplotlib.pyplot as mpl
import h5py
import collections
import functools
import time
import cProfile

GALLERY_SIZE = 100    
  
class memoize(object):
    """cache the return value of a method
    
    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.
    
    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object):
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
    
    def get_class_prediction(self):
        return self['feature'] \
                   ['primary__primary'] \
                   ['object_classification'] \
                   ['prediction'].value
                   
    def get_gallery_image(self, index, object='primary__primary'):
        if not isinstance(index, (list, tuple)):
            index = (index,)
        image_list = []
        for ind in index:
            time_idx = self['object'][object][ind]['time_idx']
            cen1 = self['feature'][object]['center'][ind]
            image = numpy.zeros((GALLERY_SIZE,GALLERY_SIZE))
            tmp_img = self['image'] \
                             ['channel'] \
                             [0, time_idx, 0,
                              max(0, cen1[1]-GALLERY_SIZE/2):min(1040,cen1[1]+GALLERY_SIZE/2), 
                              max(0, cen1[0]-GALLERY_SIZE/2):min(1389,cen1[0]+GALLERY_SIZE/2)]
            image[:tmp_img.shape[0],:tmp_img.shape[1]] = tmp_img
            image_list.append(image)
        return numpy.concatenate(image_list, axis=1)
    
    def get_class_label(self, index):
        if not isinstance(index, list):
            index = [index]
        return self.get_class_prediction()['label_idx'][index] + 1
          
    def get_class_color(self, class_labels, object):
        class_mapping = self.definitions.class_definition(object)
        return [class_mapping['color'][col-1] for col in class_labels]
    
    def get_class_name(self, class_labels, object):
        class_mapping = self.definitions.class_definition(object)
        return [class_mapping['name'][col-1] for col in class_labels]
    
    def _get_object_table(self, object):
        return self['object'][object].value
    
    def get_events(self):
        dset_event = self._get_object_table('event')
        events = []
        for event_id in range(1,dset_event['obj_id'].max()):
            idx = numpy.where(dset_event['obj_id'] == event_id)
            idx1 = dset_event[idx]['idx1']
            idx2 = dset_event[idx]['idx2']
            
            event_list = []
            for p1, _ in zip(idx1, idx2):
                if p1 in event_list:
                    # branch ends
                    break
                else:
                    event_list.append(p1)
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
    def _get_object_table(self, *args, **kwargs):
        return super(CH5CachedPosition, self)._get_object_table(*args, **kwargs)
    
    @memoize
    def get_tracking(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_tracking(*args, **kwargs)
    
    @memoize
    def get_class_prediction(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_class_prediction(*args, **kwargs)

    @memoize
    def get_gallery_image(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_gallery_image(*args, **kwargs)
    
    @memoize
    def get_class_name(self, class_labels, object='primary__primary'):
        return super(CH5CachedPosition, self).get_class_name(class_labels, object)
    
    @memoize
    def get_class_color(self, class_labels, object='primary__primary'):
        return super(CH5CachedPosition, self).get_class_color(class_labels, object)

class CH5File(object):
    POSITION_CLS = CH5CachedPosition
    def __init__(self, filename):
        self._file_handle = h5py.File(filename, 'r')
        self.plate = self._get_group_members('/sample/0/plate/')[0]
        self.wells = self._get_group_members('/sample/0/plate/%s/experiment/' % self.plate)
        self.positions = collections.OrderedDict()
        for w in sorted(self.wells):
            self.positions[w] = self._get_group_members('/sample/0/plate/%s/experiment/%s/position/' % (self.plate, w))
                                                        
        print 'Plate', self.plate
        print 'Positions', self.positions
        self._position_group = {}
        for w, pos_list in self.positions.items():
            for p in pos_list:
                print '/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)
                self._position_group[(w,p)] = CH5File.POSITION_CLS(self.plate, w, p, self._file_handle['/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)], self)
        self.current_pos = self._position_group.values()[0]
        
    def get_position(self, well, pos):
        return self._position_group[(well, pos)]
    
    def set_current_pos(self, well, pos):
        self.current_pos = self.get_position(well, pos)
        
    def _get_group_members(self, path):
        return map(str, self._file_handle[path].keys())
    
    @memoize
    def class_definition(self, object):
        return self._file_handle['/definition/feature/%s/object_classification/class_labels' % object].value
    
    def close(self):
        self._file_handle.close()    
    
    
import unittest
class CH5TestBase(unittest.TestCase):
    pass

class TestCH5Basic(CH5TestBase): 
    def setUp(self):
        self.fh = CH5File('0038-cs.h5')
        self.well_str = '0'
        self.pos_str = self.fh.positions[self.well_str][0]
        
    def testGallery(self):
        
        a1 = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(1)
        b1 = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(2)
        a2 = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(1)
        
        self.assertTrue(a1.shape == (GALLERY_SIZE, GALLERY_SIZE))
        self.assertTrue(b1.shape == (GALLERY_SIZE, GALLERY_SIZE))
        self.assertTrue(numpy.all(a1 == a2))
        self.assertFalse(numpy.all(a1 == b1))
        
    def testGallery2(self):
        event = self.fh.get_position(self.well_str, self.pos_str).track_first(5)
        a1 = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(tuple(event))
#        import vigra
#        vigra.impex.writeImage(a1.swapaxes(1,0), 'c:/Users/sommerc/Desktop/bla.png')
        
    def testGallery3(self):
        event = self.fh.get_position(self.well_str, self.pos_str).get_events()[42][0]
        tracks = self.fh.get_position(self.well_str, self.pos_str).track_all(event)
        w = numpy.array(map(len, tracks)).max()*GALLERY_SIZE
        img = numpy.zeros((GALLERY_SIZE * len(tracks), w), dtype=numpy.uint8)
        
        for k, t in enumerate(tracks):
            a = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(tuple(t))
            print a.shape
            img[k*GALLERY_SIZE:(k+1)*GALLERY_SIZE, 0:a.shape[1]] = a
#        import vigra
#        vigra.impex.writeImage(img.swapaxes(1,0), 'c:/Users/sommerc/Desktop/foo.png')
        
    def testGallery4(self):
        event = self.fh.get_position(self.well_str, self.pos_str).get_events()[42]
        a1 = self.fh.get_position(self.well_str, self.pos_str).get_gallery_image(tuple(event))
#        import vigra
#        vigra.impex.writeImage(a1.swapaxes(1,0), 'c:/Users/sommerc/Desktop/blub.png')   
              
    def testClassNames(self):
        for x in ['inter', 'pro', 'earlyana']:
            self.assertTrue(x in self.fh.get_position(self.well_str, self.pos_str).get_class_name((1,2,5)))
     
    def testClassColors(self):
        for x in ['#FF8000', '#D28DCE', '#FF0000']:
            self.assertTrue(x in self.fh.get_position(self.well_str, self.pos_str).get_class_color((3,4,8)))   
         
    def testEvents(self):
        self.assertTrue(len(self.fh.get_position(self.well_str, self.pos_str).get_events()) > 0)
        self.assertTrue(len(self.fh.get_position(self.well_str, self.pos_str).get_events()[0]) > 0)
        
    def testTrack(self):
        self.assertTrue(len(self.fh.get_position(self.well_str, self.pos_str).track_first(42)) > 0)
        
    def testTrackFirst(self):
        self.assertListEqual(self.fh.get_position(self.well_str, self.pos_str).track_first(42), 
                             self.fh.get_position(self.well_str, self.pos_str).track_all(42)[0])
        
    def testTrackLast(self):  
        self.assertListEqual(self.fh.get_position(self.well_str, self.pos_str).track_last(1111), 
                             self.fh.get_position(self.well_str, self.pos_str).track_all(1111)[-1])
        
    def tearDown(self):
        self.fh.close()

if __name__ == '__main__':
    unittest.main()