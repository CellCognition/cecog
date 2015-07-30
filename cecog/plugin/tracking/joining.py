import numpy as np
from math import sqrt, fabs, pi
from scipy import spatial
from itertools import combinations
import pdb, sys
from tracking.importPack import EVENTS, SIZES,k, d_bf_move, d_bf_more, XMAX, YMAX#, FEATURE_NUMBER

compteur = [0,0]

def angle(center, centersTuple):
    l=len(centersTuple)
    u=[]; angles=[]
    for k in range(l):
        u.append((centersTuple[k][0]-center[0], centersTuple[k][1]-center[1]))
        
    for v1, v2 in combinations(u, 2):
        n=sqrt(v1[0]**2+v1[1]**2)*sqrt(v2[0]**2+v2[1]**2)

#BON DONC ici il faut regler 
#1. le cas n==0 : que mettre => regarder la distribution de l'angle pour les vrais splits et mettre qqch d'improbable (oui ms si c'est un vrai split ?)
#2. le cas ou il y a une imprecision numerique =>

#je remarque que cet attribut ne vaut NaN que pour les fois ou l'hypothese est fausse. L'attribut a une valeur aleatoire : moy 1.48, std dev 0.83
#alors que pour les fois ou l'hypothese est vraie il a une valeur moy 2.59, std dev 0.49. Donc il suffit de mettre les NaN a 0.7
#Apres discussion avec Thomas on decide finalement de le mettre a zero
        zz= np.arccos(np.dot(v1,v2)/n)
        if not np.isnan(zz):
            angles.append(zz)
        else:
            angles.append(0)
    if l==2:
        return angles[0]
    else:
        m = max(angles)
        angles = filter(lambda x: x<m, angles)
        if angles==[]: return m
        return np.mean(angles) 
    
def angle_N(center, centersTuple):
    l=len(centersTuple)
    u=[]; angles=[]
    for k in range(l):
        u.append((centersTuple[k][0]-center[0], centersTuple[k][1]-center[1]))
        
    for v1, v2 in combinations(u, 2):
        n=sqrt(v1[0]**2+v1[1]**2)*sqrt(v2[0]**2+v2[1]**2)
        zz= np.arccos(np.dot(v1,v2)/n)
        angles.append(zz)

    if l==2:
        return angles[0]
    else:
        m = max(angles)
        angles = filter(lambda x: x<m, angles)
        return np.mean(angles) 


#a partir du dictionnaire retourne par nn, la fonction formule les hypotheses dans une liste or whatever sous la forme (tuple id source,
# tuple id target)
def transformToHyp(dictionary):
    hyp = []
    for label in dictionary:
        #print label
        for target in dictionary[label]:
            hyp.append((label, target))
    
    #pour que les hypotheses soient dans un ordre bien determine et inchangeable
    result = tuple(hyp)
    #print result
    return result


#retourne l'index de l'objet avec le label s dans la liste SingletsL
def ind(singletsL, s):
    r = filter(lambda x: x.label == s, singletsL)
    if len(r)>1:
        print s, r
        raise MoreThanOneException(s)
    if len(r)==0:
        sprim = list(s); sprim.sort()
        r = filter(lambda x: x.label == tuple(sprim), singletsL)
        
    return singletsL.index(r[0])

def constraints(t, t1, t2, singletsL, nextSinglets):
    len_hyp = len(t)
    constraints_arr = np.zeros(shape = (t1+t2, len_hyp))
    
    if singletsL == None:
        for l in range(len_hyp):
            #print t[l]
            s2 = t[l][1]
            j = ind(nextSinglets, s2)
            #print s2, j
            constraints_arr[t1+j][l]=1
        
    elif nextSinglets == None:
        for l in range(len_hyp):
            #print t[l]
            s = t[l][0]
            i = ind(singletsL, s)
            #print s, i #son id est sa place dans la liste de singlets
            constraints_arr[i][l]=1
        
    else:
        for l in range(len_hyp):
            #print t[l]
            if type(t[l][0])==tuple:
                
                for s in t[l][0]:
                    i = ind(singletsL, s)
             #       print s, i #son id est sa place dans la liste de singlets
                    constraints_arr[i][l]=1
            else:
                s = t[l][0]
                i = ind(singletsL, s)
              #  print s, i #son id est sa place dans la liste de singlets
                constraints_arr[i][l]=1
            if type(t[l][1])==tuple:
                for s2 in t[l][1]:
                    j = ind(nextSinglets, s2)
               #     print s2, j
                    constraints_arr[t1+j][l]=1
            else:
                s2 = t[l][1]
                j = ind(nextSinglets, s2)
                #print s2, j
                constraints_arr[t1+j][l]=1
    #print constraints_arr        
    return constraints_arr

