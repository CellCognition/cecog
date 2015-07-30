import sys
import numpy as np

import vigra.impex as vi


def gettingRaw(filename, filenameT, plate, well, secondary=False,name_primary_channel='primary__primary3'):
    global FEATURE_NUMBER
    print "images loading : plate = "+plate+",well = "+well    
    tabF = None
    try:
        frameLotC, tabF = importRawSegFromHDF5(filename, plate, well, secondary=secondary, name_primary_channel=name_primary_channel)
    except ValueError:
        sys.stderr.write( sys.exc_info()[1])
        sys.stderr.write("File {} containing data for plate {}, well {} does not contain all necessary data".format(filename, plate, well))
        return None, None

    if filenameT is not None:
        frameLotC.addTraining2(filename, filenameT)
        print "current training set content :"
        print frameLotC.statisticsTraining2()
    
    return frameLotC, tabF

def importRawSegFromHDF5(filename, plaque, puits, secondary=False, name_primary_channel='primary__primary'):

    pathObjects = "/sample/0/plate/{}/experiment/{}/position/{}/object/{}".format(plaque, puits[:-3], puits[-1], name_primary_channel)
    pathFeatures = "/sample/0/plate/"+plaque+"/experiment/"+puits[:-3]+"/position/"+puits[-1]+"/feature/{}/object_features".format(name_primary_channel)
    pathCenters = "/sample/0/plate/"+plaque+"/experiment/"+puits[:-3]+"/position/"+puits[-1]+"/feature/{}/center".format(name_primary_channel)
    pathOrientation = "/sample/0/plate/"+plaque+"/experiment/"+puits[:-3]+"/position/"+puits[-1]+"/feature/{}/orientation".format(name_primary_channel)
    #not loading segmentation nor raw data since we only use the features that are computed by Cell Cognition
    #print pathObjects, filename
    tabObjects = vi.readHDF5(filename, pathObjects)
    tabFeatures = vi.readHDF5(filename, pathFeatures)
    tabCenters = vi.readHDF5(filename, pathCenters)
    
    if secondary:
        pathSecondaryObjects = "/sample/0/plate/"+plaque+"/experiment/"+puits[:-3]+"/position/"+puits[-1]+"/object/secondary__propagate"
        pathSecondaryFeatures = "/sample/0/plate/"+plaque+"/experiment/"+puits[:-3]+"/position/"+puits[-1]+"/feature/secondary__propagate/object_features"
        
        tabSecondaryObjects =vi.readHDF5(filename, pathSecondaryObjects)
        if len(tabSecondaryObjects)!=len(tabObjects):
            raise
        tabSecondaryFeatures = vi.readHDF5(filename, pathSecondaryFeatures)
    
    if int(tabFeatures.shape[1])!=FEATURE_NUMBER:
        raise FeatureException('There is a problem with the size of features array')
#this to deal with hdf5 files where the frames are not in the chronological order
    frameList = np.array(tabObjects, dtype=int)
    frameNumber = np.max(frameList)+1#otherwise we forget the last frame
    frameLot = frameLots()
    
    for i in range(frameNumber):
        if frames_to_skip is not None and i in frames_to_skip:
            print "##########################################################Skipping frame {}".format(i)
            continue
        elif frames_to_skip is not None:
            new_frame_number=i-len(np.where(frames_to_skip<i)[0])
        else:
            new_frame_number=i

        try:
            cellsF = cells(i, frameList, tabObjects)
        except IndexError:
            sys.stderr.write('WARNING no frame {}, p {}, w {} \n'.format(i, plaque, puits))
            continue
        featuresF=tabFeatures[cellsF.firstLine():cellsF.lastLine()+1]
        centersF = tabCenters[cellsF.firstLine():cellsF.lastLine()+1]
        orientationF = tabOrientation[cellsF.firstLine():cellsF.lastLine()+1] if not old else np.zeros(shape=(cellsF.lastLine()+1-cellsF.firstLine(),2))
        
        if secondary:
            secondaryFeaturesF = tabSecondaryFeatures[cellsF.firstLine():cellsF.lastLine()+1]
            featuresF = np.hstack((featuresF, secondaryFeaturesF))
        
        newFrame = frame(plaque, puits, new_frame_number, #tabSeg[0][i][0][:][:], tabRaw[0][i][0][:][:],
                          cellsF, centersF, featuresF, orientationF)

        frameLot.append(newFrame)
        
    return frameLot, tabFeatures

