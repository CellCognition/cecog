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
       vigra

import matplotlib.pyplot as plt
import time as timing

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

def print_timing(func):
    def wrapper(*arg):
        t1 = timeing.time()
        res = func(*arg)
        t2 = timeing.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper

#-------------------------------------------------------------------------------
# classes:
#

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
    
    def get_definition(self, definition_key):
        """
        returns: the first found value for a given 'defintion_key', by searching up the tree.
                 if 'definition_key' can not be found it reaises a KeyError
        """
        # check local definition first
        # FIXME: The global at the root is a special case. 
        if 'definition' in self._hf_group:
            if definition_key in self._hf_group['definition']:
                return self._hf_group['definition'][definition_key]
            
        # check parent
        if self._parent._hf_group.name == '/':
            # we are root already.
            
            # definition is manditory the root node
            if definition_key in self._parent._hf_group['definition']:
                return self._parent._hf_group['definition'][definition_key]
            else:
                raise KeyError('get_definition(): definition for key "%s" not be found in the tree!' % (definition_key,))
        
        else:
            # recurse one level up
            return self._parent.get_definition(definition_key)
                
    def get_objects_definition(self):
        return self.get_definition('object')
        
    
    def get_relation_definition(self):
        return self.get_definition('relation')
    
    def close(self):
        self._hf_group.close()
        
class Position(_DataProvider):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None
    def __init__(self, hf_group, parent=None):
        super(Position, self).__init__(hf_group, parent)
        self._hf_group_np_copy = self._hf_group['image']['channel'].value
        self._cache_terminal_objects()
        
    def _cache_terminal_objects(self):
        t = len(self._hf_group['time'])
        z = len(self._hf_group['time']['0']['zslice'])
        c = len(self._hf_group['time']['0']['zslice']['0']['region'])

        self._terminal_objects_np_cache = numpy.zeros((c, t, z), dtype=numpy.ndarray)
        
        for t, tg in self._hf_group['time'].iteritems():
            t = int(t)
            for z, zo in tg['zslice'].iteritems():
                z = int(z)
                for c, co in zo['region'].iteritems():
                    c = int(c)
                    self._terminal_objects_np_cache[c,t,z] = co['object'].value, co['crack_contour'].value

    def get_events(self):
        object = self._hf_group['object']['event']
        relation = self._hf_group['relation']['tracking']
        relation_primary_primary = self._hf_group['relation']['relation___primary__primary']
        channel = self._hf_group['image']['channel']
        time = self._hf_group['time']

        ids = object['id']
        graph = networkx.Graph()
        for id in ids:
            relation_idx = object['edge'][object['edge']['obj_id'] == id]['relation_idx']
            edges = relation[list(relation_idx)]
            for edge in edges:
                node_id1 = tuple(edge)[:3]
                node_id2 = tuple(edge)[3:]
                graph.add_node(node_id1, {'time_idx': edge['time_idx1'], 'zslice_idx': edge['zslice_idx1'], 'obj_id': edge['obj_id1']})
                graph.add_node(node_id2, {'time_idx': edge['time_idx2'], 'zslice_idx': edge['zslice_idx2'], 'obj_id': edge['obj_id2']})
                graph.add_edge(node_id1, node_id2)
                #print node_id1, '==', node_id2



        sub_graph = networkx.connected_component_subgraphs(graph)[0]
        
        
        # get start node
        start_node = None
        for node, in_degree in  sub_graph.degree_iter():
            print node, in_degree
            if in_degree == 1:
                start_node = node
                break
                
        assert start_node is not None, 'cyclic graph'
        
        print 'Start node', start_node
        
#        # convert to DiGraph
#        di_sub_graph = networkx.algorithms.traversal.depth_first_search.dfs_tree(sub_graph)
        networkx.drawing.nx_pylab.draw_spectral(sub_graph)
        
            
        for node_1, node_2 in  networkx.algorithms.traversal.depth_first_search.dfs_edges(sub_graph, start_node):
            node_1_time_id = node_1[0]
            node_1_zslice_id = node_1[1]
            node_1_obj_id = node_1[2]
            
            node_2_time_id = node_2[0]
            node_2_zslice_id = node_2[1]
            node_2_obj_id = node_2[2]
         
            obj_id =  relation_primary_primary[node_1_obj_id][-1]
            
            obj =  self.get_objects_from_id(node_1_time_id, node_1_zslice_id, obj_id)
            print obj['upper_left'], obj['lower_right']
            
        
            
        
        plt.draw()
        plt.show()
        
