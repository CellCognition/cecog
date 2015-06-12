/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Xiwei Zhang
// $Date$
// $Rev$
// $URL$


#ifndef __maxTree_hxx
#define __maxTree_hxx

#include "project_definitions.hxx"

#include <queue>
#include <list>

// #include "utility_z.hxx"



/*  Construction of a Max-tree from an image
Method from article:
@article{salembier1998antiextensive,
title={Antiextensive connected operators for image and sequence processing},
author={Salembier, P. and Oliveras, A. and Garrido, L.},
journal={Image Processing, IEEE Transactions on},
volume={7},
number={4},
pages={555--570},
year={1998},
publisher={IEEE}
}
*/


// using namespace std;


const int nl6[2][6][2] = { { {0,-1},{1,0},{0,1},{-1,1},{-1,0},{-1,-1}},
                            {{1,-1},{1,0},{1,1},{0,1},{-1,0},{0,-1}} };
const int nl8[2][8][2] = { { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} },
                           { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} } };

namespace cecog{
namespace morpho{

using namespace std;
using namespace vigra;

template <class T1, class S1>
int *histogram( const MultiArrayView<2, T1, S1> imin ) {
    int size[2] = { imin.shape()[0], imin.shape()[1]};
    int *hist = new int[258];
    memset( hist, 0, sizeof(int) * 258);

    for (int i=0; i<size[0]; ++i){
        for (int j=0; j<size[1]; ++j){
            ++ hist[(int) imin(i,j)];
        }
    }

    int vmin(0), vmax(255);
    bool fmin(true), fmax(true);
    for (int i=0; i<255; ++i){
        if (hist[i]==0 && fmin) ++vmin;
        else fmin = false;
        if (hist[255 - i]==0 && fmax) --vmax;
        else fmax = false;
    }

    hist[256] = vmin;
    hist[257] = vmax;

    return hist;

} // end of function histogram

class mxt{
public:
	queue<int> *hqueueX;
	queue<int> *hqueueY;
	queue<int> Qhi[2];
	queue<int> Qmj[2];
	int *Nnodes;
	int *hist;
	bool *nodeAtLevel;

	mxt(const MultiArrayView<2, UInt8> imin, MultiArrayView<2, int> imstate);  // constructor
	void DeMT();  // Deconstruction
	int flood_h(int h, const MultiArrayView<2, UInt8> imin, MultiArrayView<2, int> imstate, int se);  // build a maxtree
};

// Construct for mxt (max tree) class
mxt::mxt(const MultiArrayView<2, UInt8> imin, MultiArrayView<2, int> imstate){
    int w = imin.shape()[0];
    int h = imin.shape()[1];
	hist = histogram(imin);

	int lenH = hist[257]+1;
 	
	hqueueX = new queue<int>[lenH];  // hist 256,257 --> min and max histogram
	hqueueY = new queue<int>[lenH]; 
	
	Nnodes = new int[lenH];  // number of node for each layer
    memset(Nnodes, 0, sizeof(int) * lenH);
	nodeAtLevel = new bool[lenH];
    std::fill( nodeAtLevel, nodeAtLevel+lenH, false);

	// initialize
	// put the lowest gray level pixel into queue 
    bool f(false);
	for (int j=0;j<h;++j){
		for (int i=0;i<w;++i){
			if (imin(i,j) ==  hist[256]){
				hqueueX[hist[256]].push(i); // hqueueX[0].push(0)
				hqueueY[hist[256]].push(j); // hqueueY[0].push(0)
				imstate(i,j) = -1;
				nodeAtLevel[hist[256]] = true;
                f = true;
				break;
			}
		}
		if (f) break;
	}
}

// Deconstruction 
void mxt::DeMT(){
	delete[] hqueueX;
	delete[] hqueueY;
	delete[] Nnodes;
	delete[] nodeAtLevel;
	delete[] hist;
}

// Flood at h-level (Maxtree is built here by recursion) 
int mxt::flood_h(int h, const MultiArrayView<2, UInt8> imin, MultiArrayView<2, int> imstate, int se){  // build a maxtree
	int size[2] = {imin.shape()[0], imin.shape()[1]};
    int nl[2][6][2] = { { {0,-1},{1,0},{0,1},{-1,1},{-1,0},{-1,-1}},
                            {{1,-1},{1,0},{1,1},{0,1},{-1,0},{0,-1}} };

	//int **se_even = nl(se,1);
	//int **se_odd = nl(se,0);
	int px,py,x,y,vp,vq,m,s,t;
	while (! hqueueX[h].empty()){
		px = hqueueX[h].front();
		py = hqueueY[h].front();
		hqueueX[h].pop();
		hqueueY[h].pop();
        imstate(px, py) = Nnodes[h];
		vp = h;

		for (int k=0; k<se; ++k){
            x = px + nl[py%2][k][0];
            y = py + nl[py%2][k][1];
			// if (py%2==0){
			// 	x = px + se_even[k][0];
			// 	y = py + se_even[k][1];
			// }
			// else{
			// 	x = px + se_odd[k][0];
			// 	y = py + se_odd[k][1];
			// }
			 
			if(x<0 || x>=size[0]|| y<0||y>=size[1]) continue;

			if(imstate(x,y)==-2){
				vq = int(imin(x,y));
				hqueueX[vq].push(x);
				hqueueY[vq].push(y);
				imstate(x,y) = -1;
				nodeAtLevel[vq] = true;
				if (vq>vp){
					m = vq;
					while(m!=h){
						m = flood_h(m,imin, imstate, se);
					}
				}
			}
		}
	}
	++Nnodes[h];

	m = h-1;
	while (m>=0 && nodeAtLevel[m] == false){
		--m;
	}

	if (m>=0){
		s = Nnodes[h]-1;
		t = Nnodes[m];
		Qhi[0].push(h);
		Qhi[1].push(s);
		Qmj[0].push(m);
		Qmj[1].push(t);
	}
	else{
		Qhi[0].push(h);
		Qhi[1].push(0);
		Qmj[0].push(-1);
		Qmj[1].push(-1);
	}

	
	nodeAtLevel[h]=false;
	return m;
}





//###########################################
// Class layer (analysis each node of maxtree)
class layer{
public:
	// Management de maxtree
	int h,i; // h: height  i: number of label
	int parent[2]; // -1,-1 mean root
	std::list<int> children[2];  // all children
	std::list<int> p[2];  // all pixels within this layer
	std::list<int> maxChild[2];  // all maxima of this layer
		