class cell():
    def __init__(self, plate, well, index, label, center, features, centers=None, orientation = None):
        global compteur
        self.plate = plate
        self.well = well
        self.index = index
        self.label=label
        self.center=(center[0], center[1])
        self.features = features
        self.inTraining = False
        self.fr=None
        self.to=None
        compteur+=1
        self.centers = centers
        self.orientation = orientation #[angle, eccentricity]    
#        print "une nouvelle cellule"

    def findFrom(self, lstCellsF):
        plate = self.plate
        well = self.well
        index = self.index
        result = None
        trouve = 0
        for size in range(6):
            lstCellsFLocal = lstCellsF[size]

            if (plate in lstCellsFLocal) and (well in lstCellsFLocal[plate]) and (index in lstCellsFLocal[plate][well]):
                if self.label in lstCellsFLocal[plate][well][index]:
                        result = size
                        trouve+=1
#                        print "la cellule vient de", result, index, self.label
        
        if result == None:
            print "pas trouve de from pour la cellule", self.label, "a l'image ", index
        if trouve>1:
            raise MoreThanOneException(self.label)
        return result

class cells():
    def __init__(self, frame, frameList, tabObjects):
 #       self.cellLines = {}
        where_=np.where(frameList==frame)
        beginFrame = where_[0][0]
        endFrame = where_[0][-1]
        self.cellLines={tabObjects[k][1]:k for k in range(beginFrame, endFrame+1)}

###PLUS ELEGANT MAIS PLUS LENT
##        dict_={el[1]:np.where(tabObjects==el)[0][0] for el in filter(lambda x: x[0]==frame, tabObjects)}    
            
    def __getitem__(self, label):
        return self.cellLines[label]

            
    def cellNumber(self):
        return len(self.cellLines)
    
    def firstLine(self):
        return min(self.cellLines.values())
    
    def lastLine(self):
        return max(self.cellLines.values())
        
        

class frame():
    def __init__(self, plate, well, index, labels, centers, features, orientation,classification=None, secondary=False):
        self.plate = plate
        self.well = well
        self.index = index
#        self.segmentation = segmentation
#        self.raw = rawInfo
        self.labels = labels
        self.centers = centers
        self.features=features
        self.orientation = orientation
        self.source = []
        self.target = []
    #in case the nuclei have been segmented
        self.classification=classification
    #saving if anything has been processed on the second channel
        self.secondary=secondary
        
    def getFeatures(self, label):
        try:
            line = self.labels[label]
        except KeyError:
            print "KeyError", self.index, label
            return None
        else:
#            print line, label
            firstLine = self.labels.firstLine()
            line-=firstLine
            
            center = self.centers[line]
            features = self.features[line]
            orientation = self.orientation[line]
            ori = [orientation[0], orientation[1]]
            return cell(self.plate, self.well, self.index, label, center, features, centers=None, orientation = ori)
        
    def getCenter(self, label):
        try:
            line = self.labels[label]
        except KeyError:
            print "KeyError", self.index, label
            return None
        else:
#            print line, label
            firstLine = self.labels.firstLine()
            line-=firstLine
            
            return self.centers[line]
     
    def getAllSinglets(self):
        result =[]
        labelsC = self.labels.cellLines.keys()
        for label in labelsC:
            result.append(self.getFeatures(label))  
        return result
        
    def distToBorder(self, label):
        #verifier sur un autre exemple que cela marche bien
        dmin = 10000
        print self.segmentation.shape
        xmax = XMAX
        ymax = YMAX
#        xmax = self.segmentation.shape[0]
#        ymax = self.segmentation.shape[1]
        for i in range(xmax):
            for j in range(ymax):
                if self.segmentation[i][j]==label:
                    d = min(i, j, xmax-i, ymax-j)
                    if d<dmin:
                        dmin=d
        print self.index, label, dmin
        return dmin
                    
    def addTraining2(self, solC):
        for e in solC:
            source = solC[e][0]
            target = solC[e][1]
            for c in source:
                self.source.append(c)
            for c in target:
                self.target.append(c)
        #print "training set : source, target :", self.source, self.target
    
    def statisticsTraining2(self):
        count = [0,0,0,0,0,0]
        i=0
        for listLabelS in self.source:
            listLabelT = self.target[i]
            if listLabelT == [-1]:
                cnt=0
            else:
                cnt = len(listLabelT)
            i+=1
            
            count[cnt]+=len(listLabelS)

        return count
    
    def clean(self, f):
        self.features = np.delete(self.features, f, 1)
        
    def zeros(self, toZeros):
        for col in toZeros:
            self.features[:,col]=0
        #print self.features.shape
        
        
