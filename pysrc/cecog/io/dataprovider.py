"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2011 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""
__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import os
import zlib
import base64

#-------------------------------------------------------------------------------
# extension module imports:
#
import h5py, \
       numpy, \
       vigra, \
       random

import time as timing

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#

MAX_OBJECT_ITEM_CACHE_SIZE = 3

#-------------------------------------------------------------------------------
# functions:
#


#-------------------------------------------------------------------------------
# classes:
#
import threading, Queue
class InputOutputThread(threading.Thread):
    inQueue = Queue.Queue()
    outDict = {}
    dictLock = threading.Lock()
    
    def __init__(self, target):
        threading.Thread.__init__(self) 
        self.target = target
        
    def run(self):
        temp = self.inQueue.get()
        print 'started for positon', temp[0],
        res = self.target(*temp[1:])
        print 'done'
        self.outDict[temp[0]] = res
        self.inQueue.task_done()
        


class _DataProvider(object):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None

    def __init__(self, hf_group, parent=None):
        self._hf_group = hf_group
        self._children = {}
        self._parent = parent
        
        self._init()
        
        if self.CHILDREN_GROUP_NAME is not None:
            for name, group in self._hf_group[self.CHILDREN_GROUP_NAME].iteritems():
                self._children[name] = self.CHILDREN_PROVIDER_CLASS(group, parent=self)
                
    def _init(self):
        pass
        
    def __getitem__(self, name):
        return self._children[name]

    def __iter__(self):
        return self._children.__iter__()

    def keys(self):
        return self._children.keys()
    
    def get_definition(self, key):
        """
        returns: the first found value for a given 'defintion_key', by searching up the tree.
                 if 'key' can not be found it reaises a KeyError
        """
        # check local definition first
        # FIXME: The global at the root is a special case. 
        if 'definition' in self._hf_group:
            if key in self._hf_group['definition']:
                return self._hf_group['definition'][key]
            
        # check parent
        if self._parent._hf_group.name == '/':
            # we are root already.
            
            # definition is manditory the root node
            if key in self._parent._hf_group['definition']:
                return self._parent._hf_group['definition'][key]
            else:
                raise KeyError('get_definition(): definition for key "%s" not be found in the tree!' % (key,))
        
        else:
            # recurse one level up
            return self._parent.get_definition(key)
        
    def has_definition(self, key):
        has_key = False
        try:
            self.get_definition(key)
            has_key = True
        except KeyError:
            pass
        return has_key
            
                
    def get_object_definition(self, name):
        objects_definition = self.get_definition('object')
        for object_def in objects_definition:
            if object_def[0] == name:
                break
        else:
            raise ValueError('No object found to given object name %s' % name)
        return object_def
    
    def get_object_relation(self, name):
        return self.get_object_definition(name)[1] # relation name
    
    def close(self):
        self._hf_group.close()
        
