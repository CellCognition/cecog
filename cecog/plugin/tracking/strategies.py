"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

import os
import re
import numpy
from sklearn.cross_validation import KFold

from cecog import ccore
from cecog.gui.guitraits import (BooleanTrait,
                                 IntTrait,
                                 FloatTrait,
                                 StringTrait)


from cecog.plugin import stopwatch
from cecog.plugin.tracking.manager import _TrackingPlugin 
from cecog.plugin.tracking.learning_support import gettingRaw
from cecog.plugin.tracking import joining

import math
from collections import OrderedDict

from PyQt5 import QtWidgets
from PyQt5.Qt import QFrame, QPushButton

from cecog.logging import LoggerObject
from cecog.extensions.graphLib import Graph
from cecog import ccore   


class BaseTracker(LoggerObject):
    
    def __init__(self):
        super(BaseTracker, self).__init__()

    def _init(self):
        self.graph = Graph()
        self._frame_data = OrderedDict()

    def track_next_frame(self, frame, samples):
        raise NotImplementedError("ABC class")

    def clone_graph(self, timeholder, channel, region):
        """Clone the tracking graph with data from a different channel."""

        ngraph = Graph()

        # add nodes from other segmentation region
        for nodeid in self.graph.node_list():
            iframe, objid = self.split_nodeid(nodeid)[:2]
            sample = timeholder[iframe][channel].get_region(region)[objid]
            ngraph.add_node(nodeid, sample)

        for edge in self.graph.edges.values():
            ngraph.add_edge(*edge)

        return ngraph
    
    @staticmethod
    def node_id(frame, object_label):
        return '%d_%s' %(frame, object_label)

    @staticmethod
    def split_nodeid(nodeid):
        return tuple([int(i) for i in nodeid.split('_')])
    
    @property
    def start_frame(self):
        """Return the index of the first frame."""
        return min(self._frame_data.keys())

    @property
    def end_frame(self):
        """Returns the index of the last frame currently processed."""
        return max(self._frame_data.keys())

    def render_tracks(self, frame, size, n=5, thick=True, radius=3):
        img_conn = ccore.Image(*size)
        img_split = ccore.Image(*size)

        if n < 0 or frame-n+1 < self.start_frame:
            current = self.start_frame
            n = frame-current+1
        else:
            current = frame-n+1

        found = False
        for i in range(n):
            col = int(max(255.*(i+1)/n, 255))

            if current in self._frame_data:
                preframe = self.closest_preceding_frame(current)
                if preframe is not None:
                    found = True
                    for objIdP in self._frame_data[preframe]:
                        nodeIdP = self.node_id(preframe, objIdP)
                        objP = self.graph.node_data(nodeIdP)

                        if self.graph.out_degree(nodeIdP) > 1:
                            img = img_split
                        else:
                            img = img_conn

                        for edgeId in self.graph.out_arcs(nodeIdP):
                            nodeIdC = self.graph.tail(edgeId)
                            objC = self.graph.node_data(nodeIdC)
                            ccore.drawLine(ccore.Diff2D(*objP.oCenterAbs),
                                           ccore.Diff2D(*objC.oCenterAbs),
                                           img, col,
                                           thick=thick)
                            ccore.drawFilledCircle(
                                ccore.Diff2D(*objC.oCenterAbs), radius, img_conn, col)
            current += 1

        if not found and frame in self._frame_data:
            for objId in self._frame_data[frame]:
                nodeId = self.node_id(frame, objId)
                obj = self.graph.node_data(nodeId)
                ccore.drawFilledCircle(ccore.Diff2D(*obj.oCenterAbs),
                                       radius, img_conn, col)

        return img_conn, img_split

