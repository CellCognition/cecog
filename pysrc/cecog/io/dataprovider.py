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

#-------------------------------------------------------------------------------
# extension module imports:
#
import h5py, \
       networkx, \
       numpy, \
       vigra

import matplotlib.pyplot as plt
import time as timeing

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
                
    def get_object_definition(self):
        return self.get_definition('object')
        
    
    def get_relation_definition(self):
        return self.get_definition('relation')
        
class Position(_DataProvider):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None

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
            
            obj =  self.get_object_from_id(node_1_time_id, node_1_zslice_id, obj_id)
            print obj['upper_left'], obj['lower_right']
            
        
            
        
        plt.draw()
        plt.show()
        
#    def get_object_from_id(self, time_id, zslice_id, object_id):
#        objects = self._hf_group['time'][str(time_id)]['zslice'][str(zslice_id)]['region']['0']['object']
#        
#        return objects[objects["obj_id"]==object_id]
    
    def get_object(self, object_name):
        objects_description = self.get_object_definition()
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
                raise KeyError('get_object() object "%s" not found in definition.' % object_name)
            
            if object_name not in self._hf_group['object']:
                raise KeyError('get_object() no entries found for object "%s".' % object_name)
            
            h5_object_group = self._hf_group['object'][object_name]
        
            return Objects(object_name, h5_object_group, involved_relation)
    
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
                
        
    def get_bounding_box(self, t, z, o, c=0):
        obj = self._hf_group['time'][str(t[0])]['zslice'][str(z[0])]['region'][str(c)]['object']
        obj = obj[obj['obj_id'] == o]
        return (obj['upper_left'][0], obj['lower_right'][0])
    
    def get_cell(self, t, y, o, c, min_bounding_box_size=50):
        ul, lr = self.get_bounding_box(t, z, o, c)
        
        offset_0 = (min_bounding_box_size - lr[0] + ul[0])
        offset_1 = (min_bounding_box_size - lr[1] + ul[1]) 
        
        ul[0] = max(0, ul[0] - offset_0/2 - cmp(offset_0/2,0) * offset_0 % 2) 
        ul[1] = max(0, ul[1] - offset_1/2 - cmp(offset_1/2,0) * offset_1 % 2)  
        
        lr[0] = min(self._hf_group['image']['channel'].shape[4], lr[0] + offset_0/2) 
        lr[1] = min(self._hf_group['image']['channel'].shape[3], lr[1] + offset_1/2) 
        
        return self._hf_group['image']['channel'][c, t[0], z[0], ul[1]:lr[1], ul[0]:lr[0]]
    
        
        
        
                

        

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


class Moo(object):

    def __init__(self, filename):
        self._hf = h5py.File(filename, 'r')

        self.data = Data(self._hf)

    def close(self):
        self._hf.close()
        
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
    
    def __init__(self, name, h5_object_group, involveld_relation):
        self.name = name
        self._h5_object_group = h5_object_group
        self.relation_name = involveld_relation
        self.relation = position.get_relation(self.relation_name)          
        
        
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
            return self.__getitemiter__(obj_id)    
        else:
            return self.mapping[obj_id]
            
    def __getitemiter__(self, obj_ids):
        for o in obj_ids:
            yield self.mapping[o]
        
    def __str__(self):
        res =  'object: ' + self.name + '\n' 
        
        if self.relation_name:
            res += ' - relations: '+ self.relation_name + '\n' 
        
        for attribs in self._h5_object_group:
            if attribs not in [self.HDF5_OBJECT_EDGE_NAME, self.HDF5_OBJECT_ID_NAME]:
                res += ' - attributs: ' + attribs + '\n'
        return res
    
    def get_obj_ids(self):
        return list(self._h5_object_group[self.HDF5_OBJECT_ID_NAME]['obj_id'])
    
#    def get_obj_idx(self):
#        return xrange(len(self._h5_object_group[self.HDF5_OBJECT_ID_NAME]))

    
    def apply_relation(self, relation, obj_ids=None, position_provider=None):
        if obj_ids is None:
            obj_ids = self.get_obj_ids()
            
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
        
    def get_obj_ids(self):
        pass      
            
    

#-------------------------------------------------------------------------------
# main:
#

if __name__ == '__main__':
    try:
        m = Moo('/Users/miheld/data/Analysis/H2bTub_20x_hdf5_test1/dump/0037.hdf5')
    except:
        
        m = Moo('C:/Users/sommerc/data/Chromatin-Microtubles/Analysis/H2b_aTub_MD20x_exp911/dump/0037.hdf5')

    for sample_id in m.data:
        print sample_id
        for plate_id in m.data[sample_id]:
            print plate_id
            for experiment_id in m.data[sample_id][plate_id]:
                print 'In experiment:', experiment_id
                for position_id in m.data[sample_id][plate_id][experiment_id]:
                    'In position:', position_id
                    position = m.data[sample_id][plate_id][experiment_id][position_id]

                    events = position.get_object('event')

                    primary_primary = position.get_object(events.next_object_level)
                    
                    print events[42][0,2]
                    print primary_primary[events[42][0,2]]
  
                                   
                    
#                    for e in selected_event_id:
#                        primary_object_ids = mapping_tracking[e]['obj_id2']
#                        mapping_primary, onto_object_name = primary_primary.apply_relation(relation_primary_primary, \
#                                                                                           obj_ids=primary_object_ids)
#                        print type(position.get_object(onto_object_name))
#                                   
#                        for prim_obj_id in mapping_primary:
#                            t = mapping_primary[prim_obj_id]['time_idx1']
#                            z = mapping_primary[prim_obj_id]['zslice_idx1']
#                            o = mapping_primary[prim_obj_id]['obj_id1']
#                            c = position.get_definition('region')['channel_idx'][0]
#                            tmp = position.get_cell(t,z,o,c)
#                            vigra.impex.writeImage(tmp, 'c:/Users/sommerc/blub%d_%d_%d.png'%(e,t,o))
                            
                    
                    
                    
                    