#    def get_objects_from_id(self, time_id, zslice_id, object_id):
#        objects = self._hf_group['time'][str(time_id)]['zslice'][str(zslice_id)]['region']['0']['object']
#        
#        return objects[objects["obj_id"]==object_id]
    
    def get_objects(self, object_name):
        objects_description = self.get_objects_definition()
        object_name_found = False
        
        for o_desc in objects_description:
            if o_desc[0] == object_name:
                object_name_found = True
                if o_desc[1]:
                    involved_relation = o_desc[1]
        
        is_terminal = len(involved_relation) == 0
        if is_terminal:
            return TerminalObjects(object_name)
        else:
            # if a relation is involved with this objects
            # also an group must be specified under positions
            if not object_name_found:
                raise KeyError('get_objects() object "%s" not found in definition.' % object_name)
            
            if object_name not in self._hf_group['object']:
                raise KeyError('get_objects() no entries found for object "%s".' % object_name)
            
            h5_object_group = self._hf_group['object'][object_name]
        
            return Objects(object_name, h5_object_group, involved_relation, self)
    
    def get_relation(self, relation_name):
        releations = self.get_relation_definition()
        
        releation_name_found = False
        for rel in releations:
            if rel[0] == relation_name:
                releation_name_found = True
                from_object_name = rel[1]
                to_object_name = rel[3]
                
        if not releation_name_found:
            raise KeyError('get_relation() releation "%s" not found in definition.' % relation_name)
        
        if relation_name not in self._hf_group['relation']:
            raise KeyError('get_relation() no entries found for relation "%s".' % relation_name)
        
        h5_relation_group = self._hf_group['relation'][relation_name]
        
        return Relation(relation_name, h5_relation_group, (from_object_name, to_object_name))
                
        
    def get_bounding_box(self, t, z, obj_idx, c=0):
#        obj = self._hf_group['time'][str(t)]['zslice'][str(z)]['region'][str(c)]['object']
        obj = self._terminal_objects_np_cache[c,t,z][0]
        return (obj['upper_left'][obj_idx], obj['lower_right'][obj_idx])
    
    def get_image(self, t, z, obj_idx, c, bounding_box=None, min_bounding_box_size=50):
        if bounding_box is None:
            ul, lr = self.get_bounding_box(t, z, obj_idx, c)
        else:
            ul, lr = bounding_box
        
        offset_0 = (min_bounding_box_size - lr[0] + ul[0])
        offset_1 = (min_bounding_box_size - lr[1] + ul[1]) 
        
        ul[0] = max(0, ul[0] - offset_0/2 - cmp(offset_0%2,0) * offset_0 % 2) 
        ul[1] = max(0, ul[1] - offset_1/2 - cmp(offset_1%2,0) * offset_1 % 2)  
        
        lr[0] = min(self._hf_group['image']['channel'].shape[4], lr[0] + offset_0/2) 
        lr[1] = min(self._hf_group['image']['channel'].shape[3], lr[1] + offset_1/2) 
        
        bounding_box = (ul, lr)
        
        return self._hf_group_np_copy[c, t, z, ul[1]:lr[1], ul[0]:lr[0]], bounding_box

    def get_crack_contours(self, t, z, obj_idx, c):      