def features(t, singletsL, nextSinglets, split=False, move = False):
    global FEATURE_NUMBER
    #pour l'instant on fait une distance dans l'espace des features
    len_hyp = len(t) ; taille_feat = FEATURE_NUMBER
    distances = np.zeros(shape=(len_hyp, 1))
    angles = np.zeros(shape=(len_hyp, 1))
    
#pour les app et dis on prend uniquement les features resp de l'arrivee et du depart =>
#pas de differences, donc les features sont beaucoup plus grosses :/    
    
    if singletsL==None:
        #taille_feat = nextSinglets[1].features.shape[0]
        feat_arr = np.empty(shape=(len_hyp, taille_feat))
        
        for l in range(len_hyp):
            #print t[l]
            s2 = t[l][1]
            j = ind(nextSinglets, s2)
            #print s2, j
            #print "feat[0]",nextSinglets[j].features
            feat_arr[l]=-np.copy(nextSinglets[j].features)
            #.copy()
            distances[l]=min(nextSinglets[j].center[0], nextSinglets[j].center[1], np.fabs(nextSinglets[j].center[0] - YMAX), 
                             np.fabs(nextSinglets[j].center[1] - XMAX))
            
    elif nextSinglets == None:
        #taille_feat = singletsL[1].features.shape[0]
        feat_arr = np.empty(shape=(len_hyp, taille_feat))
        for l in range(len_hyp):
            #print t[l]
    
            s = t[l][0]
            i = ind(singletsL, s)
            #print s, i #son id est sa place dans la liste de singlets
            feat_arr[l]=np.copy(singletsL[i].features)
            #.copy()
            distances[l]=min(singletsL[i].center[0], singletsL[i].center[1], np.fabs(singletsL[i].center[0] - YMAX), np.fabs(singletsL[i].center[1] - XMAX))
            
    else:
#        try:
#            taille_feat = singletsL[1].features.shape[0]
#        except IndexError:
#            print "attention je prends une longeur de feat de celle du vecteur 0"
#            taille_feat = singletsL[0].features.shape[0]
        feat_arr = np.empty(shape=(len_hyp, taille_feat))
        
        for l in range(len_hyp):
            #print t[l]
    
            s = t[l][0]
            i = ind(singletsL, s) ; center1 = singletsL[i].center
            #print s, i #son id est sa place dans la liste de singlets
            try:
                feat_arr[l]=np.copy(singletsL[i].features)
            except ValueError:
                print singletsL[i].features.shape, feat_arr[l].shape
                raise FeatureException("Cannot find features of object with label {} ".format(singletsL[i].label))
            #.copy()
            #feat_arr[l].shape = (239,)

            s2 = t[l][1]
            j = ind(nextSinglets, s2) ; center2= nextSinglets[j].center
            #print s2, j
            #print "feat[0]",nextSinglets[j].features
            feat_arr[l]-=nextSinglets[j].features
            #print feat_arr[l]
            distances[l]=sqrt((center1[0]-center2[0])**2 + (center1[1]-center2[1])**2)
            if split:
                angles[l]=angle(center1, nextSinglets[j].centers)
                
            if move:
                ecc = (singletsL[i].orientation[1]+nextSinglets[j].orientation[1])/2
                angl = min(fabs(singletsL[i].orientation[0]-nextSinglets[j].orientation[0]), fabs(singletsL[i].orientation[0]-nextSinglets[j].orientation[0] - pi))
                angles[l]=ecc*angl
                if np.isnan(angles[l]):
                    raise FeatureException("Il y a des NaN dans le calcul des angles, label initial {} ".format(singletsL[i].label))
    
    r = np.fabs(feat_arr)
    r2 = np.hstack((r, distances)) 
    r2 = np.hstack((r2, angles)) 
    return r2
    