	// Self-properties
	int W;
	int H;
	int xmin,xmax,ymin,ymax;
	int area;
	int center[2];
	int length;// geolength;
	float length2; // cartesian, distance between two end points
	int length3; // orthogonal to length2 ,width for bounding box rotated
	float length4; // mean width along geolength direction
	float widthVar;
	int maxWidth;
	std::list<float> meanWidthL; // interrupted orthogonal width. inter points see interP
	std::list<int> maxWidthL;
	std::list<float> widthVarL;

	int volume;
	int perimeter;
		
    int Npics;
	int NpixelsAboveC; // given a criterier C, for each cc, number of pixels above this threshold
	int vIPic;   // Value of maxima in I (orig) image. for MA, the minima in orig 
	int vTHPic;  // Value of maxima in Top Hat image.
	int IC;  // given a number of pixels, for each cc, from the maximum to the bottom, when arrive this number of pixels, take the greylevel
	float Imean; 
	int Imedian;
	int THC;
	float THmean;
	int THmedian;

	float circ1;  // (pi*D^2)/(4*S) where D is diameter and S is area
	float circ2;  // C^2/(4*pi*S) where C is perimeter and S is area
		
	float orient; // Not used...

	float var1; // local variance green channel
	float var2; // local variance on tophat image
	float var3; // between 12 direction

	// Environment	
	int inner_en_area[8];
	int outter_en_area[8];
	int count[4];
		
	// Others		
	int mark;  // mark:0 background ,1 vessel1 2,vessel2 3,ma 4,noise 5,big
	int markFilter;
	int p1[2];
	int p2[2];
	int p3[2];
	int p4[2];
	std::list<int> interP[2];

	// viterbi
	double emP[5];
	double V[5],maxV;
	int maxP,maxFP;
	int maContrast;
	int hmContrast;
		
