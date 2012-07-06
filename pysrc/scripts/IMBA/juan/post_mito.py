import numpy
import matplotlib.pyplot as mpl
import h5py
import collections

GALLERY_SIZE = 50

class CecogHDF(object):
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
                self._position_group[(w,p)] = self._file_handle['/sample/0/plate/%s/experiment/%s/position/%s' % (self.plate, w, p)]
        self.current_pos = self._position_group.values()[0]
        self._cache = {}
        
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
        result = []
        for ind in index:
            result.append(self.current_pos['feature'] 
                                          ['primary__primary']
                                          ['object_classification']
                                          ['prediction'][ind][0] + 1)
        if len(result) == 1:
            return result
        else:
            return result
        
    def get_class_color(self, class_labels, object='primary__primary'):
        class_mapping = self._file_handle['/definition/feature/%s/object_classification/class_label' % object].value
        return [class_mapping['color'][col-1] for col in class_labels]
    
    def get_class_name(self, class_labels, object='primary__primary'):
        class_mapping = self._file_handle['/definition/feature/%s/object_classification/class_label' % object].value
        return [class_mapping['name'][col-1] for col in class_labels]
        
    def get_events(self):
        dset_event = ceh5.current_pos['object']['event'].value
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
        dset_tracking = ceh5.current_pos['object']['tracking'].value

            
        idx = start_idx
        while True:
            next_p_idx = numpy.where(dset_tracking['obj_idx1']==idx)[0]
            if len(next_p_idx) == 0:
                break
            idx = dset_tracking['obj_idx2'][next_p_idx[0]]
            idx_list.append(idx)
        return idx_list


if __name__ == "__main__":
    filename = 'V:/JuanPabloFededa/Analysis/001658/hdf5/_all_positions.h5'
    ceh5 = CecogHDF(filename)
    post_tracks = {}
    for well, pos_list in ceh5.positions.items():
        pos = pos_list[0]
        ceh5.set_current_pos(well, pos)
        events = ceh5.get_events()
        post_tracks[(well, pos)] = []
        print well, '+'*12
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
            print class_labels_str
            
#            if '7' in class_labels_str:
#                fig = mpl.figure(figsize=(20,10))
#                mpl.imshow(track_image, cmap=mpl.gray())
#                mpl.show()
    
    
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
    for (well, pos), tracks in post_tracks.items():
        names.append('%s_%s' % (well, pos))
        m, e = compute_class_freq(tracks, 8)
        apo_means.append(m)
        apo_yerr.append(e)
        m, e = compute_class_freq(tracks, 1)
        inter_means.append(m)
        inter_yerr.append(e)
        m, e = compute_class_freq(tracks, 9)
        multi_means.append(m)
        multi_yerr.append(e)
        
        
    
    width = 0.25
    ax = mpl.gca()
    ind = numpy.arange(len(apo_means))
    
    bp = mpl.bar(ind, inter_means, width, yerr=inter_yerr, color='g', ecolor='k')
    bp = mpl.bar(ind+width, multi_means, width, yerr=multi_yerr, color='b', ecolor='k')
    bp = mpl.bar(ind+2*width, apo_means, width, yerr=apo_yerr, color='r', ecolor='k')
    
    ax.set_xticks(ind+(3.0*width)/2)
    ax.set_xticklabels(names, rotation='vertical')
    ax.set_title('Post-mitotic apo frequencies')
    mpl.show()
    
    ceh5.close()
            

    
    