def truth(t, singletsL, nextSinglets, app=False, dis=False):
    len_hyp = len(t)
    truth = []
    if  app:
        for l in range(len_hyp):
            targ=t[l][1]
            j = ind(nextSinglets, targ)
            r = 0 if singletsL[0].to is None or nextSinglets[j].label not in singletsL[0].to else 1
            truth.append(r)
    elif dis:
        for l in range(len_hyp):
            s = t[l][0]
            i = ind(singletsL, s)
            r = 1 if singletsL[i].to == (-1,) else 0
            truth.append(r)
    else:
        for l in range(len_hyp):
            s = t[l][0];targ=t[l][1]
            i = ind(singletsL, s) ; j = ind(nextSinglets, targ)
            r = 1 if np.all(singletsL[i].to == nextSinglets[j].label) else 0
            truth.append(r)
    return truth

class Solution():
    def __init__(self, plate, well, index, singletsL, nextSinglets, doubletsL, nextDoublets, featsize, training = True):
        global FEATURE_NUMBER
        FEATURE_NUMBER = featsize
        self.plate = plate ; self.well = well ; self.index = index ; self.singlets = singletsL ; self.nextSinglets = nextSinglets
        if training:
#            print "AVANT D'AVOIR ENLEVE LES MORETHAN THREES"
#            print msg(singletsL, doubletsL), msg(nextSinglets, nextDoublets)
            self.events = [] #dict(zip(EVENTS, [None for x in range(len(EVENTS))]))
            
            self.constraints=np.array([])
            self.features = np.array([])
            self.truth = []
            self.hypotheses = None
            #moreThanThrees = []; 
            moreThanThreesLabels = []; moreThanThreesTarget=[]; moreThanThreesTargetLabels = []
            for s in filter(lambda x: (x.label !=-1) and ((x.to is not None and len(x.to)>3)  or len(x.fr)>3), singletsL):
                moreThanThreesLabels.append(s.label)
                if s.to is not None:
                    #moreThanThreesTarget.append(s.to)#donc une liste de tuplesappend
                    moreThanThreesTargetLabels.extend(s.to)
                else:
                    monDoub = filter(lambda z: z.label == s.fr , doubletsL)[0]
                    #moreThanThrees.append(monDoub.label)
                    if monDoub.to not in moreThanThreesTarget:
                        moreThanThreesTarget.append(monDoub.to)
                        moreThanThreesTargetLabels.extend(monDoub.to)
                
            nextDoubletsC = list(nextDoublets)
            for d in nextDoublets:
                if filter(lambda x: x in d.label, moreThanThreesTargetLabels) != []:
                    nextDoubletsC = filter(lambda x: x.label != d.label, nextDoubletsC)
            doubletsLC = list(doubletsL)
            for d in doubletsL:
                if filter(lambda x: x in d.label, moreThanThreesLabels) != []:
                    doubletsLC = filter(lambda x: x.label != d.label, doubletsLC)
            
#            if len(moreThanThreesLabels)>0:
##                if index == 56:
##                    pdb.set_trace()
#                print "APRES LES AVOIR ENLEVES"
#                print msg(filter(lambda x: x.label not in moreThanThreesLabels, singletsL), doubletsLC), msg(filter(lambda x: x.label not in moreThanThreesTargetLabels, nextSinglets), nextDoubletsC)            
            doubletsLC = filter(lambda x : len(x.label)<4, doubletsLC)
            nextDoubletsC = filter(lambda x : len(x.label)<4, nextDoubletsC)
#            print 'APRES TOUS LES FILTRAGES'
#            print msg(filter(lambda x: x.label not in moreThanThreesLabels, singletsL), doubletsLC), msg(filter(lambda x: x.label not in moreThanThreesTargetLabels, nextSinglets), nextDoubletsC)            