	// Functions
	layer();
	void getBasicInfo(std::list<int>* pp);
	void printInfo();
	void getPixels(layer **node, std::list<int>* pp);
	void setValue(MultiArrayView<2, UInt8> imin, int v,int ini);
	// void setValueP(Mat imin, std::list<int>* pp, int v,int ini);
	void geoLength(MultiArrayView<2, UInt8> imin, MultiArrayView<2, UInt8> imstate, layer **node, int se, std::list<int> *pp, int interval, int critere,  MultiArrayView<2, UInt8> imout, bool lenOrtho);
	void lengthOrtho(std::list<int> *pp, int *startP, int *endP, int critere, MultiArrayView<2, UInt8> imout);
};

layer::layer(){
	W = -1;
	H = -1;
	xmin = 99999;
	xmax = -1;
	ymin = 99999;
	ymax = -1;
	area = 0;
	center[0] = -1;
	center[1] = -1;
	orient = -1;
	mark = 0;
	vTHPic = -1;
	NpixelsAboveC = 0;
	volume = 0;
	for(int i=0; i<8; ++i){
		inner_en_area[i] = 0;
		outter_en_area[i] = 0;
	}
    Npics = 0;
	count[0] = -1;
	count[1] = -1;
	markFilter = -1;
	maContrast = 0;
	hmContrast = 0;
	length = 0;
	circ1 = 0.0f;
	circ2 = 0.0f;
}

void layer::printInfo(){
	cout<<"parents: "<< parent[0]<<" "<<parent[1]<<endl;
	cout<<"W: "<<W<<endl;
	cout<<"H: "<<H<<endl;
	cout<<"area: "<<area<<endl;
	cout<<"center: "<<center[0]<<" "<<center[1]<<endl;
	cout<<"orient: "<<orient;
	cout<<endl;
}

void layer::getBasicInfo(std::list<int>* pp){
	std::list<int>::iterator it1; 
	std::list<int>::iterator it2;
	it1 = pp[0].begin();
	it2 = pp[1].begin();
	int xmin(9999),ymin(9999),xmax(-1),ymax(-1);
	while(it1!=pp[0].end()){
		if (*it1>=xmax) xmax = *it1;
		if (*it1<=xmin) xmin = *it1;
		if (*it2>=ymax) ymax = *it2;
		if (*it2<=ymin) ymin = *it2;
		it1++;
		it2++;
	}
	W = xmax - xmin;
	H = ymax - ymin;
	area = (int)pp[0].size();
}

void layer::getPixels( layer **node, std::list<int>* pp){
	std::list<int>::iterator it1; 
	std::list<int>::iterator it2; 
	it1 = p[0].begin();
	it2 = p[1].begin();
	while(it1!=p[0].end()){
		pp[0].push_back(*it1);
		pp[1].push_back(*it2);
		it1++;
		it2++;
	}
	it1 = children[0].begin();
	it2 = children[1].begin();
	while (it1 != children[0].end()){
		node[*it1][*it2].getPixels(node, pp);
		it1++;
		it2++;
	}
}


void layer::setValue(MultiArrayView<2, UInt8> imin, int v,int ini=-1){  // set image value
	std::list<int>::iterator it1; 
	std::list<int>::iterator it2; 
	it1 = p[0].begin();
	it2 = p[1].begin();
	while(it1!= p[0].end()){
		if (ini==-2){
			if (imin(*it1, *it2) < v){
				imin(*it1, *it2) = v;
			}
		}
		else if (ini!=-1){
			if (imin(*it1, *it2)==ini){
				imin(*it1, *it2) = v;
			}
		}
		else
			imin(*it1, *it2) = v;
		++it1;
		++it2;
	}
}

/***
void layer::setValueP(Mat imin, std::list<int>* pp, int v, int ini=-1){
	std::list<int>::iterator it1; 
	std::list<int>::iterator it2; 
	it1 = pp[0].begin();
	it2 = pp[1].begin();
	while(it1!= pp[0].end()){
		if (ini!=-1){
			if (imin.at<uchar>(*it2,*it1)==ini){
				imin.at<uchar>(*it2,*it1) = v;
			}
		}
		else
			imin.at<uchar>(*it2,*it1) = v;
		++it1;
		++it2;
	}
}

***/


// get geodesic length

void layer::geoLength(const MultiArrayView<2, UInt8> imin, MultiArrayView<2, UInt8> imstate, layer **node, int se, std::list<int> *pp, int interval, int critere,  MultiArrayView<2, UInt8> imout, bool lenOrtho){
	////  Four steps:
	//////1. Get all border pixels
	//////2. Get the most further pixel (to the geometric center)
	//////3. First propagation from the most further pixel, get the last pixel(another most further, to avoid concave case)
	//////4. Second propagation from the new most further pixel, get the geo-length
	int size[2] = {imin.shape()[0],imin.shape()[1]};
	int inter = interval;

    int *** nl = new int ** [2];
    if (se == 6){
        for (int k=0; k<2; ++k){
            nl[k] = new int * [6];
            for (int l=0; l<6; ++l){
                nl[k][l] = new int [2];
                nl[k][l][0] = nl6[k][l][0];
                nl[k][l][1] = nl6[k][l][1];
            }
        }
    }
    else if (se == 8){
        for (int k=0; k<2; ++k){
            nl[k] = new int * [8];
            for (int l=0; l<8; ++l){
                nl[k][l] = new int [2];
                nl[k][l][0] = nl8[k][l][0];
                nl[k][l][1] = nl8[k][l][1];
            }
        }
    }
 

	////int croix[4][2] = {{0,-1} ,{-1,0}, {1,0}, {0,1}}; // Cross SE
	////int diag[4][2] = {{-1,-1} ,{1,-1}, {-1,1}, {1,1}}; // Cross SE
	queue<int> Q[2];
	std::list<int>::iterator itx;
	std::list<int>::iterator ity;
	itx = p[0].begin();
	ity = p[1].begin();
	float dist, maxDist(0);
	int px,py,mx,my,f(0), len(0),sumX(0),sumY(0);
	std::list<int> temppp[2];

	// 1. Get border pixels. put into Q
	while (itx != p[0].end()){
		f = 0;

		for (int k=0; k<se; ++k){
            px = *itx + nl[*ity%2][k][0];
            py = *ity + nl[*ity%2][k][1];
			if (px<0 || px>=size[0] || py<0 || py>=size[1]) continue;
			if (imin(px, py)<h){  // see if it's on the edge;
				f = 1;
				break;
			}
		}

		if (f==1){
			Q[0].push(*itx);
			Q[1].push(*ity);
			sumX += *itx;
			sumY += *ity;
		}

		imstate(*itx, *ity) = 0;

		++itx;
		++ity;
	}

	// for perimeter
	perimeter = (int)Q[0].size();
	// for center
	center[0] = round(sumX / float(perimeter));
	center[1] = round(sumY / float(perimeter));

	// 2. Get the pixel most far 
	while(!Q[0].empty()){
		px = Q[0].front();
		py = Q[1].front();
		dist = sqrt((float)(center[0]-px)*(center[0]-px) + (center[1]-py)*(center[1]-py));
		if (dist>=maxDist){
			maxDist = dist;
			mx = px;
			my = py;
		}
		Q[0].pop();
		Q[1].pop();
	}

	Q[0].push(mx);
	Q[1].push(my);

	while(!Q[0].empty()){
		mx = Q[0].front();
		my = Q[1].front();
		if (imstate(mx,my)!=0){
			Q[0].pop();
			Q[1].pop();
			continue;
		}

		for (int k=0; k<se; ++k){
            px = mx + nl[my%2][k][0];
            py = my + nl[my%2][k][1];
			if (px<0 || px>=size[0] || py<0 || py>=size[1]) continue;
			if (imin(px, py)>=h && imstate(px,py)==0){  // see if it's on the edge;
				Q[0].push(px);
				Q[1].push(py);
			}
		}
		imstate(mx, my)= 1;
		Q[0].pop();
		Q[1].pop();
	}
	Q[0].push(mx);
	Q[1].push(my);
	temppp[0].push_back(mx);
	temppp[1].push_back(my);
	Q[0].push(-1); // -1 is a mark point
	Q[1].push(-1);
	imstate(mx, my) = 2;
	p1[0] = mx;
	p1[1] = my;
	interP[0].push_back(mx);
	interP[1].push_back(my);
	p3[0] = mx;
	p3[1] = my;
	// cout<<p3[0]<<" "<<p3[1]<<endl;

	// 4. Second propagation
	while(!Q[0].empty()){
		mx = Q[0].front();
		my = Q[1].front();

		if (mx == -1) {  // if the mark point pop out, one iteration is done, len ++
			++len;
			Q[0].pop();
			Q[1].pop();
			if (Q[0].empty()) break;
			Q[0].push(-1);
			Q[1].push(-1);
			mx = Q[0].front();
			my = Q[1].front();

			if(len>=inter){
				interP[0].push_back(p4[0]);
				interP[1].push_back(p4[1]);
				//cout<<"INT: "<<interval<<" "<<p3[0]<<" "<<p3[1]<<" "<<p4[0]<<" "<<p4[1]<<"  "<<p1[0]<<" "<<p1[1]<<endl;
				lengthOrtho(temppp,p3,p4,critere,imout);
				temppp[0].clear();
				temppp[1].clear();
				
				inter += interval;
				p3[0] = mx;
				p3[1] = my;
			}
		}
		p2[0] = mx;
		p2[1] = my;

		f = 0;
		for (int k=0; k<se; ++k){
            px = mx + nl[my%2][k][0];
            py = my + nl[my%2][k][1];
			if (px<0 || px>=size[0] || py<0 || py>=size[1]) continue;
			if (imin(px, py)>=h && imstate(px, py)==1){
				Q[0].push(px);	
				Q[1].push(py);
				temppp[0].push_back(px);
				temppp[1].push_back(py);
				imstate(px, py) = 2;
				f = 1;
				p4[0] = px;
				p4[1] = py;
			}
		}

	//	imstate[my][mx] = 2;
		Q[0].pop();
		Q[1].pop();
	}
	// cout<<"INT: "<<interval<<" "<<p3[0]<<" "<<p3[1]<<" "<<p4[0]<<" "<<p4[1]<<"  "<<p1[0]<<" "<<p1[1]<<endl;
	if (lenOrtho)
		lengthOrtho(temppp,p3,p4,critere,imout);
	interP[0].push_back(p2[0]);
	interP[1].push_back(p2[1]);

	length = len;
	length2 = sqrt(pow(float(p1[0]-p2[0]),2) + pow(float(p1[1]-p2[1]),2));


	for (int k=0; k<2; ++k){
        for (int l=0; l<se; ++l){
		    delete[] nl[k][l];
        }
	}
	delete[] nl;


}

void layer::lengthOrtho(std::list<int> *pp, int *startP, int *endP, int critere, MultiArrayView<2, UInt8> imout){
	// cout<<" "<<startP[0]<<" "<<startP[1]<<" "<<endP[0]<<" "<<endP[1]<<" "<<pp[0].size()<<endl;

	//// Axis rotation:
	//// 	(x') = (cosA -sinA)   (x)
	//// 	(y')   (sinA cosA )   (y)
	//// 	x' = x cosA - y sinA
	//// 	y' = x sinA + y cosA
	
	float A,minVx(9999),maxVx(-9999),minVy(9999),maxVy(-9999),x_,y_;
	std::list<int> temp[2];

	if ((startP[0] - endP[0])==0) A=3.1415f/2;
	else{
		A = float(3.1415 - atan2(float(endP[1]-startP[1]),float(endP[0]-startP[0])));
	}

	std::list<int>::iterator itx;
	std::list<int>::iterator ity;
	itx = pp[0].begin();
	ity = pp[1].begin();				
	while(itx!=pp[0].end()){
		x_ = *itx * cos(A) - *ity * sin(A);
		y_ = *itx * sin(A) + *ity * cos(A);
		if (y_<=minVy) {minVy = y_;}
		if (y_>=maxVy) {maxVy = y_;}
		if (x_<=minVx) {minVx = x_;}
		if (x_>=maxVx) {maxVx = x_;}
		temp[0].push_back(round(x_));
		temp[1].push_back(round(y_));
		itx++;
		ity++;
	}
	length3 = round(maxVy - minVy);


	//#########################
	// for the mean width
	float w(0),meanNorm;
	int n(0),x,y,x0,minVY(9999),maxVY(-9999);
	std::list<int> wd; //width
	temp[0].push_back(99999999);
	temp[1].push_back(99999999);
	for (int i=round(minVx); i<=round(maxVx); i++){
		while(temp[0].front() != 99999999){
			x = temp[0].front();
			y = temp[1].front();
			temp[0].pop_front();
			temp[1].pop_front();
			if (x==i){
				if (y<=minVY) minVY=y;
				if (y>=maxVY) maxVY=y;
			}
			else{
				temp[0].push_back(x);
				temp[1].push_back(y);
			}
		}
		if (maxVY!=-9999)
			wd.push_back(maxVY - minVY+1);
		temp[0].pop_front();
		temp[1].pop_front();
		if (temp[0].empty()) break;
		x0 = temp[0].front();
		minVY = temp[1].front();
		maxVY = temp[1].front();
		temp[0].pop_front();
		temp[1].pop_front();
		temp[0].push_back(99999999);
		temp[1].push_back(99999999);
	}
	std::list<int>::iterator it = wd.begin();
	while(it != wd.end()){
		w+=*it;
		it++;
	}
	
	if (wd.size()==0) {
		meanWidthL.push_back(0);
		length4 = 0;
	}
	else {
		meanWidthL.push_back(length4);
		length4 = w/wd.size();
	}
	// VAR
	wd.sort();
	meanNorm = length4/wd.back();
	it = wd.begin();
	w = 0;
	while(it != wd.end()){
		w += pow(((*it)/wd.back() - meanNorm),2);
		it++;
	}
	widthVar = w/(wd.size());
	maxWidth = wd.back();
	widthVarL.push_back(widthVar);
	maxWidthL.push_back(maxWidth);

	//////////////// classification //////////
	//if (length4<=critere && maxWidth<=2*critere){
	//	setValueP(imout,pp,1,0);
	//	mark = 1;
	//}
	//else{
	//	setValueP(imout,pp,3);
	//	mark = 3;
	//}
}


// end of class layer
//###########################################



void getRelations(mxt maxTree, layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, int lenH, int C_area_max){
	int hh,ii,fh,fi;
	int size[2] = {imin.shape()[0], imin.shape()[1]};
	// For every node in maxtree, get it's parent nodes and children nodes
	while (! maxTree.Qhi[0].empty()){  
		hh = maxTree.Qhi[0].front(); // Qhi's father is Qmj
		ii = maxTree.Qhi[1].front();
		fh = maxTree.Qmj[0].front();
		fi = maxTree.Qmj[1].front();
		maxTree.Qhi[0].pop();
		maxTree.Qhi[1].pop();
		maxTree.Qmj[0].pop();
		maxTree.Qmj[1].pop();
		node[hh][ii].parent[0] = fh;
		node[hh][ii].parent[1] = fi; node[hh][ii].h = hh;
		node[hh][ii].i = ii;
		if (fh==-1 || fi == -1) continue;
		node[fh][fi].children[0].push_back(hh);
		node[fh][fi].children[1].push_back(ii);
	}

	for (int j=0; j<size[1]; ++j){ // get all pixels' position of each node
		for(int i=0; i<size[0]; ++i){
			hh = (int)imin(i,j);
			ii = (int)imstate(i,j);
			node[hh][ii].p[0].push_back(i);
			node[hh][ii].p[1].push_back(j);
			if (i<node[hh][ii].xmin) node[hh][ii].xmin = i;
			if (i>node[hh][ii].xmax) node[hh][ii].xmax = i;
			if (j<node[hh][ii].ymin) node[hh][ii].ymin = j;
			if (j>node[hh][ii].ymax) node[hh][ii].ymax = j;
		}
	}

	if (C_area_max!=0){
		std::list<int>::iterator it1;
		std::list<int>::iterator it2;
		std::list<int>::iterator it3;
		std::list<int>::iterator it4;
		for (int i=lenH-1; i>0; --i){
			for (int j=0; j<maxTree.Nnodes[i]; ++j){
				if (!node[i][j].children[0].empty()){
					it1 = node[i][j].children[0].begin();
					it2 = node[i][j].children[1].begin();
					while (it1 != node[i][j].children[0].end()){
						if (node[*it1][*it2].area>C_area_max){
							node[i][j].area = C_area_max+1;
							break;
						}
						it3 = node[*it1][*it2].p[0].begin();
						it4 = node[*it1][*it2].p[1].begin();
						while(it3 != node[*it1][*it2].p[0].end()){
							node[i][j].p[0].push_back(*it3);
							node[i][j].p[1].push_back(*it4);
							if (*it3<node[i][j].xmin) node[i][j].xmin = *it3;
							if (*it3>node[i][j].xmax) node[i][j].xmax = *it3;
							if (*it4<node[i][j].ymin) node[i][j].ymin = *it4;
							if (*it4>node[i][j].ymax) node[i][j].ymax = *it4;
							it3++;
							it4++;
						}
						it1++;
						it2++;
					}
				}
				if (node[i][j].area == 0)
					node[i][j].area = (int)node[i][j].p[0].size();
			}
		}
	}
}


void areaSelection( layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, MultiArrayView<2, UInt8> imout, int C_area){
	int size[2] = {imin.shape()[0], imin.shape()[1]};
    imout = imin;
	
	int fh,fi,hh,ii,hh_,ii_,ch;

	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			if (node[hh][ii].children[0].empty()){
				while (node[hh][ii].area <= C_area && node[hh][ii].area!=0){
					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1){
						hh=0;
						break;
					}
				}
				if(hh<ch)
					node[hh_][ii_].setValue(imout,hh);
			}
		}
	}
}


