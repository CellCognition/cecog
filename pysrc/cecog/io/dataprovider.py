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
       networkx

import matplotlib.pyplot as plt

#-------------------------------------------------------------------------------
# cecog imports:
#

#-------------------------------------------------------------------------------
# constants:
#

#-------------------------------------------------------------------------------
# functions:
#

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
        # FIXME: This local definition is a special case. E.g. each Position has a definition 
        #        under each position number
        if 'definition' in self._hf_group:
            if definition_key in self._hf_group['definition']:
                return self._hf_group['definition'][definition_key]
            
        # check parent
        if self._parent._hf_group.name == '/':
            # we are parent already.
            
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
        
        involved_relations = []
        for o_desc in objects_description:
            if o_desc[0] == object_name:
                object_name_found = True
                involved_relations.append(o_desc[1])
                
        if not object_name_found:
            raise KeyError('get_object() object "%s" not found in definition.' % object_name)
        
        if object_name not in self._hf_group['object']:
            raise KeyError('get_object() no entries found for object "%s".' % object_name)
        
        h5_object_group = self._hf_group['object'][object_name]
        
        return Objects(object_name, h5_object_group, involved_relations)
    
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
        
    def __str__(self):
        return 'relation: ' + self.name + '\n' + ' - ' + self.from_object + ' --> ' + self.to_object
    
    def map(self, idx):
        return self.h5_table[list(idx)]
        
        
class Objects(object):
    HDF5_OBJECT_EDGE_NAME = 'edge'
    HDF5_OBJECT_ID_NAME = 'id'
    
    def __init__(self, name, h5_object_group, involveld_relations):
        self.name = name
        self._h5_object_group = h5_object_group
        self.relations = involveld_relations
        self.isTerminal = bool(len(self.relations))
        
    def __str__(self):
        res =  'object: ' + self.name + '\n' 
        
        for rel in self.relations:
            res += ' - relations: '+ rel + '\n' 
        
        for attribs in self._h5_object_group:
            if attribs not in [self.HDF5_OBJECT_EDGE_NAME, self.HDF5_OBJECT_ID_NAME]:
                res += ' - attributs: ' + attribs + '\n'
        return res
    
    def get_obj_ids(self):
        return self._h5_object_group[self.HDF5_OBJECT_ID_NAME]['obj_id']

    
    def apply_relation(self, relation, obj_ids=None, position_provider=None):
        if obj_ids is None:
            obj_ids = self.get_obj_ids()
            
        relation_idx = dict([(x, []) for x in obj_ids])

        for row in self._h5_object_group[self.HDF5_OBJECT_EDGE_NAME]:
            relation_idx[row[0]].append(row[1])
            
#        for obj_id, r_idx in relation_idx.iteritems():
#            pass#print obj_id, '===', relation.map(r_idx)
            
        
        return relation_idx, relation.to_object
        
            
            
        
            
        
            
        
    
    
    
        
        
    
    

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
                print experiment_id
                for position_id in m.data[sample_id][plate_id][experiment_id]:
                    print position_id
                    position = m.data[sample_id][plate_id][experiment_id][position_id]

                    #position.get_events()
                    events = position.get_object('event')
                    print events
                    
                    relation_tracking = position.get_relation(events.relations[0])
                    
                    mapping, onto_objects = events.apply_relation(relation_tracking)
                    
                    primary_primary = position.get_object(onto_objects)
                    
                    relation_primary_primary = position.get_relation(primary_primary.relations[0])
                    
                    print relation_primary_primary
                    
                    
                    
                    