class Position(_DataProvider):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None
    
    def read_image_data(self):
        if not hasattr(self, '_hf_group_np_copy'):
            tic = timing.time()
            self._hf_group_np_copy = self._hf_group['image']['channel']
            print '  decompressing image data', timing.time() - tic
            
    
    def __init__(self, hf_group, parent=None):
        super(Position, self).__init__(hf_group, parent)
        
    def _init(self):
        print ' Position: *** reading ', self._hf_group.name
        self.plate = self._parent._parent
        self._read_objects()
        self._read_relations()
        
    def _read_objects(self):
        self.objects = {}
        self.sub_objects = {}
        for object_def_row in self.get_definition('object'):
            object_name = object_def_row[0]
            object_sub_rel = object_def_row[1]
            object_type = object_def_row[2]
            
            self.sub_objects[object_name] = None
            for rel_row in self.get_definition('relation'):
                if rel_row[0] == object_sub_rel:
                    self.sub_objects[object_name] = rel_row[1]
                    break
            
            if object_type == 'object':
                print ' Position: caching object', object_name
                self.objects[object_name] = \
                    {'cache' : self.init_objects(object_name), 
                     'sub_relation' : object_sub_rel }
            
                    
    def _read_relations(self):
        self.relation_compund = {}
        self.relation_cross = {}
        for relation_def_row in self.get_definition('relation'):
            rel_name = relation_def_row[0]
            obj_1 = relation_def_row[1]
            obj_2 = relation_def_row[2]
            if obj_1 in self.objects or obj_1 in self.plate.regions:
                if obj_1 == obj_2:
                    print ' Position: found compound relation for', obj_1, ' : ', rel_name
                    self.relation_compund.setdefault(obj_1,[]).append({'relation_name': rel_name,
                                                  'to': obj_2,
                                                  'cache': self._hf_group['relation'][rel_name].value})
                else:
                    print ' Position: found cross relation for', obj_1, ' : ', rel_name
                    self.relation_cross.setdefault(obj_1,[]).append({'relation_name': rel_name,
                                                  'to': obj_2,
                                                  'cache': self._hf_group['relation'][rel_name].value})     


    def init_objects(self, object_name):
        return Objects(object_name, self)
    
    def get_objects(self, object_name):
        return self.objects[object_name]['cache']
    
    def get_sorted_objects(self, object_name, criteria, *critera_options):
        if criteria == 'state_periods':
            objects = self.objects[object_name]['cache']
            
            result = []
            for obj in objects:
                state_periods = {}
                pc_old = 0
                cnt = 0
                for i in obj.children():
                    pc = i.predicted_class
                    if pc_old == pc: 
                        cnt += 1
                    else:
                        if cnt > state_periods.setdefault(pc_old, 0):
                            state_periods[pc_old] = cnt   
                        cnt = 0
                    pc_old = pc 
                if cnt > state_periods.setdefault(pc_old, 0):
                    state_periods[pc_old] = cnt
                result.append(sum([state_periods.setdefault(j,0) for j in critera_options]))
                
            tmp = zip(result, objects)
            tmp.sort()
            
            result = []
            for obj in tmp:
                result.append(obj[-1])
                
            return result
                
        else:
            raise NotImplementedError('The sort criteria %s is not implemented', criteria)
                
            
            
            
    
    def get_objects_type(self, object_name):
        return self.objects[object_name]['type']
    
    def get_object_group(self, name):
        return self._hf_group['object'][name]     
    
    def get_relation(self, relation_name):
        releations = self.get_definition('relation')
        
        releation_name_found = False
        for rel in releations:
            if rel[0] == relation_name:
                releation_name_found = True
                from_object_name = rel[1]
                to_object_name = rel[2]
                
        if not releation_name_found:
            raise KeyError('get_relation() releation "%s" not found in definition.' % relation_name)
        
        if relation_name not in self._hf_group['relation']:
            raise KeyError('get_relation() no entries found for relation "%s".' % relation_name)
        
        h5_relation_group = self._hf_group['relation'][relation_name]
        
        return Relation(relation_name, h5_relation_group, (from_object_name, to_object_name))
                
        
    
        
        
class Experiment(_DataProvider):

    CHILDREN_GROUP_NAME = 'position'
    CHILDREN_PROVIDER_CLASS = Position


class Plate(_DataProvider):

    CHILDREN_GROUP_NAME = 'experiment'
    CHILDREN_PROVIDER_CLASS = Experiment
    
    def __init__(self, hf_group, parent=None):
        super(Plate, self).__init__(hf_group, parent)
    
    def _init(self):
        self._read_channel_region_info()
        self._read_feature_set_info()
        self._read_classification_info()
        
    def _read_channel_region_info(self):
        self.regions = {}
        channel_info = self.get_definition('channel')
        for object_def_row in self.get_definition('object'):
            object_name = object_def_row[0]
            object_type = object_def_row[2]
                    
            if object_type == 'region':
                print 'Plate: reading region objects', object_name
                for region_row in self.get_definition('region'):
                    if region_row[0] == object_name:
                        channel_idx = region_row[1]
                        self.regions[object_name] = \
                          {'channel_idx' : channel_idx, 
                           'channel_name' : channel_info[channel_idx][0],
                           'description' : channel_info[channel_idx][1],
                           'is_phydical' : channel_info[channel_idx][2],
                           'voxel_size' : channel_info[channel_idx][3]}
                        break
        
    def _read_feature_set_info(self):
        self.object_feature = {}
        last_feature_for_object = 'ham'
        feature_group = self.get_definition('feature')
        for feature_row in self.get_definition('feature'):
            feature_for_object = feature_row[2]
            if last_feature_for_object != feature_for_object:
                #feature_uses_channels = feature_row[4][:feature_row[3]]
                print 'Plate: found features for object', feature_for_object
                for f in feature_group[self.get_definition('feature_set')[feature_for_object]]:
                    self.object_feature.setdefault(feature_for_object, []).append(f[0])
                last_feature_for_object = feature_for_object
        
    def _read_classification_info(self):
        self.object_classifier = {}
        self.object_classifier_index = {}
        
        if not self.has_definition('classifier'):
            return
        
        for classifier_idx, classifier_row in enumerate(self.get_definition('classifier')):
            object_name = self.get_definition('feature')[self.get_definition('feature_set')[classifier_row[3]][0]][2]
            print 'Plate: found classifier for object', object_name, 'with schema: ', classifier_row[4]
            self.object_classifier[(object_name, classifier_idx)] = \
                    {'name' : classifier_row[0],
                     'method' : classifier_row[1],
                     'version' : classifier_row[2],
                     'feature_set' : classifier_row[3],
                     'schema' : self.get_definition('classification')[classifier_row[4]],
                     'parameter' : classifier_row[6],
                     'description' : classifier_row[7],
                     }
            self.object_classifier_index[object_name] = classifier_idx


