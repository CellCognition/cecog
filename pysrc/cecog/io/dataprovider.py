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
       networkx, \
       numpy, \
       vigra, \
       random

import matplotlib.pyplot as plt
import time as timing

#-------------------------------------------------------------------------------
# cecog imports:
#


#-------------------------------------------------------------------------------
# constants:
#
BOUNDING_BOX_SIZE = 50

#-------------------------------------------------------------------------------
# functions:
#

def print_timing(func):
    def wrapper(*arg):
        t1 = timing.time()
        res = func(*arg)
        t2 = timing.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper

#-------------------------------------------------------------------------------
# classes:
#

class TrackletItem(object):
    def __init__(self, time, data, crack_contour, predicted_class, size=BOUNDING_BOX_SIZE):
        self.time = time
        self.size = size
        self.data = data
        self.crack_contour = crack_contour.clip(0, BOUNDING_BOX_SIZE)
        self.predicted_class = predicted_class

class TrajectoryFeatureBase(object):
    def compute(self):
        raise NotImplementedError('TrajectoryFeatureBase.compute() has to be implemented by its subclass')

class TrajectoryFeatureMeanIntensity(TrajectoryFeatureBase):
    name = 'Mean intensity'
    
    def compute(self, trajectory_seq):
        value = 0
        for t in trajectory_seq:
            value += t.data.mean()
        value /= len(trajectory_seq)
        return value
        
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

trajectory_features = [tf() for tf in TrajectoryFeatureBase.__subclasses__()]


class _DataProvider(object):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None

    def __init__(self, hf_group, parent=None):
        self._hf_group = hf_group
        self._children = {}
        self._parent = parent
        if self.CHILDREN_GROUP_NAME is not None:
            for name, group in self._hf_group[self.CHILDREN_GROUP_NAME].iteritems():
                self._children[name] = self.CHILDREN_PROVIDER_CLASS(group, parent=self)
        #print self._children

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
    def __init__(self, hf_group, parent=None):
        super(Position, self).__init__(hf_group, parent)
        #self._hf_group_np_copy = self._hf_group['image']['channel'].value
        
        self.objects = {}
        self.sub_objects = {}
        self.regions= {}
        channel_info = self.get_definition('channel')
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
                print 'Position: caching object', object_name
                self.objects[object_name] = \
                    {'cache' : self.init_objects(object_name), 
                     'sub_relation' :object_sub_rel }
                    
            elif object_type == 'region':
                print 'Position: reading region objects', object_name
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
                    
        self.relation_compund = {}
        self.relation_cross = {}
        for relation_def_row in self.get_definition('relation'):
            rel_name = relation_def_row[0]
            obj_1 = relation_def_row[1]
            obj_2 = relation_def_row[2]
            if obj_1 in self.objects or obj_1 in self.regions:
                if obj_1 == obj_2:
                    print 'Position: found inter relation for', obj_1, ' : ', rel_name
                    self.relation_compund.setdefault(obj_1,[]).append({'relation_name': rel_name,
                                                  'to': obj_2})
                else:
                    print 'Position: found cross relation for', obj_1, ' : ', rel_name
                    self.relation_cross.setdefault(obj_1,[]).append({'relation_name': rel_name,
                                                  'to': obj_2})
                    
        self.object_feature = {}
        last_feature_for_object = 'ham'
        feature_group = self.get_definition('feature')
        for feature_row in self.get_definition('feature'):
            feature_for_object = feature_row[2]
            if last_feature_for_object != feature_for_object:
                #feature_uses_channels = feature_row[4][:feature_row[3]]
                print 'Position: found features for object', feature_for_object
                for f in feature_group[self.get_definition('feature_set')[feature_for_object]]:
                    self.object_feature.setdefault(feature_for_object, []).append(f[0])
                last_feature_for_object = feature_for_object
                
        self.object_classifier = {}
        for classifier_idx, classifier_row in enumerate(self.get_definition('classifier')):
            object_name = self.get_definition('feature')[self.get_definition('feature_set')[classifier_row[3]][0]][2]
            print 'Position: found classifier for object', object_name, 'with schema: ', classifier_row[4]
            self.object_classifier[(object_name, classifier_idx)] = \
                    {'name' : classifier_row[0],
                     'method' : classifier_row[1],
                     'version' : classifier_row[2],
                     'feature_set' : classifier_row[3],
                     'schema' : self.get_definition('classification')[classifier_row[4]],
                     'parameter' : classifier_row[6],
                     'description' : classifier_row[7],
                     }
        
    def _cache_terminal_objects(self):
        t = len(self._hf_group['time'])
        c = len(self._hf_group['time']['0']['region'])

        self._terminal_objects_np_cache = numpy.zeros((c, t), dtype=object)
        
        for t, tg in self._hf_group['time'].iteritems():
            t = int(t)
            for c, co in tg['region'].iteritems():
                c = int(c)
                self._terminal_objects_np_cache[c,t] = {'object': co['object'].value, \
                                                              'crack_contours' : co['crack_contour'].value}
    
    def init_objects(self, object_name):
        return Objects(object_name, self)
    
    def get_objects(self, object_name):
        return self.objects[object_name]['cache']
    
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
                
        
    def get_bounding_box(self, t, obj_idx, c=0):
        objects = self._terminal_objects_np_cache[c,t]['object']
        return (objects['upper_left'][obj_idx], objects['lower_right'][obj_idx])
    
    def get_image(self, t, obj_idx, c, bounding_box=None, min_bounding_box_size=BOUNDING_BOX_SIZE):
        if bounding_box is None:
            ul, lr = self.get_bounding_box(t, obj_idx, c)
        else:
            ul, lr = bounding_box
        
        offset_0 = (min_bounding_box_size - lr[0] + ul[0])
        offset_1 = (min_bounding_box_size - lr[1] + ul[1]) 
        
        ul[0] = max(0, ul[0] - offset_0/2 - cmp(offset_0%2,0) * offset_0 % 2) 
        ul[1] = max(0, ul[1] - offset_1/2 - cmp(offset_1%2,0) * offset_1 % 2)  
        
        lr[0] = min(self._hf_group['image']['channel'].shape[4], lr[0] + offset_0/2) 
        lr[1] = min(self._hf_group['image']['channel'].shape[3], lr[1] + offset_1/2) 
        
        bounding_box = (ul, lr)
        
        # TODO: get_iamge returns am image which might have a smaller shape than 
        #       the requested BOUNDING_BOX_SIZE, I dont see a chance to really
        #       fix it, without doing a copy...
        
        return self._hf_group_np_copy[c, t, 0, ul[1]:lr[1], ul[0]:lr[0]], bounding_box

    def get_crack_contours(self, t, obj_idx, c):  
        crack_contours_string = self._terminal_objects_np_cache[c,t]['crack_contours'][obj_idx]                               
        return numpy.asarray(zlib.decompress( \
                             base64.b64decode(crack_contours_string)).split(','), \
                            dtype=numpy.float32).reshape(-1,2)
        
    def get_object_data(self, t, obj_idx, c):
        bb = self.get_bounding_box(t, obj_idx, c)
        img, new_bb = self.get_image(t, obj_idx, c, bb)
        cc = self.get_crack_contours(t, obj_idx, c)
         
        cc[:,0] -= new_bb[0][0]
        cc[:,1] -= new_bb[0][1]
        
        return img, cc
    
    def get_additional_object_data(self, object_name, data_fied_name, index):
        return self._hf_group['object'][object_name][data_fied_name][str(index)]
        
        