#        print numpy.asarray( zlib.decompress( \
#                              base64.b64decode(self._terminal_objects_np_cache[c,t,z][1] \
#                                [obj_idx])).split(','), dtype=numpy.uint32).reshape(-1,2)[0,:]
                                
        return numpy.asarray( zlib.decompress(base64.b64decode(self._terminal_objects_np_cache[c,t,z][1][obj_idx])).split(','), dtype=numpy.float32).reshape(-1,2)
        
    def get_object_data(self, t, z, obj_idx, c):
        bb = self.get_bounding_box(t, z, obj_idx, c)
        img, new_bb = self.get_image(t, z, obj_idx, c, bb)
        cc = self.get_crack_contours(t, z, obj_idx, c)
        
        
        cc[:,0] -= new_bb[0][0]
        cc[:,1] -= new_bb[0][1]
        
        return img, cc
        
    
        
        
        
                

        

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
            position = self[s, p, e, pos]
            c = position.get_definition('region')['channel_idx'][0]
    
            events = position.get_objects(object_name) 
            primary_primary = events.get_sub_objects()
            
            for event_id, prim_prims_ids in events.iter_sub_objects():  
                res = []
                for prim_prim_id, reg_prim_id in primary_primary.iter_sub_objects(prim_prims_ids):
                    t = primary_primary[prim_prim_id][0][1]
                    z = primary_primary[prim_prim_id][0][2]
                    obj_idx = primary_primary[prim_prim_id][0][3]
                    obj_id= primary_primary[prim_prim_id][0][0]
                    img, cc = position.get_object_data(t, z, obj_idx, c) 
                    tmp = (t, img, cc)
                    res.append(tmp)
            
                res.sort(cmp=lambda x,y: cmp(x[0],y[0]))
                yield res
                
                    
        
class Relation(object):
    def __init__(self, relation_name, h5_table, from_to_object_names):
        self.from_object, self.to_object = from_to_object_names
        self.name = relation_name
        self.h5_table = h5_table
        self.h5_table_np_copy = self.h5_table.value
        self.h5_table_np_copy = self.h5_table_np_copy.view(numpy.uint32) \
                                 .reshape(len(self.h5_table_np_copy), -1)   # shape can be (.,4) or (.,8) 
                                                                            # due to triple in obj_idx        
    def __str__(self):
        return 'relation: ' + self.name + '\n' + ' - ' + self.from_object + ' --> ' + self.to_object + '\n'
    
    def map(self, idx):
        return self.h5_table_np_copy[idx,:]
              

class Objects(object):
    HDF5_OBJECT_EDGE_NAME = 'edge'
    HDF5_OBJECT_ID_NAME = 'id'
    
    def __init__(self, name, h5_object_group, involveld_relation, position):
        self.name = name
        self._h5_object_group = h5_object_group
        self.relation_name = involveld_relation
        self.relation = position.get_relation(self.relation_name)     
        self.parent_positon_provider = position 
        self.sub_objects = None
        self._obj_ids_np_copy = self._h5_object_group[self.HDF5_OBJECT_ID_NAME]['obj_id']
        
        object_edges = self._h5_object_group[self.HDF5_OBJECT_EDGE_NAME]
        object_id_edge_refs = self._h5_object_group[self.HDF5_OBJECT_ID_NAME]
        
        _object_id_edge_refs_np_copy = object_id_edge_refs.value
        self._object_id_edge_refs_np_copy = _object_id_edge_refs_np_copy \
                                 .view(numpy.uint32) \
                                 .reshape(len(_object_id_edge_refs_np_copy), 3)
                                 
        _object_edge_np_copy = object_edges.value
        self._object_edge_np_copy = _object_edge_np_copy \
                                 .view(numpy.uint32) \
                                 .reshape(len(object_edges), 2)
                                 
        self.mapping, self.next_object_level = self.apply_relation(self.relation)   
        
    def __getitem__(self, obj_id):
        if isinstance(obj_id, (list, tuple)):
            return self.__iter__(obj_id)    
        else:
            return self.mapping[obj_id]
            
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
            if len(self.mapping[o]) > 0:
#                print ' getting event', o
                temp = self.mapping[o]
                start_node = temp[0,2]
                start_node = start_node.reshape((1,))
                rest_nodes =  temp[:,2]
                yield o, numpy.concatenate((start_node, rest_nodes))
        
    def __str__(self):
        res =  'object: ' + self.name + '\n' 
        
        if self.relation_name:
            res += ' - relations: '+ self.relation_name + '\n' 
        
        for attribs in self._h5_object_group:
            if attribs not in [self.HDF5_OBJECT_EDGE_NAME, self.HDF5_OBJECT_ID_NAME]:
                res += ' - attributs: ' + attribs + '\n'
        return res
    
    @property
    def obj_ids(self):
        return self._obj_ids_np_copy
    
    def get_sub_objects(self):
        if self.next_object_level:
            self.sub_objects = self.parent_positon_provider.get_objects(self.next_object_level)
            return self.sub_objects
        else:
            raise RuntimeError('get_sub_objects() No sub objects available for objects of name %s' % self.name)
    
    def apply_relation(self, relation, obj_ids=None, position_provider=None):
        if obj_ids is None:
            obj_ids = self.obj_ids
            