class Sample(_DataProvider):

    CHILDREN_GROUP_NAME = 'plate'
    CHILDREN_PROVIDER_CLASS = Plate


class Data(_DataProvider):

    CHILDREN_GROUP_NAME = 'sample'
    CHILDREN_PROVIDER_CLASS = Sample
             
class File(object):
    def __init__(self, filename):
        self.filename = filename
        self._data = Data(h5py.File(filename, 'r'))
        
    def __getitem__(self, spepos):
        s, p, e, pos = spepos
        return self._data[s][p][e][pos]
    
    def clearObjectItemCache(self):
        for pos_key in self.positions:
            for object_name in self[pos_key].objects:
                self[pos_key].get_objects(object_name)._object_item_cache = {}
    
    def close(self):
        self._data.close()
    
    @property
    def samples(self):
        return [s for s in self._data]
    
    @property
    def plates(self):
        return [(s, p) for s in self.samples for p in self._data[s]]
    
    @property
    def experiment(self):
        return [(s, p, e) for (s, p) in self.plates for e in self._data[s][p]]
    
    @property
    def positions(self):
        return [(s, p, e, pos) for (s, p, e) in self.experiment for pos in self._data[s][p][e]]
                 
class Relation(object):
    def __init__(self, relation_name, h5_table, from_to_object_names):
        self.from_object, self.to_object = from_to_object_names
        self.name = relation_name
        self.h5_table = h5_table
        
    def get_cache(self):
        return self.h5_table.value.view(numpy.uint32).reshape(len(self.h5_table), -1)
    
class ObjectItemBase(object):
    def __init__(self, id, parent):
        self.id = id
        self.parent = parent
        self.name = parent.name
        self.compute_features()
        
    def compute_features(self):
        pass
        
    def get_position(self):
        return self.parent.position
    
    def get_plate(self):
        return self.parent.position.plate
    
    def get_child_objects_type(self):
        return self.parent.get_object_type_of_children()
        
    @property
    def idx(self):
        return self.id - 1
    
    def is_terminal(self):
        return isinstance(self, TerminalObjectItem)
    
    def children(self):
        if not hasattr(self, '_children'):
            self._children = self.get_children_paths()[0]
        return self._children

    def _get_children_nodes(self):
        if not hasattr(self, '_children_nodes'):
            child_entries = self.parent.object_np_cache['child_ids'][self.id]
            if len(child_entries) == 0:
                return []
            result = numpy.zeros(child_entries.shape[0]+1, dtype=numpy.uint32)
            result[0] = child_entries[0,0]
            result[1:] = child_entries[:,2]
            self._children_nodes = map(lambda id: self.get_child_objects_type()(id, self.sub_objects()), result)
        return self._children_nodes
            
    
    def get_siblings(self):
        if self.name in self.get_position().relation_cross:
            res = {}
            for sibling in self.get_position().relation_cross[self.name]:
                sibling_object_name = sibling['to']
                sibling_object_relation = sibling['cache']
                res[sibling_object_name] = self.get_position().get_objects(sibling_object_name).get(sibling_object_relation[self.idx][2])
            return res[sibling_object_name]
        
        
    def _find_edges(self, id, expansion=None, max_length=5, reverse=False):
        if expansion is None:
            expansion = []
        ind1 = 0
        ind2 = 2
        if reverse:
            ind1, ind2 = ind2, ind1
        tmp = numpy.where(self.parent.object_np_cache['relation'][:, ind1] == id)[0]
        if len(tmp) > 0 and max_length > 0:
            next_id = self.parent.object_np_cache['relation'][tmp[0], ind2]
            expansion.append(next_id)
            return self._find_edges(next_id, expansion, max_length-1, reverse)
        else:
            if reverse:
                expansion.reverse()
            return expansion
        
    def get_children_paths(self):
        child_list = self._get_children_nodes()
        child_id_list = [x.id for x in child_list]
        if len(child_id_list) == 0:
            return [None]
        else:
            head_id = child_list[0].id
            
            def all_paths_of_tree(id):
                found_ids = numpy.where(self.parent.object_np_cache['relation'][:, 0] == id)[0]
                out_all_ids = [self.parent.object_np_cache['relation'][found_id, 2] for found_id in found_ids]
                out_ids = [out_id for out_id in out_all_ids if out_id in child_id_list]
                
                if len(out_ids) == 0:
                    return [[id]]
                else:
                    all_paths_ = []
                    for out_id in out_ids:
                        for path_ in all_paths_of_tree(out_id):
                            all_paths_.append([id] + path_)
    
                    return all_paths_ 
                
            res = all_paths_of_tree(head_id)
            for i, r in enumerate(res):
                res[i] = [self.get_child_objects_type()(id, self.sub_objects()) for id in r]
            
            return res
        
    def get_children_expansion(self, max_length=5):
        child_list = self.get_children_paths()[0]
        front_id = child_list[0].id
        back_id = child_list[-1].id
        
        succs = self._find_edges(back_id, max_length=max_length)
        pred  = self._find_edges(front_id, max_length=max_length, reverse=True)
        
        result = pred + [x.id for x in child_list] + succs
        
        return map(lambda id: self.get_child_objects_type()(id, self.sub_objects()), result)
                
    def sub_objects(self):
        return self.get_position().get_objects(self.get_position().sub_objects[self.name])
    
    def __getitem__(self, key):
        return self._features[key]
    
    def __setitem__(self, key, value):
        if not hasattr(self, '_features'):
            self._features = {}
        self._features[key] = value

