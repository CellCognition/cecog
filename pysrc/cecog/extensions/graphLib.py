"""
Python implementation of a Graph.

Version 1.0.0
Copyright Nathan Denny, May 27, 1999

Changes (Jan Finell):
  - changed the tab size to 4 spaces instead of 8.
  - moved the method documentation into a proper doc string.

"""

#-- Error classes --#
class Graph_duplicate_node(StandardError):
    pass

class Graph_topological_error(StandardError):
    pass
#-- added these since they were missing (Jan Finell) --#

class Graph_no_edge(StandardError):
    pass

class GraphQueue:
    def __init__(self):
        self.q=[]

    def empty(self):
        if(len(self.q)>0):
            return 0
        else:
            return 1

    def count(self):
        return len(self.q)

    def add(self, item):
        self.q.append(item)

    def remove(self):
        item=self.q[0]
        self.q=self.q[1:]
        return item

class GraphStack:
    def __init__(self):
        self.s=[]

    def empty(self):
        if(len(self.s)>0):
            return 0
        else:
            return 1

    def count(self):
        return len(self.s)

    def push(self, item):
        ts=[item]
        for i in self.s:
            ts.append(i)
        self.s=ts

    def pop(self):
        item=self.s[0]
        self.s=self.s[1:]
        return item