void flooding(layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, MultiArrayView<2, UInt8> imout, int C_area){
    imout = imin;
	int size[2] = {imin.shape()[0], imin.shape()[1]};
	int fh,fi,hh,ii,hh_,ii_,ch;
	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			if (node[hh][ii].children[0].empty() && node[hh][ii].Npics==0){
                node[hh][ii].Npics ++ ;
				while (node[hh][ii].parent[0] != -1){
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
                    node[fh][fi].Npics ++;
					hh = fh;
					ii = fi;
				}
			}
		}
	}

	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			if (node[hh][ii].children[0].empty()){
				while (node[hh][ii].parent[0] != -1){
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
                    if (node[fh][fi].Npics > 1) {
                        node[hh][ii].setValue(imout, fh);
                        break;
                    }
					hh = fh;
					ii = fi;
				}
			}
		}
	}

}


/***
void lengthSelection( layer **node, Mat imin, Mat imstate, Mat imout, int C_len, int max_area, int C_circ, int op){
	// op: 1-keep elongated structure ; 2-keep round things
	int size[2] = {imin.cols,imin.rows};
	imin.copyTo(imout);
	Mat imtemp = Mat::zeros(imin.rows, imin.cols, CV_8U);
	Mat imvisited = Mat::zeros(imin.rows, imin.cols, CV_8U);

	int fh,fi,hh,ii,hh_,ii_,ch,count(0);

	for (int j=0; j<imin.rows; j++){
		for (int i=0; i<imin.cols; i++){
			if (imvisited.at<uchar>(j,i)!=0 || imin.at<uchar>(j,i)==0) continue;
			hh = imin.at<uchar>(j,i);
			ii = imstate.at<int>(j,i);
			ch = hh;
			if (node[hh][ii].children[0].empty()){
				node[hh][ii].setValue(imvisited,1);
				while (node[hh][ii].area <= max_area){
					if (node[hh][ii].length == 0 && node[hh][ii].area<=max_area){
						node[hh][ii].geoLength(imin,imtemp,node,6,node[hh][ii].p,999,999,imout,false);
					}
					if (node[hh][ii].circ1 == 0 && node[hh][ii].area<=max_area &&  C_circ>0)
						node[hh][ii].circ1 = 3.1415*node[hh][ii].length*node[hh][ii].length/(4*node[hh][ii].area);
					
					if (C_circ==0){
						if (node[hh][ii].length>C_len ) break;
					}
					else{
						if (op==1){
							if (node[hh][ii].circ1>C_circ && node[hh][ii].length>C_len) break;
						}
						else if (op==2){
							if (node[hh][ii].circ1<C_circ && node[hh][ii].length>C_len) break;
						}
					}
					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1 || hh==0){
						hh=0;
						break;
					}
				}
				if(hh<ch){
					node[hh_][ii_].setValue(imout,hh);
				}
			}
		}
	}
}


***/