#DONC ICI ON EST BIEN APRES TOUS LES FILTRAGES
            lnSCenters = [nsing.center for nsing in filter(lambda x: x.label not in moreThanThreesTargetLabels and x.label!=-1, nextSinglets)];
            lnDCenters = [ndoub.center for ndoub in nextDoubletsC]
            treeNextSinglets = spatial.cKDTree(lnSCenters, leafsize = 10)
            try:
                treeNextDoublets = spatial.cKDTree(lnDCenters, leafsize = 10)
            except ValueError:
                treeNextDoublets = None

            self.singletsSize = len(singletsL)-len(moreThanThreesLabels)
            t1 = self.singletsSize
            t2 = len(nextSinglets)-len(moreThanThreesTargetLabels)
            
            for x in range(len(EVENTS)):
                si = SIZES[x]
                #print "############################ evenement", EVENTS[x]
                e = Event(si, filter(lambda x: x.label not in moreThanThreesLabels, singletsL), filter(lambda x: x.label not in moreThanThreesTargetLabels, nextSinglets),
                          doubletsLC, nextDoubletsC, treeNextSinglets, treeNextDoublets)
                #print len(e.truth)
                if len(e.truth) != 0:
                    self.constraints = e.constraints if self.constraints.shape ==(0,) else np.hstack((self.constraints, e.constraints))
                    self.truth.extend(e.truth)
                    self.hypotheses = e.hypotheses if self.hypotheses is None else self.hypotheses + e.hypotheses
                    self.features = e.features if self.features.shape ==(0,) else np.vstack((self.features, e.features))
                self.events.append(e)#.update({EVENTS[x]:e})
                
            #print self.constraints, self.truth
            #print "et le resultat du produit constraints*truth :", np.dot(self.constraints, self.truth)
            expected_truth = np.zeros(shape=(t1+t2))
            expected_truth[1:t1]=1; expected_truth[t1+1:]=1
            if not np.all(np.dot(self.constraints, self.truth)== expected_truth) :
                #print "pbl"
                raise TruthException()
            
        else:
            #CAS OU JE CONSTRUIS JUSTE LES HYPOTHESES MAIS JE N'AI PAS LA VERITE
            #print msg(singletsL, doubletsL), msg(nextSinglets, nextDoublets)
            self.events = [] #dict(zip(EVENTS, [None for x in range(len(EVENTS))]))
            
            self.constraints=np.array([])
            self.features = np.array([])
            self.truth = []
            self.hypotheses = None
            
            lnSCenters = [nsing.center for nsing in filter(lambda x: x.label!=-1, nextSinglets)]
            lnDCenters = [ndoub.center for ndoub in nextDoublets]

            treeNextSinglets = spatial.cKDTree(lnSCenters, leafsize = 10)
            try:
                treeNextDoublets = spatial.cKDTree(lnDCenters, leafsize = 10)
            except ValueError:
                treeNextDoublets=None
            self.singletsSize = len(singletsL)
            t1 = self.singletsSize
            t2 = len(nextSinglets)
            
            for x in range(len(EVENTS)):
                si = SIZES[x]
                #print "############################ evenement", EVENTS[x]
                e = Event(si, singletsL, nextSinglets, doubletsL, nextDoublets,treeNextSinglets, treeNextDoublets, training)
                #print len(e.hypotheses)
                try:
                    l=len(e.hypotheses)
                except TypeError:
                    print plate, well, index
                    print "Event: {}. type(e.hypotheses)=NoneType hence likely that there is an error in hdf5 file. ".format(EVENTS[x])
                    l=0
                if l != 0:
                    self.constraints = e.constraints if self.constraints.shape ==(0,) else np.hstack((self.constraints, e.constraints))
                    self.hypotheses = e.hypotheses if self.hypotheses is None else self.hypotheses + e.hypotheses
                    self.features = e.features if self.features.shape ==(0,) else np.vstack((self.features, e.features))
                self.events.append(e)#.update({EVENTS[x]:e})

    
    def constraintsMatrix(self):
        return np.copy(self.constraints)
    
    def featuresMatrix(self):
        result = []       
        
        for x in range(len(EVENTS)):
            if self.events[x].hypotheses is not None and len(self.events[x].hypotheses) >0:
                #print EVENTS[x]
                result.append(np.copy(self.events[x].features))
            else:
                result.append([])
             
        return result
    
    def truthVec(self):
        result = []       
        
        for x in range(len(EVENTS)):
            if len(self.events[x].truth) >0:
                #print EVENTS[x]
                result.append(list(self.events[x].truth))
            else:
                result.append([])
             
        return result
    
    def length_feat(self):
        try:
            return self.features.shape[1]
        except:
            return -1

    def length_events(self):
        return len(EVENTS)
    
    def output(self):
        result = "_______________________##########################NOUVELLE SOLUTION \n"
        result+="tailles :\n"
        result+="les evenements :"+str(self.length_events())+"\n"
        result+="les contraintes"+str(self.constraints.shape)+"\n"
        result+="les features :"+str(self.length_feat())+"\n"
        Mf = self.featuresMatrix(); zou=""; bou=""
        for m in Mf:
            try:
                zou+=str(m.shape)+" "
            except AttributeError:
                zou+="0 "
            bou +=repr(m)+"\n"
        result+="les matrices de features :"+str(zou)+"\n"
        result+="les hypotheses"+str(len(self.hypotheses))+"\n"
        
        Mf2 = self.truthVec(); zou=""; bou2=""
        for m in Mf2:
            zou+=str(len(m))+" "
            bou2+=repr(m)+"\n"
        result += "la verite"+str(zou)+"\n"
        result +="les singlets "+str(self.singletsSize)
        
        result += "------------------------------------------------------------------------Matrice des features : \n"
        result+=str(bou)+"\n"
        result += "------------------------------------------------------------------------Verite : \n"
        result+=str(bou2)
        result+="------------------------------------------------------------------------Matrice des contraintes : \n"
        Mf3 = self.constraintsMatrix()
        result+=repr(Mf3)+"\n"
        
        if Mf2 != [[], [], [], [], []]:
            xTilde = Mf
            psi = np.array([])
            for m in range(self.length_events()):
                fz = np.dot(np.transpose(xTilde[m]), Mf2[m])
                psi = np.hstack((psi, fz))
                
            siQueAppDis = [[0 for x in range(len(Mf2[0]))], [1 for x in range(len(Mf2[1]))], [1 for x in range(len(Mf2[2]))],[0 for x in range(len(Mf2[3]))],
                           [0 for x in range(len(Mf2[4]))]]
            
            psi2 = np.array([])
            for m in range(self.length_events()):
                fz = np.dot(np.transpose(xTilde[m]), siQueAppDis[m])
                psi2 = np.hstack((psi2, fz))
                
            psi-=psi2
            result += "------------------------------------------------------------------------DeltaPsi : \n"
            result+=str(psi)+"\n"
        
        
        return result