class TrackingStructuredLearning(_TrackingPlugin, BaseTracker):

    LABEL = 'Structured Learning tracker'
    NAME = 'structured_learning_tracker'
    COLOR = '#FFFF00'
    DOC = ''''1. Building training set (TS)
    a. Use NN tracker to output first estimates of trajectories ->hdf5
    b. hdf5 -> xml files
    c. With the browser, manual correction of cell trajectories saved in xml files
2. Learning to track
    a. Load TS from xml files
    b. Grid search the right parameters and learn a tracking model on the TS
    c. Report tracking accuracy and save model
3. Predicting tracks
    a. Load classifier from ** file and features from hdf5 files
    b. Predict tracks and save in hdf5
'''

    REQUIRES = None
    NAME_FILTERS = ['Settings files (*.conf)', 'All files (*.*)']
    PARAMS = [('max_doublet_distance', IntTrait(45, 0, 400, label='Max distance between elements of a doublet')),
              ('max_move_distance', IntTrait(40, 0, 400, label='Max move distance')),
              ('max_other_distance', IntTrait(30, 0, 400, label='Max distance for merge and split')),
              ('max_hypothesis_generation', IntTrait(5, 0, 15, label='Max number of hypotheses per cell')),
              ('training_set_folder', StringTrait('', 1000, label='Training set folder',widget_info=StringTrait.STRING_PATH)),
              ('model_folder', StringTrait('', 1000, label='Model folder',widget_info=StringTrait.STRING_PATH)),
              ]
    
    def __init__(self, *args, **kwargs):
        _TrackingPlugin.__init__(self, *args, **kwargs)
        BaseTracker.__init__(self)

    def render_to_gui(self, panel):
        '''
        Here, we set all buttons for the interface. When setting a button, we just give the link to the
        function to execute, we don't execute it otherwise it's going to pop out when the plugin is added
        '''        
        
        panel.add_group(None,
                       [('max_doublet_distance', (0,0,1,1)),
                        ('max_move_distance', (1,0,1,1)),
                        ('max_other_distance', (0,1,1,1)),
                        ('max_hypothesis_generation', (1,1,1,1)),
                        ], link='tracking_parameters', label='Tracking parameters for hypothesis generation'
                        )
        
        panel.add_input('training_set_folder')
        panel.add_input('model_folder')
        panel.add_button("Learn tracking model", self._learn)
        #I guess it's not relevant since for that there is the button "test tracking" panel.add_button("Predict cell tracking", self._predict)
        self.panel=panel

    @stopwatch()
    def _run(self, *args, **kwargs):
        # the run function is actually not needed
        print args, kwargs
        return
    
    def track_next_frame(self, frame, samples):
        # To be implemented that's the iterative tracking part
        
        # Here samples of the current frame are just added to the graph structure
        self._frame_data.setdefault(frame, [])
        for label, sample in samples.iteritems():
            node_id = self.node_id(frame, label)
            self.graph.add_node(node_id, sample)
            self._frame_data[frame].append(label)

        # connect time point only if any object is present
        if len(self._frame_data[frame]) > 0:
            self.connect_nodes(frame)
            
    def gettingSolu(self):
        '''
       Info a recuperer : where to find information such as result folder or primary channel name
        '''
        modelFolder=self.params['model_folder']
        dataFolder="Youpi"#####PATH for h5 files of training set
        global FEATURE_NUMBER
    
        #tableau qui contiendra toutes les features de tlm pr voir lesquelles contiennent des NaN
        tabF= None
        newFrameLot = None

        training_files = filter(lambda x: '.xml' in x, os.listdir(self.params['training_set_folder']))
        experiment_list=[]
        for file_ in experiment_list:
            plate = file_.split('__')[0][2:]
            well = file_.split('__')[1][1:]
            experiment_list.append((plate, well))
    
        for plate, well in experiment_list:
            filename = os.path.join(dataFolder, plate,'hdf5', well+".ch5")
            filenameT =os.path.join(self.params['training_set_folder'], 'PL{}___P{}___T00000.xml'.format(plate, well))
            
            #ajout du frameLot et du tabF
            frameLotC, tabFC = gettingRaw(filename, filenameT, plate, well, name_primary_channel='primary__primary3')
            
            if frameLotC==None:
                sys.stdout.write("File {} containing data for plate {}, well {} does not contain all necessary data".format(filename, plate, well))
                continue
            
            if newFrameLot == None:
                newFrameLot = frameLotC 
            else: newFrameLot.addFrameLot(frameLotC)
            
            tabF = tabFC if tabF == None else np.vstack((tabF, tabFC))
        
        print "final training set content :"
        count, total= newFrameLot.statisticsTraining2()
        print count, total
        
        #en ce qui concerne le nettoyage des NaN
        featuresToDelete = np.where(np.isnan(tabF))[1]
        
        newFrameLot.clean(featuresToDelete) ##np.delete(X, f, 1)
        FEATURE_NUMBER -=len(featuresToDelete)
    
        fichier = open(os.path.join(modelFolder, "featuresToDelete.pkl"), 'w')
        pickle.dump(featuresToDelete, fichier)
        fichier.close()
    
        #print FEATURE_NUMBER
        #print "uplets now"
        #ICI ON RECUPERE DONC LES SINGLETS ET DOUBLETS AVEC LA VALEUR DU TRAINING DANS CELL.TO SI ILS Y SONT, NONE SINON
        #POUR LE CENTRE ET LES FEATURES C'EST LA MOYENNE DES OBJETS DU SINGLET
        singlets, doublets = newFrameLot.getTrainingUplets(None)
    
        return j(singlets, doublets, FEATURE_NUMBER)
    
    def j(singlets, doublets, featSize, training= True):
        solutions= None
        for plate in singlets:
                #print plate
                for well in singlets[plate]:
                    #print well
                    sys.stderr.write("\n plate {}, well {}\n".format(plate, well))
                    for index in singlets[plate][well]:
                        print '-- ',
                        if index+1 not in singlets[plate][well] or singlets[plate][well][index+1]==[]:
                            continue
                        singletsL = singlets[plate][well][index]
                        nextSinglets = singlets[plate][well][index+1]
                        doubletsL = doublets[plate][well][index]
                        nextDoublets = doublets[plate][well][index+1]
                        if len(nextSinglets)==1:
                            continue
                        solution = joining.Solution(plate, well, index, singletsL, nextSinglets, doubletsL, nextDoublets, featSize, training)
                        if solutions == None:
                            solutions= joining.Solutions(solution, lstSolutions = None)
                        else:
                            solutions.append(solution)    
        return solutions
    
    def foldingBig(self, mesSolu, trainT, testT, n_big_fold, small=True):
        '''
        Splitting the data to perform cross-validation, first level (need two levels because
        we need to choose the parameter C of the SVM)
        '''
        if n_big_fold == -1:
            minMax = mesSolu.normalisation()
            output = open(os.path.join(self.params['model_folder'],"minMax_data_all.pkl"), "w")  
            pickle.dump(minMax, output)
            output.close()
        
        else:
            train, test =trainT[n_big_fold], testT[n_big_fold]
            if small:
                kf = KFold(len(train), nb_folds, shuffle = True)
                trainST = []; testST = []
                for tr, te in kf:
                    trainST.append(tr); testST.append(te)
                
            training_set = filter(lambda x : mesSolu.lstSolutions.index(x) in train, mesSolu.lstSolutions)
            test_set = filter(lambda x : mesSolu.lstSolutions.index(x) in test, mesSolu.lstSolutions)
            training_sol = joining.Solutions(solution = None, lstSolutions = training_set)
            test_sol = joining.Solutions(solution = None, lstSolutions = test_set)
            
            minMax = training_sol.normalisation()
            #test_sol.normalisation(minMax)
            output = open(os.path.join(loadingFolder,"minMax"+str(n_big_fold)+".pkl"), "w")  
            pickle.dump(minMax, output)
            output.close()
            output = open(os.path.join(loadingFolder,"data_TRAIN_fold_BIG"+str(n_big_fold)+".pkl"), "w")  
            pickle.dump(training_sol, output)
            output.close()
            
            if small:
                training_sol.denormalisation(minMax)
                
                for n_f in range(nb_folds):
                    folding(training_sol, trainST, testST, n_f, n_big_fold) 
            
            td = {}
            for sol in test_sol.lstSolutions:
                if sol.plate not in td:
                    td[sol.plate]={}
                if sol.well not in td[sol.plate]:
                    td[sol.plate][sol.well]=[]
                td[sol.plate][sol.well].append(sol.index)
            output = open(os.path.join(loadingFolder,"data_TEST_fold_BIG"+str(n_big_fold)+".pkl"), "w")  
            pickle.dump(td, output)
            output.close()
    
        return 1
    
    def folding(mesSolu, trainT, testT, n_fold, n_big_fold):
        '''
        Splitting the data to perform cross-validation, second level
        '''
        if n_fold == -1:
            minMax = mesSolu.normalisation()
            output = open(os.path.join(loadingFolder,"minMax_data_all.pkl"), "w")  
            pickle.dump(minMax, output)
            output.close()
        
        else:
            train, test =trainT[n_fold], testT[n_fold]
            training_set = filter(lambda x : mesSolu.lstSolutions.index(x) in train, mesSolu.lstSolutions)
            test_set = filter(lambda x : mesSolu.lstSolutions.index(x) in test, mesSolu.lstSolutions)
            
            training_sol = joining.Solutions(solution = None, lstSolutions = training_set)
            test_sol = joining.Solutions(solution = None, lstSolutions = test_set)
    
            minMax = training_sol.normalisation()
            #test_sol.normalisation(minMax)
            output = open(os.path.join(loadingFolder,"minMax"+str(n_big_fold)+'_'+str(n_fold)+".pkl"), "w")  
            pickle.dump(minMax, output)
            output.close()
            output = open(os.path.join(loadingFolder,"data_TRAIN_fold_SMALL"+str(n_big_fold)+'_'+str(n_fold)+".pkl"), "w")  
            pickle.dump(training_sol, output)
            output.close()
            training_sol.denormalisation(minMax)
            
            td = {}
            for sol in test_sol.lstSolutions:
                if sol.plate not in td:
                    td[sol.plate]={}
                if sol.well not in td[sol.plate]:
                    td[sol.plate][sol.well]=[]
                td[sol.plate][sol.well].append(sol.index)
            output = open(os.path.join(loadingFolder,"data_TEST_fold_SMALL"+str(n_big_fold)+'_'+str(n_fold)+".pkl"), "w")  
            pickle.dump(td, output)
            output.close()
    
        return 1
    
    
    def _learn(self, nb_big_folds=5):
        # example on how to trigger an execution from within the bay
        print "my execution: with param number of hypotheses per cell", self.params['max_hypothesis_generation']
        
        #i.load data set
        mesSolu = self.gettingSolu(self.params['training_set_folder'], os.path.join("PATH_IN"))
        
        #ii. forming folds for cross-validation
        kf = KFold(len(mesSolu.lstSolutions), nb_big_folds, shuffle = True)
        trainT = []; testT = []
        for train, test in kf:
            trainT.append(train); testT.append(test)
        Parallel(n_jobs=3, verbose=5)(delayed(foldingBig)(mesSolu, trainT, testT, n_big_fold, small=True) for n_big_fold in range(nb_big_folds))

        print "TIME TIME TIME TIME TIME", time.clock()
        print 'liste des puissances de C etudiees : ', c_list
        
        Parallel(n_jobs=3, verbose=5)(delayed(wholeProcess)(i, nb_big_folds, nb_folds, args.output, loadingFolder) for i in c_list)
        
        
        
    def _predict(self):
        print "Youpi"
        
    