#        relation_idx = dict([(x[0], relation.map(self._object_edge_np_copy[x[1]:x[2], 1])) for x in self._object_id_edge_refs_np_copy])
#        relation_idx = dict([(x[0], (self._object_edge_np_copy[x[1]:x[2], 1])) for x in self._object_id_edge_refs_np_copy if x[0] in obj_ids])
       
        relation_idx = {}
        for x in self._object_id_edge_refs_np_copy:
            relation_idx[x[0]] = self._object_edge_np_copy[x[1]:x[2], 1]
                            
        self.relation_idx = relation_idx
        
        related_obj = {}   
        for o, r in relation_idx.iteritems():
            related_obj[o] = relation.map(r)
    
        self.mapping = related_obj
        return related_obj, relation.to_object
    


"""
#        Timing results for all obj_ids from primary__primary
#        ====================================
#        timeit_1 took 10114.000 ms
#        timeit_2 did not finish in finite time
#        timeit_3 took 48998.000 ms (extreme memory consumption up to 3.2 GB)
#        timeit_4 took 14926.000 ms (extreme memory consumption up to 2.1 GB)
#        timeit_5 took 4288.000 ms

#        Timing results for one object from events
#        ====================================
#        timeit_1 took 213.000 ms
#        timeit_2 took 64.000 ms
#        timeit_3 took 6.000 ms 
#        timeit_4 took 3.000 ms
#        timeit_5 took 10.000 ms
        
        @print_timing
        def timeit_1():
            for row in relation_edges:
                if row[0] in obj_ids:
                    relation_idx[row[0]].append(row[1])   
        @print_timing    
        def timeit_2():
            for o_id in obj_ids:
                relation_idx[o_id].extend(relation_edges[relation_edges['obj_id'] == o_id]['relation_idx'])
        
        @print_timing    
        def timeit_3():
            tt = relation_edges.value
            tt = tt.view(numpy.uint32).reshape(len(tt), 2)
                    
            for row in tt[numpy.logical_or.reduce([tt[:,0] == x for x in obj_ids]),:]:
                relation_idx[row[0]].append(row[1])

        @print_timing
        def timeit_4():
            # is memory intense! cause of outer product
            tt = relation_edges.value
            tt = tt.view(numpy.uint32).reshape(len(tt), 2)
            
            obj_ids2 = numpy.expand_dims(obj_ids, 1)
            
            for row in tt[numpy.any(tt[:, 0] == obj_ids2, 0), :]:
                relation_idx[row[0]].append(row[1])
                 
        @print_timing
        def timeit_5():
            tt = relation_edges.value
            tt = tt.view(numpy.uint32).reshape(len(tt),2)
            
            @numpy.vectorize
            def selected(elmt): return elmt in obj_ids
            
            for row in tt[selected(tt[:, 0]),:]:
                relation_idx[row[0]].append(row[1])
        
        # use different implementation of the lookup
        # when itheer all obj_ids are requested or just
        # a given (usually small) list of obj_ids
        if use_all_obj_ids:
            timeit_5()
        else:
            timeit_4()
"""

    
class TerminalObjects(Objects):
    def __init__(self, name):
        super(TerminalObjects, self).__init__(name, None, [])
        
    @property
    def obj_ids(self):
        pass      
            
    

#-------------------------------------------------------------------------------
# main:
#

if __name__ == '__main__':
    try:
        t = File('/Users/miheld/data/Analysis/H2bTub_20x_hdf5_test1/dump/0037.hdf5')
    except:
        
        t = File('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911/dump/0037.hdf5')
        
    for i, a in enumerate(t.traverse_objects('event')):
        vigra.impex.writeImage(numpy.concatenate([b[1] for b in a], axis=0), '%03d.png'%i)

    
#    import cProfile, pstats
#    cProfile.run('t.traverse_objects("event")', 'profile-result')
#    ps = pstats.Stats('profile-result')
#    ps.strip_dirs().sort_stats('cumulative').print_stats()
    

    