class Event():
    
    def __init__(self, si, singletsL, nextSinglets, doubletsL, nextDoublets,treeNextSinglets, treeNextDoublets, training = True):
        global compteur
        self.features=np.array([])
        self.hypotheses = None
        self.constraints=np.array([])
        self.truth = []
#CE QUE JE FAIS LA C'EST DE GENERER TOUTES LES POSSIBILITES D'UNE IMAGE A LA SUIVANTE
        t1 = len(singletsL)
        t2 = len(nextSinglets)

        X = [] ; Y=[]; X2=[] ; Y2=[]
        source1=[] ; source2=[]
        #print "calcul des nearest neighbours d'une frame a l'autre, distance dans l'espace des features, determination de la verite et enfin des contraintes correspondantes pour le mouvement"
        d={}
        if si==(1,1):
            j=0
            for s in filter(lambda x: x.label !=-1, singletsL):
                #print s.label
                dou, i = treeNextSinglets.query(s.center, k, distance_upper_bound = d_bf_move)
                for couple in filter(lambda x: x[1]<100, zip(i,dou)):
                    ll = singletsL[j+1].label
                    if ll not in d:
                        d[ll]=[]
                    try:
                        d[ll].append(nextSinglets[couple[0]+1].label)
                    except:
                        raise MovementException(si)
                j+=1 
            