class frameLots():
    def __init__(self):
        self.numFrames = 0
        self.lstFrames = {}
        
    def append(self, newFrame):
        plate = newFrame.plate
        well = newFrame.well
        index = newFrame.index
        if plate not in self.lstFrames:
            self.lstFrames[plate]={}
        if well not in self.lstFrames[plate]:
            self.lstFrames[plate][well]={}
            
        self.lstFrames[plate][well][index]=newFrame
        self.numFrames+=1
        
    def addFrameLot(self, newFrameLot):
        #print "avant : numFrames"+str(self.numFrames)+" len(lstFrames) "+str(len(self.lstFrames))
        self.numFrames += newFrameLot.numFrames
        for plate in newFrameLot.lstFrames:
            if plate in self.lstFrames:
                self.lstFrames[plate].update(newFrameLot.lstFrames[plate])
            else:
                self.lstFrames[plate]=newFrameLot.lstFrames[plate]
#        self.lstFrames.update(newFrameLot.lstFrames)
        #print "apres : numFrames"+str(self.numFrames)+" len(lstFrames) "+str(len(self.lstFrames))
        
        
    def addTraining2(self, filename, filenameT):
        plateT =filenameT[-34:-25]
        wellT = filenameT[-21:-13]
        global LENGTH
        print plateT, wellT
        tab = importSegOnly(filename, plateT, wellT)
        LENGTH = tab.shape[1]-1
        
        ensembleTraj = fHacktrack_reverse_vigra_saving.lireTrajectoires(filenameT, tab)
        fileToSave =  ("%s_P%s.txt" % (plateT, wellT))
        #fileToSave=sauvegarde+fileToSave
        solutions = fHacktrack_reverse_vigra_saving.ecrireTrainingSansHDF5(ensembleTraj, fileToSave, LENGTH)
        try:
            framesP = self.lstFrames[plateT]
        except KeyError:
            print "attention, les raw data etc. ne sont pas presentes (plate)"
        else:
            try:
                framesI = framesP[wellT]
            except KeyError:
                print "attention, les raw data etc. ne sont pas presentes (well)"
            else:
                lstIndexT = solutions.keys()
                lstIndexD = framesI.keys()
                for indexT in lstIndexT:
                    indexT = int(indexT)
                    if indexT not in lstIndexD:
                        print "attention, pas de raw data etc pour l'image "+str(indexT)
                    else:
#                        print "ajout du training pour ", plateT, wellT, indexT
                        frameC = framesI[indexT]
                        frameC.addTraining2(solutions[indexT])
    
    def statisticsTraining2(self):
        count = [0,0,0,0,0,0]
        total=0
        for plate in self.lstFrames:
            for well in self.lstFrames[plate]:
                for index in self.lstFrames[plate][well]:
                    frame = self.lstFrames[plate][well][index]
                    countF = frame.statisticsTraining2()
                    for i in range(6):
                        count[i]+=countF[i]
                        
        for i in count:
            total+=i

        return count, total

    def clean(self, f):
        for plate in self.lstFrames:
            for well in self.lstFrames[plate]:
                for index in self.lstFrames[plate][well]:
                    self.lstFrames[plate][well][index].clean(f)
        return 1
    
    def zeros(self, toZeros):
        for plate in self.lstFrames:
            for well in self.lstFrames[plate]:
                for index in self.lstFrames[plate][well]:
                    self.lstFrames[plate][well][index].zeros(toZeros)
        return 1
            
    def getTraining2(self):
        print self.lstFrames.keys()
        global compteur
        compteur = 0
        lstCellsT=[]
        lstCellsF =dict(zip(range(6), [{} for x in range(6)]))
        for plate in self.lstFrames:
            print "training set loading", plate
            for well in self.lstFrames[plate]:
                print well
                for index in self.lstFrames[plate][well]:
                    #print index
                    frame = self.lstFrames[plate][well][index]
                    i=0
                    for listLabelS in frame.source:
                        listLabelT = frame.target[i]

                        if listLabelS == [-1] or listLabelT == [-1]:
                            coming = None
                            fr = None
                        elif len(listLabelS)==1:
                            if len(listLabelT)==1:
                                coming = 1
                                fr = 1
                                addFrom(fr, plate, well, index+1, listLabelT, lstCellsF)
                            elif len(listLabelT)>1:
                                coming = 2
                                fr=2
                                addFrom(fr, plate, well, index+1, listLabelT, lstCellsF)
                        elif len(listLabelS)>1:
                            coming = 3
                            fr = 3
                            addFrom(fr, plate, well, index+1, listLabelT, lstCellsF)
                        else:
                            raise TrainingException               
                        
                        for label in listLabelS:
#                            nex = tabT.bindAxis('c', i)
#                            t = to(label) 
                            cellC = None
                            if int(label)!=-1:
                                cellC = frame.getFeatures(label)
                            if cellC is not None:
                                compteur+=1
                                cellC.inTraining = True
                                cellC.to = coming
                                lstCellsT.append(cellC)
                        i+=1


        for cell in lstCellsT:
            if cell.index >0:
                cell.fr = cell.findFrom(lstCellsF)

        X=None
        Xz = None
        Y=[]
        Z=[]
        print "appending TO and FROM data"
        for cell in lstCellsT:
            if cell.to is not None:
                Y.append(cell.to)
#                if int(cell.to)==1:
#                    Y.append(1)
#                else :
#                    Y.append(0)
                if X==None:
                    X = cell.features
                else:
                    X=np.vstack((X, cell.features))
                
            
            if cell.fr is not None:
                Z.append(cell.fr)
#                if int(cell.fr)==1:
#                    Z.append(1)
#                else:
#                    Z.append(0)
                if Xz==None:
                    Xz = cell.features
                else:
                    Xz=np.vstack((Xz, cell.features))
        print "compteur de la creation de cellules ", compteur
        return lstCellsT, lstCellsF, X, Y, Xz, Z
            
    def getTrainingUplets(self, outputFolder):
        print self.lstFrames.keys()
        global compteur
        compteur = 0
        singlets = {}
        doublets = {}
#        lstCellsF =dict(zip(range(6), [{} for x in range(6)]))
        for plate in self.lstFrames:
            print "Uplets loading", plate
            if plate not in singlets:
                singlets[plate]={}
            if plate not in doublets:
                doublets[plate]={}
            for well in self.lstFrames[plate]:
                print well
                if well not in singlets[plate]:
                    singlets[plate][well]={}
                if well not in doublets[plate]:
                    doublets[plate][well]={}
                centersDict = {}
                for index in self.lstFrames[plate][well]:
                    print '-- ',
                    if index not in singlets[plate][well]:
                        singlets[plate][well].update({index:[cell(plate, well, index, -1, (XMAX, YMAX), [])]})
                        #[index]=[]
                    if index not in doublets[plate][well]:
                        doublets[plate][well][index]=[]
                        
                    singletsL = singlets[plate][well][index]
                    
                    frame = self.lstFrames[plate][well][index]
                    
                    i=0
                    for listLabelS in frame.source:
                        listLabelT = frame.target[i]
                        listLabelT.sort(); listLabelS.sort()
                    
                        for label in listLabelS:
                            cellC = None
                            if int(label)!=-1:
                                cellC = frame.getFeatures(label)
                                
                                if cellC is not None:
                                    #compteur+=1
                                    cellC.inTraining = True
                                    cellC.to = tuple(listLabelT)
                                    cellC.fr = tuple( listLabelS)
                                    singletsL.append(cellC)
                            else:
                                cellC = filter(lambda x : x.label ==-1 , singletsL)[0]
                                cellC.inTraining = True
                                if cellC.to is None:
                                    cellC.to = listLabelT
                                else:
                                    cellC.to.extend(listLabelT)
                        i+=1
                    
                    #print "je calcule les doublets"

                    lCenters = []
                    for sing in filter(lambda x: x.label !=-1,singletsL):
                        lCenters.append(sing.center)
                    doubs = {}; trips = {}
                    if len(lCenters)<=1:
                        continue
                    treeC = ssp.cKDTree(lCenters, leafsize = 10)
                    centersDict[index]=np.array(lCenters)
                    
                    j = 0
                    for sing in filter(lambda x: x.label !=-1,singletsL):
                        d, i = treeC.query(sing.center, k+1, distance_upper_bound = dmax)
                        for couple in filter(lambda x: x[1]<100 and x[1]>0, zip(i,d)):
                            if couple[0]>j:
                                ll = singletsL[j+1].label
                                if ll not in doubs:
                                    doubs[ll]=[]
                                doubs[ll].append(singletsL[couple[0]+1].label)
                        #d donne les distances et i l'index dans la liste
                        if singletsL[j+1].label in doubs: doubs[ll].sort()
                        j+=1
                    
                    #doubs2 = joining.nearest_neighbors(frame, k, dmax, training_only=False)
                    #pdb.set_trace()
                    #print "je calcule les triplets"