class Experiment(_DataProvider):

    CHILDREN_GROUP_NAME = 'position'
    CHILDREN_PROVIDER_CLASS = Position


class Plate(_DataProvider):

    CHILDREN_GROUP_NAME = 'experiment'
    CHILDREN_PROVIDER_CLASS = Experiment


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
             
    def traverse_objects(self, object_name): 
        # loop over all positions
        for s, p, e, pos in self.positions:
            print 'In Sample %r plate %r, experiment %r and position %r' % (s, p, e, pos)
            position = self[s, p, e, pos]
            c = position.get_definition('region')['channel_idx'][0]
    
            events = position.get_objects(object_name) 
            
            primary_primary = events.get_sub_objects()
            
            for event_id, prim_prims_ids in events.iter_sub_objects():  
                res = []
                for prim_prim_id, reg_prim_id in primary_primary.iter_sub_objects(prim_prims_ids):
                    obj_id= primary_primary[prim_prim_id][0][0]
                    t = primary_primary[prim_prim_id][0][1]
                    obj_idx = primary_primary[prim_prim_id][0][2]
                    predicted_class = position.get_additional_object_data(primary_primary.name, 'classifier', 1) \
                                                ['prediction'][primary_primary.relation_idx[prim_prim_id][0]]
                    
                    image, crack_contour = position.get_object_data(t, obj_idx, c) 
                    tmp = TrackletItem(t, image, crack_contour, predicted_class)
                    res.append(tmp)
                print ''
                #res.sort(cmp=lambda x,y: cmp(x.time,y.time))
                yield res
                 
class Relation(object):
    def __init__(self, relation_name, h5_table, from_to_object_names):
        self.from_object, self.to_object = from_to_object_names
        self.name = relation_name
        self.h5_table = h5_table
        
    def get_cache(self):
        return self.h5_table.value.view(numpy.uint32).reshape(len(self.h5_table), -1)
    
class ObjectItemBase(object):
    def __init__(self, id, object_cache):
        self.id = id
        self.object_cache = object_cache
        
        self.in_obj_ids = []
        self.out_obj_ids = []
        
        self.children_ids = []
        
        self.sibling_obj_ids = []
    
    def is_terminal(self):
        return isinstance(self, TerminalObjectItem)
    
    def get_child_objects(self):
        child_entries = self.object_cache.object_np_cache['child_ids'][self.id]
        if len(child_entries) == 0:
            return None
        result = numpy.zeros(child_entries.shape[0]+1, dtype=numpy.uint32)
        result[0] = child_entries[0,0]
        result[1:] = child_entries[:,2]
        return map(lambda id: self.object_cache.get_object_type_of_children()(id, self.object_cache), result)
            
    
    def get_sibling_objects(self, sibling_name):
        for sibling_rel in self.object_cache.position.relation_cross:
            if sibling_name in sibling_rel['relation_name']:
                sibling_id = self.object_cache.position.h5_group['relation'][sibling_rel['relation_name']][self.id-1][2]
                return self.object_cache.get_object_type()(sibling_id, self.object_cache)
                

