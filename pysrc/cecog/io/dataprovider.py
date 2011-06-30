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

    def __init__(self, hf_group):
        self._hf_group = hf_group
        self._children = {}
        if self.CHILDREN_GROUP_NAME is not None:
            for name, group in self._hf_group[self.CHILDREN_GROUP_NAME].iteritems():
                self._children[name] = self.CHILDREN_PROVIDER_CLASS(group)
        #print self._children

    def __getitem__(self, name):
        return self._children[name]

    def __iter__(self):
        return self._children.__iter__()

    def keys(self):
        return self._children.keys()

class Position(_DataProvider):

    CHILDREN_GROUP_NAME = None
    CHILDREN_PROVIDER_CLASS = None

    def get_events(self):
        object = self._hf_group['object']['event']
        relation = self._hf_group['relation']['tracking']
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



        #networkx.draw(graph)
        #plt.draw()
        #plt.show()

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
    m = Moo('/Users/miheld/data/Analysis/H2bTub_20x_hdf5_test1/dump/0037.hdf5')

    for sample_id in m.data:
        print sample_id
        for plate_id in m.data[sample_id]:
            print plate_id
            for experiment_id in m.data[sample_id][plate_id]:
                print experiment_id
                for position_id in m.data[sample_id][plate_id][experiment_id]:
                    print position_id
                    position = m.data[sample_id][plate_id][experiment_id][position_id]

                    position.get_events()
