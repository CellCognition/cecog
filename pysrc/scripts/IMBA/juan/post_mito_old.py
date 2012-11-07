import numpy
import matplotlib.pyplot as mpl
import h5py
import collections
import functools
import time
import cProfile


GALLERY_SIZE = 50
    
  
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
    def __init__(self, plate, well, pos, grp_pos):
        self.plate = plate
        self.well = well
        self.pos = pos
        self.grp_pos = grp_pos
        
    def __getitem__(self, key):
        return self.grp_pos[key]
    
    def get_tracking(self):
        return self.grp_pos['object']['tracking'].value
    
    def get_class_prediction(self):
        return self['feature'] \
                   ['primary__primary'] \
                   ['object_classification'] \
                   ['prediction'].value

class CH5CachedPosition(CH5Position):
    def __init__(self, *args, **kwargs):
        super(CH5CachedPosition, self).__init__(*args, **kwargs)
    
    @memoize
    def get_tracking(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_tracking(*args, **kwargs)
    
    @memoize
    def get_class_prediction(self, *args, **kwargs):
        return super(CH5CachedPosition, self).get_class_prediction(*args, **kwargs)

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
                self._position_group[(w,p)] = CH5File.POSITION_CLS(self.plate, w, p, self._file_handle['/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)])
        self.current_pos = self._position_group.values()[0]
        
    def get_position(self, well, pos):
        return self._position_group[(well, pos)]
    
    def set_current_pos(self, well, pos):
        self.current_pos = self.get_position(well, pos)
        
    def _get_group_members(self, path):
        return map(str, self._file_handle[path].keys())
    
    def close(self):
        self._file_handle.close()

    def get_gallery_image(self, index, object='primary__primary'):
        if not isinstance(index, list):
            index = [index]
        image_list = []
        for ind in index:
            grp_pos = self.current_pos
            time_idx = grp_pos['object'][object][ind]['time_idx']
            cen1 = grp_pos['feature'][object]['center'][ind]
            image = numpy.zeros((GALLERY_SIZE,GALLERY_SIZE))
            tmp_img = grp_pos['image'] \
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
        return self.current_pos.get_class_prediction()['label_idx'][index] + 1
          
    def get_class_color(self, class_labels, object='primary__primary'):
        class_mapping = self._file_handle['/definition/feature/%s/object_classification/class_label' % object].value
        return [class_mapping['color'][col-1] for col in class_labels]
    
    def get_class_name(self, class_labels, object='primary__primary'):
        class_mapping = self._file_handle['/definition/feature/%s/object_classification/class_label' % object].value
        return [class_mapping['name'][col-1] for col in class_labels]
        
    def get_events(self):
        dset_event = self.current_pos['object']['event'].value
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
    
    def track_first(self, start_idx):
        ### follow last cell
        idx_list = []
        dset_tracking = self.current_pos.get_tracking()

        idx = start_idx
        while True:
            next_p_idx = (dset_tracking['obj_idx1']==idx).nonzero()[0]
            if len(next_p_idx) == 0:
                break
            idx = dset_tracking['obj_idx2'][next_p_idx[0]]
            idx_list.append(idx)
        return idx_list
    



    
def do_post_mito():
    start = time.time()
    #filename = r'C:\Users\sommerc\R\biohdf\0038-cs.h5'
    filename = r'V:\JuanPabloFededa\Analysis\001658\hdf5\_all_positions.h5'
    ceh5 = CH5File(filename)
    fh_res = open(r'V:\JuanPabloFededa\Analysis\001658\post_mito_class_labels.txt', 'w')
    post_tracks = {}
    for well, pos_list in ceh5.positions.items():
        pos = pos_list[0]
        ceh5.set_current_pos(well, pos)
        events = ceh5.get_events()
        post_tracks[(well, pos)] = []
        fh_res.write('[%s]\n' % well)
        print well
        cnt = 0
        for event in events:
            cnt += 1
            start_idx = event[-1]
            track = ceh5.track_first(start_idx)
            class_labels = ceh5.get_class_label(track)
            if len(class_labels) == 0:
                continue
            class_labels_str = ''.join(map(str, class_labels))
            post_tracks[(well, pos)].append(class_labels)
            fh_res.write('%s\n' % class_labels_str)
            print cnt, class_labels_str
    fh_res.close()
    
    ceh5.close()
    print (time.time() - start)
    
def plot_post_mito():
    fh_res = open('post_mito_class_labels.txt', 'r')
    data_dct = {}
    well = ''
    print 'reading file',
    for line in fh_res:
        if line.startswith('['):
            well = line[1:4]
            data_dct[well] = []
        else:
            data_dct[well].append(map(int, [line[i:i+1] for i in range(len(line)-1)]))
            
    fh_res.close()
    print 'done'
    def compute_class_freq(tracks_, class_label_):
        data = []
        for t in tracks_:
            apo_freq = (numpy.array(t) == class_label_).sum() / float(len(t))
            data.append(apo_freq)
        return numpy.array(data).mean(), numpy.array(data).std()
    
    apo_means = []
    apo_yerr = []
    inter_means = []
    inter_yerr = []
    multi_means = []
    multi_yerr = []
    
    names = []
    for well in sorted(data_dct):
        tracks = data_dct[well]
        names.append('%s' % well)
        m, e = compute_class_freq(tracks, 8)
        apo_means.append(m)
        apo_yerr.append(e)
        m, e = compute_class_freq(tracks, 1)
        inter_means.append(m)
        inter_yerr.append(e)
        m, e = compute_class_freq(tracks, 9)
        multi_means.append(m)
        multi_yerr.append(e)
        
    width = 0.2
    fig = mpl.figure(figsize=(30,10))
    ax = mpl.gca()
    ind = numpy.arange(len(apo_means))
    
    bp = mpl.bar(ind, inter_means, width, yerr=inter_yerr, color='g', ecolor='k', label='inter')
    bp = mpl.bar(ind+width, multi_means, width, yerr=multi_yerr, color='b', ecolor='k',label='multi')
    bp = mpl.bar(ind+2*width, apo_means, width, yerr=apo_yerr, color='r', ecolor='k', label='apo')
    
    ax.set_xticks(ind+(3.0*width)/2)
    ax.set_xticklabels(names, rotation=45)
    ax.set_title('Post-mitotic apo frequencies')
    ax.set_ylim((0,1))
    mpl.legend(loc=1)
    mpl.show()
            

if __name__ == "__main__":
    plot_post_mito()
    
            
    