class ObjectItem(ObjectItemBase):
    def __init__(self, obj_id, object_cache):
        ObjectItemBase.__init__(self, obj_id, object_cache)
       
    def get_additional_data(self):
        # helper for subclass
        pass
    def get_children(self):
        # gereric
        pass
    def get_children_expansion(self):
        # gereric
        pass
    def get_siblings(self):
        # gereric
        pass
    def get_data(self):
        #abstract
        pass
    def get_display_settings(self):
        #abstract
        pass
    
class TerminalObjectItem(ObjectItemBase):
    def __init__(self, obj_id, object_cache):
        ObjectItemBase.__init__(self, obj_id, object_cache)
    
    def get_child_objects(self):
        raise RuntimeError('Terminal objects have no childs')
      

class Objects(object):
    HDF5_OBJECT_EDGE_NAME = 'edge'
    HDF5_OBJECT_ID_NAME = 'id'
    
    def __init__(self, name, position):
        self.name = name
        self.position = position        
        self._h5_object_group = position.get_object_group(name)
        
        self.object_np_cache = {}    
        
        self._relation_name = position.get_object_relation(name)
        self.relation = position.get_relation(self._relation_name)
        self.object_np_cache['relation'] = self.relation.get_cache()
        
        edge_table = self._h5_object_group[self.HDF5_OBJECT_EDGE_NAME].value
        self.object_np_cache['edges'] = edge_table \
                                 .view(numpy.uint32) \
                                 .reshape(len(edge_table), -1)
                                 
        id_refs_table = self._h5_object_group[self.HDF5_OBJECT_ID_NAME].value
        self.object_np_cache['id_edge_refs']  = id_refs_table \
                                 .view(numpy.uint32) \
                                 .reshape(len(id_refs_table), -1)
                                                        
        self.object_np_cache['child_ids'] = {}
        for x in self.object_np_cache['id_edge_refs']:
            self.object_np_cache['child_ids'][x[0]] = self.object_np_cache['relation'][self.object_np_cache['edges'][x[1]:x[2], 1]]
            
    @property
    def ids(self):
        return self.object_np_cache['id_edge_refs'][:,0] 
        
        
    def get_object_type(self):
        ItemType = ObjectItem
        if self.position.sub_objects[self.name] in self.position.regions:
            ItemType = TerminalObjectItem
        return ItemType
    
    def get_object_type_of_children(self):
        ItemType = ObjectItem
        if self.position.sub_objects[self.position.sub_objects[self.name]] in self.position.regions:
            ItemType = TerminalObjectItem
        return ItemType
    
    def get(self, obj_id):
        ItemType = self.get_object_type()
        return ItemType(obj_id, self) 
            
    def __iter__(self, obj_ids=None):
        if obj_ids is None:
            obj_ids = self.obj_ids
        for o in obj_ids:
            if len(self.mapping[o]) > 0:
                yield o, self.mapping[o]
                
    def iter_sub_objects(self, obj_ids=None):
        if obj_ids is None:
            obj_ids = self.obj_ids
        for o in obj_ids:
            map_ = self.mapping[o]
            if len(map_) > 0:
                start_node = map_[0,0]
                start_node = start_node.reshape((1,))
                rest_nodes =  map_[:,2]
                yield o, numpy.concatenate((start_node, rest_nodes))
        
    def __str__(self):
        res =  'object: ' + self.name + '\n'   
        if self.relation_name:
            res += ' - relations: '+ self.relation_name + '\n' 
        
        for attribs in self._h5_object_group:
            if attribs not in [self.HDF5_OBJECT_EDGE_NAME, self.HDF5_OBJECT_ID_NAME]:
                res += ' - attributs: ' + attribs + '\n'
        return res
    
    def get_sub_objects(self):
        if self.next_object_level:
            self.sub_objects = self.parent_positon_provider.get_objects(self.next_object_level)
            return self.sub_objects
        else:
            raise RuntimeError('get_sub_objects() No sub objects available for objects of name %s' % self.name)
            
#-------------------------------------------------------------------------------
# main:
#

if __name__ == '__main__':
    tic = timing.time()
    try:
        t = File('/Users/miheld/data/Analysis/H2bTub_20x_hdf5_test1/dump/0037.hdf5')
    except:
        t = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911_2_channels/dump/0037.hdf5')
        
    print 'init time for position  == %5.3f msec' % (timing.time() - tic)
    
    object_name = 'event'
    
    
    position = t[t.positions[0]]
    for object_name in ['primary__primary']:
        pp = position.get_objects(object_name)
        for id in pp.ids:
            print id, '-->', pp.get(id).get_sibling_objects(position.relation_cross[object_name][0]['to'])
        
            
    
    
    

    