#                    pdb.set_trace()
                    for sing1 in doubs.keys():
                        try:
                            d1 = doubs[sing1]
                        except KeyError:
                            continue
                        else:
                            for sing2 in d1:
                                try:
                                    d2 = doubs[sing2]
                                except KeyError:
                                    continue
                                else:
                                    for sing3 in filter(lambda x: x in d1, d2):
                                        if sing1 not in trips:
                                            trips[sing1]=[]
                                        trips[sing1].append((sing2, sing3))                  

                    for cellule in filter(lambda x: x.label !=-1,singletsL):
                        #print "premiere cellule", cellule.label, cellule.center
        #DOUBLETS
                        if cellule.label not in doubs:
                            continue
                        for doub in doubs[cellule.label]:
                            autre = singletsL[ filter(lambda x: singletsL[x].label == doub, range(len(singletsL)))[0]]
                            if autre.label != doub:
                                raise DoubletsException
                            lll = (cellule.label, doub)
                            if cellule.label>autre.label:
                                lll = (doub,cellule.label)
                            
                            #print "seconde cellule", doub, autre.center
#                            print autre.label, autre.center
                            c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1]))
                            centers=(c1,c2)
#                            print type(c1), c1, c1.shape
                            #print "moyenne des cntres", np.mean((c1, c2), 0)
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index, lll, np.mean((c1, c2), 0), np.mean((cellule.features, autre.features),0), centers)#def __init__(self, plate, well, index, label, center, features):
                            multiplet.inTraining = True
                            doublets[plate][well][index].append(multiplet)
#        #TRIPLETS          
                        if cellule.label not in trips:
                            continue
                       
                        for trip in trips[cellule.label]:
                            autre = singletsL[ filter(lambda x: singletsL[x].label == trip[0], range(len(singletsL)))[0]]
                            autre2 = singletsL[ filter(lambda x: singletsL[x].label == trip[1], range(len(singletsL)))[0]]
                            
                            if autre.label != trip[0] or autre2.label != trip[1]:
                                raise DoubletsException
                            
                            l1 = min(cellule.label, autre.label, autre2.label)
                            l3 = max(cellule.label, autre.label, autre2.label)
                            l2 = filter(lambda x: x not in [l1, l3], (cellule.label, autre.label, autre2.label))[0]
#                                    if not cellule.label<autre.label<autre2.label:
#                                        raise
                            #print "seconde cellule", doub, autre.center
#                            print autre.label, autre.center
                            c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1])) ; c3 = np.array((autre2.center[0], autre2.center[1]))
                            centers = (c1, c2, c3)
#                            print type(c1), c1, c1.shape
                            #print "moyenne des cntres", np.mean((c1, c2), 0)
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index, (l1, l2, l3), np.mean((c1, c2, c3), 0), np.mean((cellule.features, autre.features, autre2.features),0), centers)#def __init__(self, plate, well, index, label, center, features):
                            multiplet.inTraining = True
                    #JE LES AJOUTE A LA LISTE DES DOUBLETS
                            doublets[plate][well][index].append(multiplet)
            savingCenters(plate, well, outputFolder, centersDict)  
        
        for plate in singlets:
            print plate
            for well in singlets[plate]:
                print well
                for index in singlets[plate][well]:
                    print "-- ",

                    if index+1 not in singlets[plate][well] or len(singlets[plate][well][index+1])==1:
                        continue
                    nextSinglets = singlets[plate][well][index+1]
                    nextDoublets = doublets[plate][well][index+1]
        #                    print "SINGLETS COURANTS"
        #                    for c in singlets[plate][well][index]:
        #                        print c.label 
        #                    print "NEXT SINGLETS"
        #                    for c2 in nextSinglets:
        #                        print c2.label
                    merge = {}#;cen = {}
                    for singlet in singlets[plate][well][index]:
            #ON EST A T = INDEX
                        #print "DE :", singlet.label, "A ", singlet.to
              #REGARDONS LES MERGE A T      
                        try:
                            if len(singlet.fr)>1:
                                print "entre les merges"
                                net = filter(lambda x: nextSinglets[x].label == singlet.to[0], range(len(nextSinglets)))[0]
                                if nextSinglets[net].label not in merge:
                                    merge[nextSinglets[net].label]=[]
                                    #cen.update({nextSinglets[net].label : nextSinglets[net].center})
                                merge[nextSinglets[net].label].append(singlet)
                        except TypeError:
                            if singlet.label !=-1:
                                print "singlet ", singlet.label, "n'a pas de fr initialise"
                #REGARDONS LES SPLITS A T
                        try:
                            if singlet.label!=-1 and len(singlet.to)>1:
                                tt=filter(lambda x: nextDoublets[x].label == singlet.to, range(len(nextDoublets)))[0]
                                #print "split"
                                #print "ce doublet est bien dans nextDoublets :", filter(lambda x: nextDoublets[x].label == singlet.to, range(len(nextDoublets)))[0]
