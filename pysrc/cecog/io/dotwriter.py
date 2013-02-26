"""
dotwriter.py

Export tracking graphs to a graphviz *.dot file

"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


class DotWriter(object):

    SHAPE = 'plaintext'
    NODE_STYLE = ' [shape=circle]'
    EDGE_STYLE = ' [style=bold, arrowsize=0.5]'

    def __init__(self, filename, tracker, default_node_color="#AAAAAA"):
        self.tracker = tracker
        self._known_node_ids = {}
        self._edges = {}

        self.default_node_color = default_node_color
        self._file = open(filename, "w")

        self._file.write("digraph G {\n")
        tmp = "ranksep=.01; nodesep=1.5; " +\
              "fontname=\"Helvetica\"; rankdir=TB;\n"
        self._file.write(tmp)

        timestrings = ["time %d" % x for x in tracker.getTimePoints()]
        self._file.write("node%s;\n" %self.NODE_STYLE)

        for frame, node_ids in tracker.getTimePoints().iteritems():
            for object_id in node_ids:
                node_id = tracker.getNodeIdFromComponents(frame, object_id)
                if frame == tracker.start_frame:
                    self._traverseGraph(node_id)
                # find appearing nuclei
                elif not self._known_node_ids.has_key(node_id):
                    self._traverseGraph(node_id)

        # write nodes
        tmp_node = '"%s" [%s];\n'

        for node_id in self._known_node_ids.iterkeys():
            node = self.tracker.graph.node_data(node_id)
            node_attrs = []

            if node.strHexColor is None:
                hexcolor = self.default_node_color
            else:
                hexcolor = node.strHexColor
            node_attrs += ['style=filled','fillcolor="%s"' %hexcolor]
            if len(node.dctProb) > 0:
                classes = 1.0 / len(node.dctProb)
                prob = node.dctProb[node.iLabel]
                # scale the node size between 1.1 (100% prob) and 0.1 (1/n% prob, less possible)
                width = 1.0 * (prob - classes) / (1.01 - classes) + 0.1
                height = width
                node_attrs += ['label="%s"' %node_id,
                               "width=\"%.2f\"" % width,
                               "height=\"%.2f\"" % height,
                               'fixedsize="%s\"' % True]
            else:
                node_attrs += ['fixedsize="%s\"' % True]

            node = tmp_node %(node_id, ",".join(node_attrs))
            self._file.write(node)

        # write ranks (force node to be on the same ranks)
        for node, (frame, object_ids) in zip(timestrings, tracker.getTimePoints().iteritems()):
            tmp = "{%s}\n" % "; ".join(['rank=same'] +
                                       ['"%s"' % tracker.getNodeIdFromComponents(frame, object_id)
                                        for object_id in object_ids])
            self._file.write(tmp)

        self._file.write("}\n")
        self._file.close()

    def _traverseGraph(self, node_id, level=0):
        if node_id not in self._known_node_ids:
            self._known_node_ids[node_id] = " "

        for edge_id in self.tracker.graph.out_arcs(node_id):
            node_idn = self.tracker.graph.tail(edge_id)

            # since merges are possible, a node reachable more than one time
            # -> store all edges (combined node ids) and follow them only once
            key = "%s--%s" % (node_id, node_idn)
            if not self._edges.has_key(key):
                self._edges[key] = 1
                self._writeEdge(node_id, node_idn)
                self._traverseGraph(node_id, level+1)

    def _writeEdge(self, node_id, node_idn):
        self._file.write('"%s" -> "%s"%s;\n' %(node_id, node_idn, self.EDGE_STYLE))
