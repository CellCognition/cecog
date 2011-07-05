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
        
    def get_object_from_id(self, time_id, zslice_id, object_id):
        objects = self._hf_group['time'][str(time_id)]['zslice'][str(zslice_id)]['region']['0']['object']
        
        return objects[objects["obj_id"]==object_id]
        

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
                    print position.get_definition('relation2')