#                        except TypeError: en fait on ne devrait pas arriver la pcq tlm dt avoir .to initialise sf eventuellement -1
#                            print "donc la ca veut dire que singlet.to n'est pas initialise, check"
#                            #pdb.set_trace()
                        except IndexError:
                            print "ce doublet n'est pas dans nextDoublets, je l'ajoute"
                            #pdb.set_trace()
                            l = len(singlet.to)
                            c = np.empty(shape = (l, 2))
                            f = np.empty(shape = (l, singlet.features.shape[0]))
                            i=0
                            #pdb.set_trace()
                            for labelCou in singlet.to:
                                celluleCou = filter(lambda x: x.label == labelCou, nextSinglets)[0]
                                c[i] = celluleCou.center
                                f[i]= celluleCou.features.copy()
                                i+=1
                            print c
                            moy = tuple(np.mean(c, 0))
                            centers = tuple(c)
                            #c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1]))
#                            print type(c1), c1, c1.shape
                            print "moyenne des cntres", moy
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index+1, singlet.to, moy, np.mean(f,0), centers)#def __init__(self, plate, well, index, label, center, features):
                            multiplet.fr = (singlet.label,)
                            multiplet.inTraining=True
                            nextDoublets.append(multiplet)
                        
                    doubletsL = doublets[plate][well][index]
                    for l in merge:
                        source = [x.label for x in merge[l]]
                        source.sort()
                        source=tuple(source)
                        print source
                        
                        try:
                            doubs = filter(lambda x : x.label == source, doubletsL)[0]
                            print doubs.label
                        except IndexError:
                            print "ce doublet n'est pas dans la liste de doublets, je l'ajoute", source
                            c = np.empty(shape = (len(merge[l]), 2))
                            f = np.empty(shape = (len(merge[l]), merge[l][0].features.shape[0]))
                            i=0
                            #pdb.set_trace()
                            for cellule in merge[l]:
                                cellule.to = None
                                c[i] = cellule.center
                                f[i]= cellule.features.copy()
                                i+=1
                            print c#marche pas
                            moy = tuple(np.mean(c, 0))
                            centers=tuple(c)
                            #c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1]))
#                            print type(c1), c1, c1.shape
                            print "moyenne des cntres", moy
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index, source, moy, np.mean(f,0), centers)#def __init__(self, plate, well, index, label, center, features):
                            multiplet.to = (l,)
                            multiplet.inTraining = True
                            doubletsL.append(multiplet)
                        else:
                            print "doublets de merge : ", doubs.label, "vers", l, "et j'enleve cela des singlets.to"
                            doubs.to = (l,)
                            for cellule in merge[l]:
                                cellule.to = None
                                cellule.inTraining = False

        return singlets, doublets

    def getAllUplets(self, outputFolder=None):
        global compteur
        singlets = {}
        doublets = {}
        for plate in self.lstFrames:
            print "Uplets loading", plate
            if plate not in singlets:
                singlets[plate]={}
            if plate not in doublets:
                doublets[plate]={}
                
            for well in self.lstFrames[plate]:
                print well
                centersDict = {}
                if well not in singlets[plate]:
                    singlets[plate][well]={}
                if well not in doublets[plate]:
                    doublets[plate][well]={}
                
                for index in self.lstFrames[plate][well]:
                    if index not in singlets[plate][well]:
                        singlets[plate][well].update({index:[cell(plate, well, index, -1, (XMAX, YMAX), [])]})
                        #[index]=[]
                    if index not in doublets[plate][well]:
                        doublets[plate][well][index]=[]
                    
                    frame = self.lstFrames[plate][well][index]
                    allSinglets = frame.getAllSinglets()
                    length = len(allSinglets)
                    compteur+=length
                    singlets[plate][well][index].extend(allSinglets)
                    singletsL = singlets[plate][well][index]

                    #print "je calcule les doublets"
                    
                    lCenters = [sing.center for sing in filter(lambda x: x.label !=-1,singletsL)]

                    doubs = {}; trips = {}
                    treeC = ssp.cKDTree(lCenters, leafsize = 10)
                    centersDict[index]=np.array(lCenters)
                    