class ObjectItem(ObjectItemBase):
    def __init__(self, obj_id, parent):
        ObjectItemBase.__init__(self, obj_id, parent)
    
class TerminalObjectItem(ObjectItemBase):
    def __init__(self, obj_id, object_cache):
        ObjectItemBase.__init__(self, obj_id, object_cache)
        
    def _get_children_nodes(self):
        raise RuntimeError('Terminal objects have no childs')
    
    @property
    def local_id(self):
        return self.parent.object_np_cache['child_ids'][self.id][0][0]
    @property
    def _local_idx(self):
        return self.parent.object_np_cache['child_ids'][self.id][0][1:3] # time, idx

class Objects(object):
    HDF5_OBJECT_EDGE_NAME = 'edge'
    HDF5_OBJECT_ID_NAME = 'id'
    
    def __init__(self, name, position):
        self.name = name
        self.position = position        
        self._h5_object_group = position.get_object_group(name)
        
        self.object_np_cache = {}  
        self._object_item_cache = {}  
        
        self._relation_name = position.get_object_relation(name)
        self.relation = position.get_relation(self._relation_name)
        self.object_np_cache['relation'] = self.relation.get_cache()
        
        if self._h5_object_group[self.HDF5_OBJECT_EDGE_NAME].shape[0] == 0:
            edge_table = numpy.zeros((0,0), dtype=numpy.uint32)
            nr_cols = 0
        else:
            edge_table = self._h5_object_group[self.HDF5_OBJECT_EDGE_NAME].value
            nr_cols = -1 # determined by numpy
        self.object_np_cache['edges'] = edge_table.view((numpy.uint32, len(edge_table.dtype.names)))
                                 
        if self._h5_object_group[self.HDF5_OBJECT_ID_NAME].shape[0] == 0:
            id_refs_table = numpy.zeros((0,0), dtype=numpy.uint32)
            nr_cols = 0
        else:
            id_refs_table = self._h5_object_group[self.HDF5_OBJECT_ID_NAME].value
            nr_cols = 2
        self.object_np_cache['id_edge_refs']  = id_refs_table.view((numpy.uint32, len(id_refs_table.dtype.names)))
                                                        
        self.object_np_cache['child_ids'] = {}
        for x in self.object_np_cache['id_edge_refs']:
            self.object_np_cache['child_ids'][x[0]] = self.object_np_cache['relation'][self.object_np_cache['edges'][x[1]:x[2], 1]]
            

        t = len(self.position._hf_group['time'])
        
        if self.is_terminal():
            c = self.position.plate.regions[self.position.sub_objects[self.name]]['channel_idx']
            self.object_np_cache['terminals'] = numpy.zeros((t), dtype=object)
            for t, tg in self.position._hf_group['time'].iteritems():
                t = int(t)
                region = tg['region'][str(c)]
                self.object_np_cache['terminals'][t] = {'object': region['object'].value, \
                                                              'crack_contours' : region['crack_contour'].value}
            
            
    def is_terminal(self):
        return self.position.sub_objects[self.name] in self.position.plate.regions
        
    @property
    def ids(self):
        return self.object_np_cache['id_edge_refs'][:,0] if self.object_np_cache['id_edge_refs'].shape[1] > 0 else [] 
    
    def __len__(self):
        return len(self.ids)
          
    def get_object_type(self):
        ItemType = ObjectItem
        if self.is_terminal():
            ItemType = TerminalObjectItem
        return ItemType
    
    def get_object_type_of_children(self):
        ItemType = ObjectItem
        if self.position.sub_objects[self.position.sub_objects[self.name]] in self.position.plate.regions:
            ItemType = TerminalObjectItem
        return ItemType
    
    def _shrink_object_item_cache(self):
        for cnt, obj_id_ in enumerate(self._object_item_cache.keys()):
            cache_size =len(self._object_item_cache.keys())
            if cnt >= cache_size - MAX_OBJECT_ITEM_CACHE_SIZE:
                break
            self._object_item_cache[obj_id_] = None
            del self._object_item_cache[obj_id_]
            cache_size -= 1
    
    def get(self, obj_id):
        if obj_id not in self._object_item_cache:
            ItemType = self.get_object_type()
            self._shrink_object_item_cache()
                       
            self._object_item_cache[obj_id] = ItemType(obj_id, self)
        return self._object_item_cache[obj_id]
            
    def __iter__(self, max_count=None):
        for id in self.ids:
            yield self.get(id)    
            
            
    def iter(self, max_count = 100):
        for id in self.ids[: (min(max_count, len(self)))]:
            yield self.get(id)
            
    def iter_random(self, max_count = 100):
        for id in random.sample(self.ids, min(max_count, len(self))):
            yield self.get(id)
    
    def get_sub_objects(self):
        if self.next_object_level:
            self.sub_objects = self.parent_positon_provider.get_objects(self.next_object_level)
            return self.sub_objects
        else:
            raise RuntimeError('get_sub_objects() No sub objects available for objects of name %s' % self.name)







        