void lengthSelection_cell_min( layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, MultiArrayView<2, UInt8> imout, int se, int C_len, int max_area, int C_circ){
	// op: 1-keep elongated structure ; 2-keep round things
	int size[2] = {imin.shape()[0],imin.shape()[1]};
    imout = imin;
    MultiArray<2, UInt8> imtemp(imin.shape());
    MultiArray<2, UInt8> imvisited(imin.shape());
	// Mat imtemp = Mat::zeros(imin.rows, imin.cols, CV_8U);
	// Mat imvisited = Mat::zeros(imin.rows, imin.cols, CV_8U);

	int fh,fi,hh,ii,hh_,ii_,ch,ci,count(0);
	int h_min, h_minhh, h_minhi;

	// cout<<imstate.at<int>(431, 237)<<endl;
	// int th= 92; // 111;
	// int ti= 123; // 87;

	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			if (imvisited(i,j)!=0 || imin(i,j)==0) continue;
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			ci = ii;
			h_min = hh;
			h_minhh = hh;
			h_minhi = ii;
			hh_ = hh;
			ii_ = ii;
			if (node[hh][ii].children[0].empty()){
				// if (ch==th && ci == ti) cout<<h_min<<" "<<h_minhh<<" "<<h_minhi<<endl;
				node[hh][ii].setValue(imvisited,1);
				while (node[hh][ii].area <= max_area){
					// if (ch==th && ci == ti) cout<<" "<<hh<<" "<<ii<<" "<<h_min<<" "<<h_minhh<<" "<<h_minhi<<endl;
					if (node[hh][ii].length == 0 && node[hh][ii].area<=max_area){
						node[hh][ii].geoLength(imin,imtemp,node,se,node[hh][ii].p,999,999,imout,false);
					}
					if (node[hh][ii].circ1 == 0 && node[hh][ii].area<=max_area &&  C_circ>0)
						node[hh][ii].circ1 = 3.1415*node[hh][ii].length*node[hh][ii].length/(4*node[hh][ii].area);
					
					// if (node[hh][ii].circ1<C_circ && node[hh][ii].length>C_len) 
					if (1){ // min criteria
						if (node[hh][ii].circ1>C_circ) {
							h_min = hh;
							h_minhh = hh_;
							h_minhi = ii_;
						}
					}


					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1 || hh==0){
						hh=0;
						break;
					}
				}
				if(h_min<ch){ // if(hh<ch)
					node[h_minhh][h_minhi].setValue(imout,h_min);
				} // end of update imout
			} // end of one maxima analyse
		}
	}
}