#TO DISCUSS                
            #on verifie que les cell.to de chaque cellule sont bien dans le dictionnaire
            for s in filter(lambda x: x.label !=-1 and x.to is not None and len(x.to)==1 and x.to!=(-1,), singletsL):
                #print s.label
                try:
                    if s.label not in d:
                        d[s.label]=[]
                    if s.to not in d[s.label]:
                        d[s.label].append(s.to)
                        print "ajout du label", s.to, "dans le dict d'appariements partant de ", s.label, d[s.label]
                        center1 = s.center ; center2 = nextSinglets[ind(nextSinglets, s.to)].center
                        print center1, center2
                        zz=sqrt((center1[0]-center2[0])**2 + (center1[1]-center2[1])**2)
                        print zz
                        if zz<40: compteur[0]+=1
                        else: compteur[1]+=1
                        print compteur
                except:
                    raise MovementException(si)
            listSinglets = transformToHyp(d)

            if listSinglets == ():
                return None
            # "hypotheses de", si, ' ', listSinglets
            #print "J'AJOUTE LES HYPOTHESES"
            self.hypotheses = listSinglets if self.hypotheses is None else self.hypotheses + listSinglets
            
            #print "CALCUL DES CONTRAINTES CORRESPONDANTES"
            contraintes = constraints(listSinglets, t1, t2, singletsL, nextSinglets)
            #print "J'AJOUTE LES CONTRAINTES"
            self.constraints = contraintes if self.constraints.shape ==(0,) else np.hstack((self.constraints, contraintes))
            
            #print "CALCUL DES joint FEATURES"
            feat = features(listSinglets, singletsL, nextSinglets, split = False, move= True)
            #print "J'AJOUTE LES FEATURES"
            self.features = feat if self.features.shape ==(0,) else np.vstack((self.features, feat))
            
            if training:
                #print "CALCUL DE LA VERITE"
                tru = truth(listSinglets, singletsL, nextSinglets)
                #print "on doit trouver un vecteur de taille hyp qui ne vaut que un", np.dot(contraintes,tru)
                #print "J'AJOUTE LA VERITE"
                self.truth.extend(tru)
#FIXME ALORS IL FAUT FAIRE AUSSI CONTRAINTES FEATURES ET TRUTH DANS LE CAS DES MERGES SPLIT APP ET DISAPP
# IL FAUT AUSSI VERIFIER QUE DANS LES APPARIEMENTS DE SINGLETS ET DOUBLETS ON PERMET LES VRAIS SPLITS ET MERGES... DONC VERIFIER SI CELL.TO EST BIEN DANS CE QUE NN() RETOURNE
 