#class TrajectoryFeatureMedianIntensity(TrajectoryFeatureBase):
#    name = 'Madian intensity'
#    
#    def compute(self, trajectory_seq):
#        value = []
#        for t in trajectory_seq:
#            value.append(numpy.median(t.data))
#        value = numpy.median(value)
#        return value
    
#class TrajectoryFeatureMeanArea(TrajectoryFeatureBase):
#    name = 'Mean area'
#    
#    def compute(self, trajectory_seq):
#        # Using the formula given in
#        # http://en.wikipedia.org/wiki/Polygon#Area_and_centroid
#        values = []
#        for t in trajectory_seq:
#            y_last, x_last = t.crack_contour[-1,:]
#            value = 0
#            for y, x in t.crack_contour:
#                value += x_last * y - x * y_last
#                x_last , y_last = x, y
#            value /= 2
#            values.append(value)
#        value = numpy.mean(values)
#
#        return value
#    
#class TrajectoryFeatureAreaVariance(TrajectoryFeatureBase):
#    name = 'Area variance'
#    
#    def compute(self, trajectory_seq):
#        # Using the formula given in
#        # http://en.wikipedia.org/wiki/Polygon#Area_and_centroid
#        values = []
#        for t in trajectory_seq:
#            y_last, x_last = t.crack_contour[-1,:]
#            value = 0
#            for y, x in t.crack_contour:
#                value += x_last * y - x * y_last
#                x_last , y_last = x, y
#            value /= 2
#            values.append(value)
#        value = numpy.std(values)
#
#        return value


            
#-------------------------------------------------------------------------------
# main:
#

if __name__ == '__main__':
    tic = timing.time()
    try:
        t = File('/Users/miheld/data/Analysis/H2bTub_20x_hdf5_test1/dump/0037.hdf5')
    except:
        t = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels_nozip/dump_save/two_positions.hdf5')
        
    print 'init time for position  == %5.3f msec' % (timing.time() - tic)
    
    object_name = 'event'
    
    
    position = t[t.positions[0]]
    for object_name in ['event']:
        pp = position.get_objects(object_name)
        for id in pp.ids:
            print id, '-->', pp.get(id).get_children_expansion()
        