class Graph(object):

    def __init__(self):
        super(Graph, self).__init__()
        self.next_edge_id=0
        self.nodes={}
        self.edges={}
        self.hidden_edges={}
        self.hidden_nodes={}

    def copy(self, G):
        """
        Performs a copy of the graph, G, into self.hidden edges and
        hidden nodes are not copied.
        node_id's remain consistent across self and G, however edge_id's
        do not remain consistent.
        Need to implement copy operator on node_data and edge data.
        """
        #--Blank self.
        self.nodes={}
        self.edges={}
        self.hidden_edges={}
        self.hidden_nodes={}
        self.next_edge_id=0
        #--Copy nodes.
        G_node_list=G.node_list()
        for G_node in G_node_list:
            self.add_node(G_node,G.node_data(G_node))
        #--Copy edges.
        for G_node in G_node_list:
            out_edges=G.out_arcs(G_node)
            for edge in out_edges:
                tail_id=G.tail(edge)
                self.add_edge(G_node, tail_id, G.edge_data(edge))

    def add_node(self, node_id, node_data=None):
        """
        Creates a new node with id node_id.  Arbitrary data can be attached
        to the node viea the node_data parameter.
        """
        if (not node_id in self.nodes) and \
               (not node_id in self.hidden_nodes):
            self.nodes[node_id]=([],[],node_data)
        else:
            #print "WARNING: Duplicate node id's. Latest node id was ignored."
            raise Graph_duplicate_node, node_id

    # def is_split_node(self, node_id):
    #     return self.out_degree(node_id) == 0

    # def is_merge_node(self, node_id):
    #     return self.in_degree == 0

    def update_node_data(self, node_id, node_data):
        t = self.nodes[node_id]
        self.nodes[node_id] = (t[0], t[1], node_data)

    def delete_node(self, node_id):
        """
        Deletes the node and all in and out arcs.
        """
        #--Remove fanin connections.
        in_edges=self.in_arcs(node_id)
        for edge in in_edges:
            self.delete_edge(edge)
        #--Remove fanout connections.
        out_edges=self.out_arcs(node_id)
        for edge in out_edges:
            self.delete_edge(edge)
        #--Delete node.
        del self.nodes[node_id]

    def delete_edge(self, edge_id):
        """
        Delets the edge.
        """
        head_id=self.head(edge_id)
        tail_id=self.tail(edge_id)
        head_data=map(None, self.nodes[head_id])
        tail_data=map(None, self.nodes[tail_id])
        head_data[1].remove(edge_id)
        tail_data[0].remove(edge_id)
        del self.edges[edge_id]

    def add_edge(self, head_id, tail_id, edge_data=None):
        """
        Adds an edge (head_id, tail_id).
        Arbitrary data can be attached to the edge via edge_data
        """
        edge_id=self.next_edge_id
        self.next_edge_id=self.next_edge_id+1
        self.edges[edge_id]=(head_id, tail_id, edge_data)
        mapped_head_data=map(None, self.nodes[head_id])
        mapped_head_data[1].append(edge_id)
        mapped_tail_data=map(None, self.nodes[tail_id])
        mapped_tail_data[0].append(edge_id)
        return edge_id

    def hide_edge(self, edge_id):
        """
        Removes the edge from the normal graph, but does not delete
        its information.  The edge is held in a separate structure
        and can be unhidden at some later time.
        """
        self.hidden_edges[edge_id]=self.edges[edge_id]
        ed=map(None, self.edges[edge_id])
        head_id=ed[0]
        tail_id=ed[1]
        hd=map(None, self.nodes[head_id])
        td=map(None, self.nodes[tail_id])
        hd[1].remove(edge_id)
        td[0].remove(edge_id)
        del self.edges[edge_id]

    def hide_node(self, node_id):
        """
        Similar to above.
        Stores a tuple of the node data, and the edges that are incident
        to and from
        the node.  It also hides the incident edges.
        """
        degree_list=self.arc_list(node_id)
        self.hidden_nodes[node_id]=(self.nodes[node_id],degree_list)
        for edge in degree_list:
            self.hide_edge(edge)
        del self.nodes[node_id]

    def restore_edge(self, edge_id):
        """
        Restores a previously hidden edge back into the graph.
        """
        self.edges[edge_id]=self.hidden_edges[edge_id]
        ed=map(None,self.hidden_edges[edge_id])
        head_id=ed[0]
        tail_id=ed[1]
        hd=map(None,self.nodes[head_id])
        td=map(None,self.nodes[tail_id])
        hd[1].append(edge_id)
        td[0].append(edge_id)
        del self.hidden_edges[edge_id]

    def restore_all_edges(self):
        """
        Restores all hidden edges.
        """
        for edge in self.hidden_edges:
            self.restore_edge(edge)

    def restore_node(self, node_id):
        """
        Restores a previously hidden node back into the graph
        and restores all of the hidden incident edges, too.
        """
        hidden_node_data=map(None,self.hidden_nodes[node_id])
        self.nodes[node_id]=hidden_node_data[0]
        degree_list=hidden_node_data[1]
        for edge in degree_list:
            self.restore_edge(edge)
        del self.hidden_nodes[node_id]

    def restore_all_nodes(self):
        """
        Restores all hidden nodes.
        """
        for node in self.nodes:
            self.nodes[node]=self.hidden_nodes[node]
            del self.hidden_nodes[node]

    def has_node(self, node_id):
        """
        Returns 1 if the node_id is in the graph and 0 otherwise.
        """
        return node_id in self.nodes

    def edge(self, head_id, tail_id):
        """
        Returns the edge that connects (head_id,tail_id)
        """
        out_edges=self.out_arcs(head_id)
        for edge in out_edges:
            if self.tail(edge)==tail_id:
                return edge
        raise Graph_no_edge, (head_id, tail_id)

    def number_of_nodes(self):
        return len(self.nodes)

    def number_of_edges(self):
        return len(self.edges)

    def node_list(self):
        """
        Return a list of the node id's of all visible nodes in the graph.
        """
        nl=self.nodes.keys()
        return nl

    #-- Similar to above.
    def edge_list(self):
        """
        """
        el=self.edges.keys()
        return el

    def number_of_hidden_edges(self):
        return len(self.hidden_edges)

    def number_of_hidden_nodes(self):
        return len(self.hidden_nodes)

    def hidden_node_list(self):
        hnl=self.hidden_nodes.keys()
        return hnl[:]

    def hidden_edge_list(self):
        hel=self.hidden_edges.keys()
        return hel[:]

    def node_data(self, node_id):
        """
        Returns a reference to the data attached to a node.
        """
        mapped_data=map(None, self.nodes[node_id])
        return mapped_data[2]

    def edge_data(self, edge_id):
        """
        Returns a reference to the data attached to an edge.
        """
        mapped_data=map(None, self.edges[edge_id])
        return mapped_data[2]

    def head(self, edge):
        """
        Returns a reference to the head of the edge.
        (A reference to the head id)
        """
        mapped_data=map(None, self.edges[edge])
        return mapped_data[0]

    #--Similar to above.
    def tail(self, edge):
        mapped_data=map(None, self.edges[edge])
        return mapped_data[1]

    def out_arcs(self, node_id):
        """
        Returns a copy of the list of edges of the node's out arcs.
        """
        mapped_data=map(None, self.nodes[node_id])
        return mapped_data[1][:]

    #--Similar to above.
    def in_arcs(self, node_id):
        mapped_data=map(None, self.nodes[node_id])
        return mapped_data[0][:]

    #--Returns a list of in and out arcs.
    def arc_list(self, node_id):
        in_list=self.in_arcs(node_id)
        out_list=self.out_arcs(node_id)
        deg_list=[]
        for arc in in_list:
            deg_list.append(arc)
        for arc in out_list:
            deg_list.append(arc)
        return deg_list


    def out_degree(self, node_id):
        mapped_data=map(None, self.nodes[node_id])
        return len(mapped_data[1])

    def in_degree(self, node_id):
        mapped_data=map(None, self.nodes[node_id])
        return len(mapped_data[0])

    def degree(self, node_id):
        mapped_data=map(None, self.nodes[node_id])
        return len(mapped_data[0])+len(mapped_data[1])

    # --- Traversals ---
    def topological_sort(self):
        """
        Performs a topological sort of the nodes by "removing" nodes with
        indegree 0.
        If the graph has a cycle, the Graph_topological_error is thrown
        with the list of successfully ordered nodes.
        """
        topological_list=[]
        topological_queue=GraphQueue()
        indeg_nodes={}
        for node in self.nodes:
            indeg=self.in_degree(node)
            if indeg==0:
                topological_queue.add(node)
            else:
                indeg_nodes[node]=indeg
        while not topological_queue.empty():
            current_node=topological_queue.remove()
            topological_list.append(current_node)
            out_edges=self.out_arcs(current_node)
            for edge in out_edges:
                tail=self.tail(edge)
                indeg_nodes[tail]=indeg_nodes[tail]-1
                if indeg_nodes[tail]==0:
                    topological_queue.add(tail)
        #--Check to see if all nodes were covered.
        if len(topological_list)!=len(self.nodes):
            #print "WARNING: Graph appears to be cyclic."\
            #      " Topological sort is invalid!"
            raise Graph_topological_error, topological_list
        return topological_list


    def reverse_topological_sort(self):
        """
        Performs a reverse topological sort by iteratively "removing" nodes
        with out_degree=0
        If the graph is cyclic, this method throws Graph_topological_error
        with the list of successfully ordered nodes.
        """
        topological_list=[]
        topological_queue=GraphQueue()
        outdeg_nodes={}
        for node in self.nodes:
            outdeg=self.out_degree(node)
            if outdeg==0:
                topological_queue.add(node)
            else:
                outdeg_nodes[node]=outdeg
        while not topological_queue.empty():
            current_node=topological_queue.remove()
            topological_list.append(current_node)
            in_edges=self.in_arcs(current_node)
            for edge in in_edges:
                head_id=self.head(edge)
                outdeg_nodes[head_id]=outdeg_nodes[head_id]-1
                if outdeg_nodes[head_id]==0:
                    topological_queue.add(head_id)
        #--Sanity check.
        if len(topological_list)!=len(self.nodes):
            raise Graph_topological_error, topological_list
        return topological_list

    def dfs(self, source_id):
        """
        Returns a list of nodes in some DFS order.
        """
        nodes_already_stacked={source_id:0}
        dfs_list=[]

        dfs_stack=GraphStack()
        dfs_stack.push(source_id)

        while not dfs_stack.empty():
            current_node=dfs_stack.pop()
            dfs_list.append(current_node)
            out_edges=self.out_arcs(current_node)
            for edge in out_edges:
                if not self.tail(edge) in nodes_already_stacked:
                    nodes_already_stacked[self.tail(edge)]=0
                    dfs_stack.push(self.tail(edge))
        return dfs_list

    def dfs_edges(self, source_id):
        """
        Returns a list of nodes in some DFS order.
        """
        nodes_already_stacked={source_id:0}
        dfs_list=[]

        dfs_stack=GraphStack()
        dfs_stack.push(source_id)


        while not dfs_stack.empty():
            current_node=dfs_stack.pop()

            out_edges=self.out_arcs(current_node)
            for edge in out_edges:
                if not self.tail(edge) in nodes_already_stacked:
                    nodes_already_stacked[self.tail(edge)]=0
                    dfs_stack.push(self.tail(edge))
                    dfs_list.append((current_node,self.tail(edge)))
        return dfs_list

    def bfs(self, source_id):
        """
        Returns a list of nodes in some BFS order.
        """
        nodes_already_queued={source_id:0}
        bfs_list=[]

        bfs_queue=GraphQueue()
        bfs_queue.add(source_id)

        while not bfs_queue.empty():
            current_node=bfs_queue.remove()
            bfs_list.append(current_node)
            out_edges=self.out_arcs(current_node)
            for edge in out_edges:
                if not self.tail(edge) in nodes_already_queued:
                    nodes_already_queued[self.tail(edge)]=0
                    bfs_queue.add(self.tail(edge))
        return bfs_list


    def back_bfs(self, source_id):
        """
        Returns a list of nodes in some BACKWARDS BFS order.
        Starting from the source node, BFS proceeds along back edges.
        """
        nodes_already_queued={source_id:0}
        bfs_list=[]

        bfs_queue=GraphQueue()
        bfs_queue.add(source_id)

        while not bfs_queue.empty():
            current_node=bfs_queue.remove()
            bfs_list.append(current_node)
            in_edges=self.in_arcs(current_node)
            for edge in in_edges:
                if not self.head(edge) in nodes_already_queued:
                    nodes_already_queued[self.head(edge)]=0
                    bfs_queue.add(self.head(edge))
        return bfs_list