#     MAIS EN MEME TEMPS IL FAUDRA S'INTERESSER' A CPLEX PARCE QUE C'EST LUI QUI PERMET' DE TROUVER LA CONTRAINTE LA PLUS VIOLEE A CHAQUE ITERATION
#     ET REGARDER BIEN TOUS LES PETITS PARAMETRES CACHES....            
#                
        if si==(1,"M"):
            j=0
            if treeNextDoublets == None:
                return None
            for s in filter(lambda x: x.label !=-1 , singletsL):
                dou, i = treeNextDoublets.query(s.center, k, distance_upper_bound = d_bf_more)
                for couple in filter(lambda x: x[1]<100, zip(i,dou)):
                    ll = singletsL[j+1].label
                    if ll not in d:
                        d[ll]=[]
                    try:
                        d[ll].append(nextDoublets[couple[0]].label)
                    except:
                        raise MovementException(si)
                j+=1 

            for s in filter(lambda x: x.label !=-1 and x.to is not None and len(x.to)>1, singletsL):
                if s.label not in d:
                    d[s.label]=[]
                if s.to not in d[s.label]:
                    d[s.label].append(s.to)
                    print "ajout du label", s.to, "dans le dict d'appariements partant de ", s.label, d[s.label]
                    
            listSinDoublets = transformToHyp(d)
             
            if listSinDoublets == ():
                return None
            #print "hypotheses de", si, ' ', listSinDoublets
            #print "J'AJOUTE LES HYPOTHESES"
            self.hypotheses = listSinDoublets if self.hypotheses is None else self.hypotheses + listSinDoublets
            
            #print "CALCUL DES CONTRAINTES CORRESPONDANTES"
            contraintes = constraints(listSinDoublets, t1, t2, singletsL, nextSinglets)
            #print "J'AJOUTE LES CONTRAINTES"
            self.constraints = contraintes if self.constraints.shape ==(0,) else np.hstack((self.constraints, contraintes))
            
            #print "CALCUL DES joint FEATURES"
            feat = features(listSinDoublets, singletsL, nextDoublets, split = True)
            #print "J'AJOUTE LES FEATURES"
            self.features = feat if self.features.shape ==(0,) else np.vstack((self.features, feat))
            if training:
                #print "CALCUL DE LA VERITE"
                tru = truth(listSinDoublets, singletsL, nextDoublets)
                #print "on doit trouver un vecteur de taille hyp qui ne vaut que un", np.dot(contraintes,tru)
                #print "J'AJOUTE LA VERITE"
                self.truth.extend(tru)
            
        if si==("M",1):
            j=0
            for s in doubletsL:
                dou, i = treeNextSinglets.query(s.center, k, distance_upper_bound = d_bf_more)
                for couple in filter(lambda x: x[1]<100, zip(i,dou)):
                    ll = doubletsL[j].label
                    if ll not in d:
                        d[ll]=[]
                    try:
                        d[ll].append(nextSinglets[couple[0]+1].label)
                    except:
                        raise MovementException(si)
                j+=1 

            for s in filter(lambda x: x.to is not None, doubletsL):

                if s.label not in d:
                    d[s.label]=[]
                if s.to not in d[s.label]:
                    d[s.label].append(s.to)
                    print "ajout du label", s.to, "dans le dict d'appariements partant de ", s.label, d[s.label]

            listDouSinglets = transformToHyp(d)
            if listDouSinglets == ():
                return None
            
            #print "hypotheses de", si, ' ', listDouSinglets
            #print "J'AJOUTE LES HYPOTHESES"
            self.hypotheses = listDouSinglets if self.hypotheses is None else self.hypotheses + listDouSinglets
            
            #print "CALCUL DES CONTRAINTES CORRESPONDANTES"
            contraintes = constraints(listDouSinglets, t1, t2, singletsL, nextSinglets)
            #print "J'AJOUTE LES CONTRAINTES"
            self.constraints = contraintes if self.constraints.shape ==(0,) else np.hstack((self.constraints, contraintes))
            
            #print "CALCUL DES joint FEATURES"
            feat = features(listDouSinglets, doubletsL, nextSinglets)
            #print "J'AJOUTE LES FEATURES"
            self.features = feat if self.features.shape ==(0,) else np.vstack((self.features, feat))
            
            if training:
                #print "CALCUL DE LA VERITE"
                tru = truth(listDouSinglets, doubletsL, nextSinglets)
                #print "on doit trouver un vecteur de taille hyp qui ne vaut que un", np.dot(contraintes,tru)
                #print "J'AJOUTE LA VERITE"
                self.truth.extend(tru)
            
        if si==(0,1):
            d = {-1:[]}
            for s in filter(lambda x: x.label !=-1, nextSinglets):
                d[-1].append(s.label)
            #print d
            listApp = transformToHyp(d)
            #print "hypotheses de", si, ' ', listApp
            #print "J'AJOUTE LES HYPOTHESES"
            self.hypotheses = listApp if self.hypotheses is None else self.hypotheses + listApp
            
            #print "CALCUL DES CONTRAINTES CORRESPONDANTES"
            contraintes = constraints(listApp, t1, t2, None, nextSinglets)
            #print "J'AJOUTE LES CONTRAINTES"
            self.constraints = contraintes if self.constraints.shape ==(0,) else np.hstack((self.constraints, contraintes))
#DECIDER CE QU'ON FAIT POUR LES FEATURES DES CELLULES QUI APPARAISSENT ??
            #print "CALCUL DES joint FEATURES"
            feat = features(listApp, None, nextSinglets)
            #print "J'AJOUTE LES FEATURES"
            self.features = feat if self.features.shape ==(0,) else np.vstack((self.features, feat))
            
            if training:
                #print "CALCUL DE LA VERITE"
                tru = truth(listApp, singletsL, nextSinglets, app=True)
                #print "on doit trouver un vecteur de taille hyp qui ne vaut que un", np.dot(contraintes,tru)
                #print "J'AJOUTE LA VERITE"
                self.truth.extend(tru)
            
        if si==(1,0):
            d = {}
            for s in filter(lambda x: x.label !=-1,singletsL):
                d.update({s.label : [-1]})
                
            #print d
            listDis = transformToHyp(d)
            #print "hypotheses de", si, ' ', listDis
            #print "J'AJOUTE LES HYPOTHESES"
            self.hypotheses = listDis if self.hypotheses is None else self.hypotheses + listDis
            
            #print "CALCUL DES CONTRAINTES CORRESPONDANTES"
            contraintes = constraints(listDis, t1, t2, singletsL, None)
            #print "J'AJOUTE LES CONTRAINTES"
            self.constraints = contraintes if self.constraints.shape ==(0,) else np.hstack((self.constraints, contraintes))