#                    singletsL.sort(key=(lambda x:x.label))
#                    print [sing.label for sing in singletsL]
                    j = 0
                    for sing in filter(lambda x: x.label !=-1,singletsL):
                        d, i = treeC.query(sing.center, k+1, distance_upper_bound = dmax)
                        for couple in filter(lambda x: x[1]<100 and x[1]>0, zip(i,d)):
                            if couple[0]>j:
                                ll = singletsL[j+1].label
                                if ll not in doubs:
                                    doubs[ll]=[]
                                doubs[ll].append(singletsL[couple[0]+1].label)
                        #d donne les distances et i l'index dans la liste
                        if singletsL[j+1].label in doubs: doubs[ll].sort()
                        j+=1
                    
                    for sing1 in doubs.keys():
                        try:
                            d1 = doubs[sing1]
                        except KeyError:
                            continue
                        else:
                            for sing2 in d1:
                                try:
                                    d2 = doubs[sing2]
                                except KeyError:
                                    continue
                                else:
                                    for sing3 in filter(lambda x: x in d1, d2):
                                        if sing1 not in trips:
                                            trips[sing1]=[]
                                        trips[sing1].append((sing2, sing3))    
                    for cellule in filter(lambda x: x.label !=-1,singletsL):
                        #print "premiere cellule", cellule.label, cellule.center
        #DOUBLETS
                        if cellule.label not in doubs:
                            continue
                        for doub in doubs[cellule.label]:
                            autre = singletsL[ filter(lambda x: singletsL[x].label == doub, range(len(singletsL)))[0]]
                            if autre.label != doub:
                                raise DoubletsException
                            
                            if singletsL.index(cellule)>singletsL.index(autre):
                                pdb.set_trace()
                                raise DoubletsException
                            
                            #print "seconde cellule", doub, autre.center
#                            print autre.label, autre.center
                            c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1]))
                            centers=(c1,c2)
#                            print type(c1), c1, c1.shape
                            #print "moyenne des cntres", np.mean((c1, c2), 0)
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index, (cellule.label, doub), np.mean((c1, c2), 0), np.mean((cellule.features, autre.features),0), centers)#def __init__(self, plate, well, index, label, center, features):
                            doublets[plate][well][index].append(multiplet)
        #TRIPLETS       
                        if cellule.label not in trips:
                            continue             
                        for trip in trips[cellule.label]:
                            #import pdb ; pdb.set_trace()
                            autre = singletsL[ filter(lambda x: singletsL[x].label == trip[0], range(len(singletsL)))[0]]
                            autre2 = singletsL[ filter(lambda x: singletsL[x].label == trip[1], range(len(singletsL)))[0]]
                            
                            if autre.label != trip[0] or autre2.label != trip[1]:
                                raise DoubletsException
                            if not singletsL.index(cellule)<singletsL.index(autre)<singletsL.index(autre2):
                                raise DoubletsException
                            #print "seconde cellule", doub, autre.center
#                            print autre.label, autre.center
                            c1 = np.array((cellule.center[0], cellule.center[1])); c2 = np.array((autre.center[0], autre.center[1])) ; c3 = np.array((autre2.center[0], autre2.center[1]))
                            centers=(c1,c2, c3)
#                            print type(c1), c1, c1.shape
                            #print "moyenne des cntres", np.mean((c1, c2), 0)
                            #print np.mean((cellule.features, autre.features),0).shape
                            multiplet= cell(plate, well, index, (cellule.label, trip[0], trip[1]), np.mean((c1, c2, c3), 0), np.mean((cellule.features, autre.features, autre2.features),0), centers)#def __init__(self, plate, well, index, label, center, features):
                    #JE LES AJOUTE A LA LISTE DES DOUBLETS
                            doublets[plate][well][index].append(multiplet)
                savingCenters(plate, well, outputFolder, centersDict)        
        return singlets, doublets

def savingCenters(plate, well, outputFolder, centersDict):
    if outputFolder is not None:
        try:
            f=open(os.path.join(outputFolder, 'centers_P{}_w{}.pkl'.format(plate, well)), 'w')
            pickle.dump(centersDict,f)
            f.close()
        except IOError:
            sys.stderr.write("Saving centers for plate {}, well {} failed".format(plate, well))
            sys.exit()
    return 1