void lengthSelection_cell_max( mxt maxTree, layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, MultiArrayView<2, UInt8> imout, int se, int C_len, int max_area, int C_circ){

	areaSelection(node, imin, imstate, imout, max_area);
    imout.init(0);

	// clean maxtree mark
	int lenH = maxTree.hist[257] + 1;
	for (int i=0; i<lenH; ++i){
		for (int j=0; j<maxTree.Nnodes[i]; ++j){
			node[i][j].mark = 0;
		}
	}

	// op: 1-keep elongated structure ; 2-keep round things
	int size[2] = {imin.shape()[0],imin.shape()[1]};
	// imin.copyTo(imout);
    MultiArray<2, UInt8> imtemp(imin.shape());
    MultiArray<2, UInt8> imvisited(imin.shape());

	int fh,fi,hh,ii,hh_,ii_,ch,ci,count(0);
	int h_min, h_minhh, h_minhi;

	// cout<<imstate.at<int>(823, 1054)<<endl;
	// int th= 91; // 111;
	// int ti= 195; // 87;

	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			if (imvisited(i,j)!=0 || imin(i,j)==0) continue;
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			ci = ii;
			h_min = hh;
			h_minhh = hh;
			h_minhi = ii;
			hh_ = hh;
			ii_ = ii;
			bool F_found = false;
			// if (ch==th && ci == ti) cout<<"DD: "<<(int)imout.at<uchar>(823, 1054)<<endl;
			if (node[hh][ii].children[0].empty()){
				// cout<<" L: "<<hh<<" "<<ii<<" "<<node[64][609].mark<< endl;
				// if (ch==th && ci == ti) cout<<h_min<<" "<<h_minhh<<" "<<h_minhi<<endl;
				node[hh][ii].setValue(imvisited,1);
				while (node[hh][ii].area <= max_area && node[hh][ii].mark != 1){ // mark==1 means visited
					node[hh][ii].mark = 1;
					if (node[hh][ii].length == 0 && node[hh][ii].area<=max_area){
						node[hh][ii].geoLength(imin,imtemp,node,6,node[hh][ii].p,999,999,imout,false);
					}
					if (node[hh][ii].circ1 == 0 && node[hh][ii].area<=max_area &&  C_circ>0)
						node[hh][ii].circ1 = 3.1415*node[hh][ii].length*node[hh][ii].length/(4*node[hh][ii].area);
					// if (ch==th && ci == ti) cout<<" "<<hh<<" "<<ii<<" "<<h_min<<" "<<h_minhh<<" "<<h_minhi<<" "<<node[hh][ii].circ1<<" "<<node[hh][ii].mark<<" "<<endl;
					
					// if (node[hh][ii].circ1<C_circ && node[hh][ii].length>C_len) 

					if (1){ // max criteria
						if (F_found){
							node[hh][ii].setValue(imout,hh,-2);
						}
						else if (node[hh][ii].circ1<C_circ && node[hh][ii].length<C_len) {
							node[hh][ii].setValue(imout,hh,-2);
							F_found = true;
						}
					}


					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1 || hh==0){
						hh=0;
						// node[hh_][ii_].setValue(imout,hh,-2);
						break;
					}
				}
			}
		}
	}
}