#DECIDER CE QU'ON FAIT POUR LES FEATURES DES CELLULES QUI APPARAISSENT ??
            #print "CALCUL DES joint FEATURES"
            feat = features(listDis, singletsL, None)
            #print "J'AJOUTE LES FEATURES"
            self.features = feat if self.features.shape ==(0,) else np.vstack((self.features, feat))
            
            if training:
                #print "CALCUL DE LA VERITE"
                tru = truth(listDis, singletsL, nextSinglets, dis=True)
                #print "on doit trouver un vecteur de taille hyp qui ne vaut que un", np.dot(contraintes,tru)
                #print "J'AJOUTE LA VERITE"
                self.truth.extend(tru) 
#                
#        print "hypotheses DE L'evenement", self.hypotheses
#        print "contraintes DE L'evenement", self.constraints
#        print "verite DE L'evenement", self.truth
        return
        
class Solutions():
    def __init__(self, solution=None, lstSolutions = None):
        if solution is not None:
            self.lstSolutions = [solution]
        elif lstSolutions is not None:
            self.lstSolutions = lstSolutions
        else:
            raise FunctionException
        
    def append(self, solution):
        self.lstSolutions.append(solution)
        
    def length_feat(self):
        #global FEATURE_NUMBER
        return self.lstSolutions[0].length_feat() if self.lstSolutions != [] else -1
    
    def output(self):
        result = ""
        for s in self.lstSolutions:
            result+=s.output()
            
        return result
    
    def normalisation(self, minMax = None):
        if minMax == None:
            result = [[[10**9, 0] for y in range(self.length_feat())] for x in range(len(EVENTS))]
            for sol in self.lstSolutions:
                for k in range(len(EVENTS)):
                    eCf = np.transpose(sol.events[k].features)
                    #shape=(len_hyp, taille_feat) avant transposition
                    for f in range(eCf.shape[0]):
                        m = np.min(eCf[f]); M = np.max(eCf[f])
                        result[k][f][0] = min(m, result[k][f][0])
                        result[k][f][1] = max(M, result[k][f][1])
            for sol in self.lstSolutions:
                for k in range(len(EVENTS)):
                    eCf = np.transpose(sol.events[k].features)
                    #shape=(len_hyp, taille_feat) avant transposition
                    for f in range(eCf.shape[0]):
                        eCf[f]=2.0 * (eCf[f] - result[k][f][0]) / (result[k][f][1] - result[k][f][0] + 0.0000001) - 1.0                
            return result
        else:
            for sol in self.lstSolutions:
                for k in range(len(EVENTS)):
                    eCf = np.transpose(sol.events[k].features)
                    #shape=(len_hyp, taille_feat) avant transposition
                    for f in range(eCf.shape[0]):
                        eCf[f]=2.0 * (eCf[f] - minMax[k][f][0]) / (minMax[k][f][1] - minMax[k][f][0] + 0.0000001) - 1.0   
            return 1
        
    def denormalisation(self, minMax):    
        for sol in self.lstSolutions:
            for k in range(len(EVENTS)):
                eCf = np.transpose(sol.events[k].features)
                #shape=(len_hyp, taille_feat) avant transposition
                for f in range(eCf.shape[0]):
                    eCf[f]= (eCf[f]+1)*(minMax[k][f][1] - minMax[k][f][0] + 0.0000001)/2+minMax[k][f][0]                   
        return 1

def msg(singletsL, doubletsL):
    result = ""
    i=0
    for singlet in singletsL:
        result+= "singlet index dans singletsL "+str(i)+" singlet label "+str(singlet.label)+"\n"
        i+=1
    j=0   
    for doublet in doubletsL:
        result+= "doublet index dans doubletsL "+str(j)+" doublet label "+str(doublet.label)+"\n"
        j+=1
        
    return result


class TruthException(Exception):
    def __init__(self):
        pass
    
    def __str__(self):
        return "le produit contraintes*verite n'est pas egal a ce qu'il devrait etre"
    
class MoreThanOneException(Exception):
    def __init__(self, label):
        print "More than one object with given label", sys.exc_info()
        print "label", label
        pass
    
class FeatureException(Exception):
    def __init__(self, string):
        print string, sys.exc_info()
        pass
    
class MovementException(Exception):
    def __init__(self, si):
        print "Problem as building {} hypothesis".format(si), sys.exc_info()
        pass
class FunctionException(Exception):
    def __init__(self):
        print "Bad arguments", sys.exc_info()
        pass
    