class TrackingNearestNeighbor(_TrackingPlugin, BaseTracker):

    LABEL = 'Nearest Neighbor tracker'
    NAME = 'nearest_neighbor_tracker'
    COLOR = '#FFFF00'
    DOC = ''':additional_tracking_plugins
'''

    REQUIRES = None

    PARAMS = [('max_object_distance', IntTrait(21, 0, 4000, label='Max object x-y distance')),
              ('max_frame_gap', IntTrait(3, 0, 7, label='Max time-point gap')),
              ('max_split_objects', IntTrait(2, 0, 7, label='Max split events')),
          ]
    
    def __init__(self, *args, **kwargs):
        _TrackingPlugin.__init__(self, *args, **kwargs)
        BaseTracker.__init__(self)

    @stopwatch()
    def _run(self, *args, **kwargs):
        # of no interest here. Use track_next_frame(..)
        print args, kwargs
        return
    
    def render_to_gui(self, panel):
        panel.add_group(None,
                       [('max_object_distance', (0,0,1,1)),
                        ('max_frame_gap', (0,1,1,1)),
                        ('max_split_objects', (1,0,1,1)),
                        ], link='tracking', label='Tracking')    

    def track_next_frame(self, frame, samples):
        self._frame_data.setdefault(frame, [])
        for label, sample in samples.iteritems():
            node_id = self.node_id(frame, label)
            self.graph.add_node(node_id, sample)
            self._frame_data[frame].append(label)

        # connect time point only if any object is present
        if len(self._frame_data[frame]) > 0:
            self.connect_nodes(frame)
            

    def closest_preceding_frame(self, frame):
        """Return the preceding frame or None if the gap between the to frames
        is larget than max_frame_gap."""

        frames = self._frame_data.keys()
        icurrent = frames.index(frame)

        pre_frame = None
        if (0 < icurrent < len(frames)):
            pre_frame = frames[icurrent-1]
        if pre_frame is not None and (frame - pre_frame) > self.params['max_frame_gap']:
            pre_frame = None
        return pre_frame
        
    def connect_nodes(self, iT):
        max_dist2 = math.pow(self.params['max_object_distance'], 2)
        bReturnSuccess = False

        # search all nodes in the previous frame
        # if there is an empty frame, look for the closest frame
        # that contains objects. For this go up to iMaxTrackingGap
        # into the past.
        iPreviousT = self.closest_preceding_frame(iT)

        if iPreviousT is not None:
            bReturnSuccess = True
            dctMerges = {}
            dctSplits = {}

            # for all nodes in this layer
            for iObjIdP in self._frame_data[iPreviousT]:

                strNodeIdP = self.node_id(iPreviousT, iObjIdP)
                oImageObjectP = self.graph.node_data(strNodeIdP)

                lstNearest = []

                for iObjIdC in self._frame_data[iT]:
                    strNodeIdC = self.node_id(iT, iObjIdC)
                    oImageObjectC = self.graph.node_data(strNodeIdC)
                    dist = oImageObjectC.squaredMagnitude(oImageObjectP)

                    # take all candidates within a certain distance
                    if dist < max_dist2:
                        lstNearest.append((dist, strNodeIdC))

                # lstNearest is the list of nodes in the current frame
                # whose distance to the previous node is smaller than the
                # fixed threshold.
                if len(lstNearest) > 0:
                    # sort ascending by distance (first tuple element)
                    lstNearest.sort(key=lambda x: x[0])

                    # take only a certain number as merge candidates (the N closest)
                    # and split candidates (this number is identical).
                    for dist, strNodeIdC in lstNearest[:self.params['max_split_objects']]:
                        try:
                            dctMerges[strNodeIdC].append((dist, strNodeIdP))
                        except KeyError:
                            dctMerges[strNodeIdC] = [(dist, strNodeIdP)]

                        try:
                            dctSplits[strNodeIdP].append((dist, strNodeIdC))
                        except KeyError:
                            dctSplits[strNodeIdP] = [(dist, strNodeIdC)]

            # dctSplits contains for each node the list of potential
            # successors with distance smaller than threshold.
            # dctMerges contains for each node the list of potential
            # predecessors with distance smaller than threshold.

            # prevent split and merge for one node at the same time
            for id_c in dctMerges:
                found_connection = False

                nodes = dctMerges[id_c]
                # for all objects that have only one predecessor within the defined radius,
                # take this predecessor.
                if len(nodes) == 1:
                    self.graph.add_edge(nodes[0][1], id_c)
                    found_connection = True
                else:
                    # If there are several candidates (previous objects fulfilling the condition)
                    # take those candidates in the previous frame that have only one possible
                    # predecessor.
                    for dist, id_p in nodes:
                        if len(dctSplits[id_p]) == 1:
                            self.graph.add_edge(id_p, id_c)
                            found_connection = True

                # if there was no connection found, take the closest predecessor,
                # unless there is none.
                if not found_connection:
                    if len(nodes) > 0:
                        self.graph.add_edge(nodes[0][1], id_c)

        return iPreviousT, bReturnSuccess
        