void lengthSelection_cell_direct( mxt maxTree, layer **node, const MultiArrayView<2, UInt8> imin, const MultiArrayView<2, int> imstate, MultiArrayView<2, UInt8> imout, int se, int C_len, int max_area, float C_circ, int UO){
    //###############################
    // se: connexity
    // C_len: not used yet
    // max_area: maximum area selection, CC larger than this will not be kept.
    // C_circ: circularity criteria. 1->perfect circle. >1 -> others
    // UO: is keep the most contrasted layer
    //###############################

	areaSelection(node, imin, imstate, imout, max_area);
    imout.init(0);

	// clean maxtree mark
	int lenH = maxTree.hist[257] + 1;
	for (int i=0; i<lenH; ++i){
		for (int j=0; j<maxTree.Nnodes[i]; ++j){
			node[i][j].mark = 0;
		}
	}

	// op: 1-keep elongated structure ; 2-keep round things
	int size[2] = {imin.shape()[0],imin.shape()[1]};
	// imin.copyTo(imout);
    MultiArray<2, UInt8> imtemp(imin.shape());
    MultiArray<2, UInt8> imvisited(imin.shape());

	int fh,fi,hh,ii,hh_,ii_,ch,ci,count(0),diff,diff_,diff_h,diff_i, max_h, max_i;
	int h_min, h_minhh, h_minhi;

	// cout<<imstate.at<int>(823, 1054)<<endl;
	// int th= 91; // 111;
	// int ti= 195; // 87;

	for (int j=0; j<size[1]; j++){
		for (int i=0; i<size[0]; i++){
			if (imvisited(i,j)!=0 || imin(i,j)==0) continue;
			hh = imin(i,j);
			ii = imstate(i,j);
			ch = hh;
			ci = ii;
			h_min = hh;
			h_minhh = hh;
			h_minhi = ii;
			hh_ = hh;
			ii_ = ii;
			bool F_found = false;
			if (node[hh][ii].children[0].empty()){
				node[hh][ii].setValue(imvisited,1);
                diff = 0;
                max_h = -1;
                diff_h = -1;
                diff_i = ii;
				while (node[hh][ii].area <= max_area && node[hh][ii].mark != 1){ // mark==1 means visited
					node[hh][ii].mark = 1;
					if (node[hh][ii].length == 0 && node[hh][ii].area<=max_area){
						node[hh][ii].geoLength(imin,imtemp,node,6,node[hh][ii].p,999,999,imout,false);
					}
					if (node[hh][ii].circ1 == 0 && node[hh][ii].area<=max_area &&  C_circ>0){
						node[hh][ii].circ1 = 3.1415*node[hh][ii].length*node[hh][ii].length/(4*node[hh][ii].area);
                    }
					

					if (1){ // direct criteria
						if (node[hh][ii].circ1<C_circ ) {
                            if (UO == 0)
							    node[hh][ii].setValue(imout,hh,-2);
                            else{
                                if (diff_h == -1) {
                                    diff_h = hh;
                                    diff_i = ii;
                                    max_h = hh;
                                    max_i = ii;
                                }
                                else{
                                    diff_ = diff_h - hh;
                                    if (diff < diff_) {
                                        diff = diff_;
                                        max_h = diff_h;
                                        max_i = diff_i;
                                    }
                                    diff_h = hh;
                                    diff_i = ii;
                                }
                            }
						}
					}


					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1 || hh==0){
						hh=0;
						// node[hh_][ii_].setValue(imout,hh,-2);
						break;
					}
				}
                if (UO!=0 && max_h != -1){
                    // cout<<"DIFF "<<ch<<" "<<ci<<" "<<max_h<<" "<<max_i<<" "<<diff<<endl;;
				    node[max_h][max_i].setValue(imout,max_h);
                }
			}
		}
	}
}


/***
void lengthSelection_cell_direct(mxt maxTree, layer **node, Mat imin, Mat imstate, Mat imout, int C_len, int max_area, int C_circ, int op){

	areaSelection(node, imin, imstate, imout, max_area);

	// clean maxtree mark
	int lenH = maxTree.hist[257] + 1;
	for (int i=0; i<lenH; ++i){
		for (int j=0; j<maxTree.Nnodes[i]; ++j){
			node[i][j].mark = 0;
		}
	}

	// op: 1-keep elongated structure ; 2-keep round things
	int size[2] = {imin.cols,imin.rows};
	// imin.copyTo(imout);
	Mat imtemp = Mat::zeros(imin.rows, imin.cols, CV_8U);
	Mat imvisited = Mat::zeros(imin.rows, imin.cols, CV_8U);

	int fh,fi,hh,ii,hh_,ii_,ch,ci,count(0);
	int h_min, h_minhh, h_minhi;

	// cout<<imstate.at<int>(823, 1054)<<endl;
	// int th= 91; // 111;
	// int ti= 195; // 87;

	for (int j=0; j<imin.rows; j++){
		for (int i=0; i<imin.cols; i++){
			if (imvisited.at<uchar>(j,i)!=0 || imin.at<uchar>(j,i)==0) continue;
			hh = imin.at<uchar>(j,i);
			ii = imstate.at<int>(j,i);
			ch = hh;
			ci = ii;
			h_min = hh;
			h_minhh = hh;
			h_minhi = ii;
			hh_ = hh;
			ii_ = ii;
			// if (ch==th && ci == ti) cout<<"DD: "<<(int)imout.at<uchar>(823, 1054)<<endl;
			if (node[hh][ii].children[0].empty()){
				// cout<<" L: "<<hh<<" "<<ii<<" "<<node[64][609].mark<< endl;
				// if (ch==th && ci == ti) cout<<h_min<<" "<<h_minhh<<" "<<h_minhi<<endl;
				node[hh][ii].setValue(imvisited,1);
				while (node[hh][ii].area <= max_area && node[hh][ii].mark != 1){ // mark==1 means visited
					node[hh][ii].mark = 1;
					if (node[hh][ii].length == 0 && node[hh][ii].area<=max_area){
						node[hh][ii].geoLength(imin,imtemp,node,6,node[hh][ii].p,999,999,imout,false);
					}
					if (node[hh][ii].circ1 == 0 && node[hh][ii].area<=max_area &&  C_circ>0)
						node[hh][ii].circ1 = 3.1415*node[hh][ii].length*node[hh][ii].length/(4*node[hh][ii].area);
					// if (ch==th && ci == ti) cout<<" "<<hh<<" "<<ii<<" "<<h_min<<" "<<h_minhh<<" "<<h_minhi<<" "<<node[hh][ii].circ1<<" "<<node[hh][ii].mark<<" "<<endl;
					
					// if (node[hh][ii].circ1<C_circ && node[hh][ii].length>C_len) 

					if (1){ // direct criteria
						if (node[hh][ii].circ1<C_circ ) {
							node[hh][ii].setValue(imout,hh,-2);
						}
					}


					hh_ = hh; ii_=ii;
					fh = node[hh][ii].parent[0];
					fi = node[hh][ii].parent[1];
					hh = fh;
					ii = fi;
					if (hh==-1 || hh==0){
						hh=0;
						break;
					}
				}
			}

		}
	}
}

***/