def calculDistances(singlets):        
    dmoy = []
    dmoySplit = [[], [], []]
    dmoySplit2=[]
    count = 0
    countSplit = 0
    dmoyMerge=[[],[],[]]
    dmoyMerge2=[]
    countMerge = 0;count2=0
    for plate in singlets:
        print plate
        for well in singlets[plate]:
            print well
            for index in singlets[plate][well]:
                print "INDEX", index
                if index+1 not in singlets[plate][well] or len(singlets[plate][well][index+1])==1:#c'est bien un parce qu'il y a toujours le singlet -1
                    continue
                nextSinglets = singlets[plate][well][index+1]
                #print len(nextSinglets)
#                    print "SINGLETS COURANTS"
#                    for c in singlets[plate][well][index]:
#                        print c.label 
#                    print "NEXT SINGLETS"
#                    for c2 in nextSinglets:
#                        print c2.label
                dist_merge = {};cen = {}
                for singlet in filter(lambda x: x.label !=-1,singlets[plate][well][index]):
                    print "DE :", singlet.label, "A ", singlet.to
                    
                    if len(singlet.fr)>3:
                        continue
                    elif len(singlet.fr)>1:
                        print "calcul dist entre les merges"
                        net = filter(lambda x: nextSinglets[x].label == singlet.to[0], range(len(nextSinglets)))[0]
                        if nextSinglets[net].label not in dist_merge:
                            dist_merge[nextSinglets[net].label]=[]
                            cen.update({nextSinglets[net].label : nextSinglets[net].center})
                        dist_merge[nextSinglets[net].label].append(singlet.center)
                        countMerge+=1
                    
                    elif len(singlet.to)==1 and singlet.to != (-1,):
                        net = filter(lambda x: nextSinglets[x].label == singlet.to[0], range(len(nextSinglets)))[0]#c'est donc un indice
                        
                        dmoy.extend(dist([singlet.center, nextSinglets[net].center]))
                        count+=1
                        print "calcul dist simple"
                    elif singlet.to != (-1,) and len(singlet.to)<4:
                        centers = []
                        print "calcul dist entre les splits"
                        for l in singlet.to:
                            indice = filter(lambda x: nextSinglets[x].label == l, range(len(nextSinglets)))[0]
                            centers.append(nextSinglets[indice].center)
                        centersM = moyMultipleCenters(centers)
                        dmoySplit2.extend(dist([centersM, singlet.center]))
                        dmoySplit[len(centers)-2].extend(dist(centers))
                        countSplit +=1
                
                for label in dist_merge:
                    taille = len(dist_merge[label])
                    print taille
                    dmoyMerge[taille-2].extend(dist(dist_merge[label]))
                    centersM2 = moyMultipleCenters(dist_merge[label])
                    dmoyMerge2.extend(dist([centersM2, cen[label]]))
                    count2+=1
                        
#        dmoy=float(dmoy)/count
#        dmoySplit = float(dmoySplit)/countSplit
#        dmoyMerge = float(dmoyMerge)/count2
    print np.mean(dmoy), np.mean(dmoySplit2), np.mean(dmoyMerge2)
    print np.std(dmoy), np.std(dmoySplit2), np.std(dmoyMerge2)

    #import pdb ; pdb.set_trace()
    for i in range(len(dmoySplit)):
        print "moyenne pour les splits de taille",i, " ", np.mean(np.array(dmoySplit)[i], 0)
        print "std pour les splits de taille",i, " ", np.std(np.array(dmoySplit)[i], 0)
        print "moyenne pour les merges de taille",i, " ", np.mean(np.array(dmoyMerge)[i], 0)
        print "std pour les merges de taille",i, " ", np.std(np.array(dmoyMerge)[i], 0)
#FIXME marche pas 
    print count, countSplit, countMerge
    dmoy.sort(); dmoyMerge.sort() ; dmoyMerge2.sort() ; dmoySplit.sort() ; dmoySplit2.sort()
    p.scatter(range(len(dmoy)), dmoy, marker='^', hold='on')
    p.xlabel('Number of occurences')
    p.ylabel("Distance between consecutive frames, moves")
    p.title('Training set size :'+str(compteur)+" objects")
    p.grid(True)
    p.show()
    
    p.scatter(range(len(dmoySplit2)), dmoySplit2, marker='o', color = 'red', hold='on')
    p.scatter(range(len(dmoyMerge2)), dmoyMerge2, marker='*')
    p.xlabel('Number of occurences')
    p.ylabel("Distance between consecutive frames, merges and splits")
    p.title('Training set size :'+str(compteur)+" objects")
    p.grid(True)
    p.show()
    
class TrainingException(Exception):
    def __init__(self):
        print "Problem as building the training set from training set files", sys.exc_info()
        pass

class DoubletsException(Exception):
    def __init__(self):
        print "Problem as finding uplets", sys.exc_info()
        pass