void AreaOpening(const MultiArrayView<2, UInt8> imin,  MultiArrayView<2, UInt8> imout, int se, int T_area){
    MultiArray<2, int> imstate(imin.shape());
	int *hist = histogram(imin);
	int h=hist[256];
	int lenH = hist[257] + 1;
	//{ using namespace vigra::multi_math;
		//imstate = imstate - 2; }
	imstate.init(-2); // NEED RETEST
    mxt maxTree(imin, imstate);
	maxTree.flood_h(h, imin, imstate, se);

	layer **node = new layer* [lenH];
	for (int i=0; i<lenH; ++i){
		node[i] = new layer [maxTree.Nnodes[i]];
	}
	
	getRelations(maxTree, node, imin, imstate, lenH, T_area );
    areaSelection(node, imin, imstate, imout, T_area);

	// exportImage(imout, ImageExportInfo("imout.png"));

	maxTree.DeMT();
    delete[] hist;
	for (int i=0; i<lenH; i++)
		delete[] node[i];
	delete[] node;

	
} // end of function

void LengthOpening(const MultiArrayView<2, UInt8> imin,  MultiArrayView<2, UInt8> imout, int se, int T_area, int length, int circ){

    using namespace vigra::multi_math;

	MultiArray<2, int> imstate(imin.shape());
    int *hist = histogram(imin);
    int h=hist[256];
    int lenH = hist[257] + 1;
    imstate.init(-2); // NEED RETEST
    // imstate = imstate -2; 
    mxt maxTree (imin, imstate);
    maxTree.flood_h(h, imin, imstate, 8);

    layer **node = new layer* [lenH];
    for (int k=0; k<lenH; ++k){
        node[k] = new layer [maxTree.Nnodes[k]];
    }

    getRelations(maxTree, node, imin, imstate, lenH, T_area );
    lengthSelection_cell_max( maxTree, node, imin, imstate, imout, se,  length, T_area, circ);

	maxTree.DeMT();
    delete[] hist;
	for (int i=0; i<lenH; i++)
		delete[] node[i];
	delete[] node;

	
} // end of function




void UltimateOpening(const MultiArrayView<2, UInt8> imin, MultiArrayView<2, UInt8> imout, int se, int C_length, int delta=0){

	int *hist = histogram(imin);
	int h=hist[256];
	int lenH = hist[257]+1;
    MultiArray<2, int> imstate(imin.shape());
    MultiArray<2, UInt8> imtemp(imin.shape());
    imout.init(0);
//	{ using namespace vigra::multi_math;
//		imstate = imstate - 2; }
    imstate.init(-2); // NEED RETEST
	
	mxt maxTree(imin,imstate);
	maxTree.flood_h(h,imin, imstate, 6);

	layer **node = new layer* [lenH];
	for (int i=0; i<lenH; ++i){
		node[i] = new layer [maxTree.Nnodes[i]];
	}

	getRelations(maxTree,node,imin,imstate,lenH,0);

	//cout<<"GD "<<imstate.at<int>(269,275)<<" "<<(int)imin.at<uchar>(269,275)<<endl;
	int hh,ii,fh,fi,diff,xmin,xmax,ymin,ymax,w,l,lf,h1;
	std::list<int>::iterator it1;
	std::list<int>::iterator it2;
	for (int i=hist[257]; i>0; --i){
		for (int j=0; j<maxTree.Nnodes[i]; ++j){
			if (!node[i][j].children[0].empty()) continue;
			hh = i; ii = j;
			diff=0;
			xmax = node[i][j].xmax;
			xmin = node[i][j].xmin;
			ymax = node[i][j].ymax;
			ymin = node[i][j].ymin;
			w = xmax-xmin+1;
			h = ymax-ymin+1;
			l = max(h,w);
			h1 = hh;

			while(l<=C_length){
				lf = l;
				if (node[hh][ii].mark != 0) break;
				fh = node[hh][ii].parent[0];
				fi = node[hh][ii].parent[1];
				
				if(fh==-1){
					diff = h1;
				}
				else{
					xmax = max(xmax,node[fh][fi].xmax);
					xmin = min(xmin,node[fh][fi].xmin);
					ymax = max(ymax,node[fh][fi].ymax);
					ymin = min(ymin,node[fh][fi].ymin);
					w = xmax-xmin+1;
					h = ymax-ymin+1;
					l = max(h,w);

					if(l>(lf+delta)){
						diff = h1 - fh;
						h1 = fh;
					}
				}
				if (diff==255) cout<<"FFF "<<h1<<" "<<fh<<endl;

				//if(i==204 && j==60) cout<<hh<<" "<<diff<<endl;
				// update output image
				std::list<int> p[2];
				node[hh][ii].getPixels(node,p);
				it1 = p[0].begin();
				it2 = p[1].begin();
				while(it1!=p[0].end()){
					if(imout(*it1, *it2) < diff){
						imout(*it1, *it2) = diff;
					}
					it1++;
					it2++;
				}

				node[hh][ii].mark=1;
				if (fh ==-1) break;
				hh = fh; ii = fi;
			}
		}
	}


	delete[] hist;
	maxTree.DeMT();
	for (int i=0; i<lenH; i++)
		delete[] node[i];
	delete[] node;
}



template <class BIMAGE>
void
lengthOpening(BIMAGE const & src, 
              BIMAGE & dest,
              int se,
              int T_area, 
              int length, 
              int circ)
{
    int width = src.width();
    int height = src.height();

	MultiArray<2, UInt8> maSrc(width, height);
	MultiArray<2, UInt8> maDest(width, height);

    typename BIMAGE::const_traverser it1Current = src.upperLeft();

    // exportImage(src.upperLeft(), src.lowerRight(), src.accessor(), "/home/zhang/work/image/temp/imFRSTz1.png");

    for (int y=0; y<height; ++y){
        for (int x=0; x<width; ++x){
            maSrc(x, y) = *(it1Current + Diff2D(x,y));
        }
    }

    LengthOpening(maSrc, maDest, se, T_area, length, circ);
    
    typename BIMAGE::traverser it3Current = dest.upperLeft();

    for (int y=0; y<height; ++y){
        for (int x=0; x<width; ++x){
            *(it3Current + Diff2D(x,y)) = maDest(x, y);
        }
    }
} // end of function multiRadialSymmetryTransform



} // end of namespace
} // end of namespace

#endif
