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


#ifndef __NUCLEISEGMENTATION_HXX
#define  __NUCLEISEGMENTATION_HXX

#include "project_definitions.hxx"

#include "cecog/morpho/basic.hxx"
#include "cecog/morpho/structuring_elements.hxx"
#include "cecog/morpho/label.hxx"

#include "vigra/pixelneighborhood.hxx"
#include "vigra/polygon.hxx"
#include "vigra/distancetransform.hxx"
#include "vigra/functorexpression.hxx"

#include <queue>
#include <list>
#include <fstream>

using namespace vigra;

void Label(const MultiArrayView<2, UInt8> imin, MultiArrayView<2, int> imout, int se){
	const int nl6[2][6][2] = { { {0,-1},{1,0},{0,1},{-1,1},{-1,0},{-1,-1}},
                            {{1,-1},{1,0},{1,1},{0,1},{-1,0},{0,-1}} };
	const int nl8[2][8][2] = { { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} },
                           { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} } };
	
	/* Vincent's queue algo. scan once */
	// initialization
	// threshold(imin,imout,0,0,0);
	imout.init(0);
	MultiArray<2, UInt8> imflag(imin.shape());
	int size[2] = {imin.shape()[0], imin.shape()[1] };

	std::queue<int> Qx,Qy;
	int label(0),x,y,s,t;
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


	for(int j=0;j<size[1];++j){
		for(int i=0;i<size[0];++i){
			if (imflag(i,j)==1)
				continue;
			if (imin(i,j)==0 && imflag(i,j)==0){
				imflag(i,j) = 1;
				imout(i,j)= 0;
			}
			else {
				imout(i,j) = ++label;
				imflag(i,j)=1;
				Qx.push(i);
				Qy.push(j);
			}

			while (!Qx.empty()){
				s = Qx.front();
				t = Qy.front();
				Qx.pop();
				Qy.pop();

				for (int k=0; k<se; ++k){
					x = s + nl[t%2][k][0];
					y = t + nl[t%2][k][1];
					if (x<0 || x>=size[0] || y<0 || y>=size[1]) continue;
					if (imflag(x,y)==0){
						imflag(x,y)=1;
						if (imin(x,y)!=0){
							imout(x,y) = label;
							Qx.push(x);
							Qy.push(y);
						}
					}
				}
			}
		}
	}
	

	for (int k=0; k<2; ++k){
		for (int l=0; l<se; ++l){
			delete[] nl[k][l];
		}
	}
	delete[] nl;

}

int labelCount(const MultiArrayView<2, int> imlabel){
	int n(0);
	for(int j=0;j<imlabel.shape()[1];++j){
		for(int i=0;i<imlabel.shape()[0];++i){
			if (imlabel(i,j)>n)
				n = imlabel(i,j);
		}
	}
	return n;
}



template<class Point, class T, class S>
int areaPolygon(vigra::Polygon<Point> const &p, MultiArrayView<2, T, S> &output_image){
    int N(0);
    if (!p.closed()) cout<<"areaPolygon: polygon must be closed"<<endl;

    std::vector<Point> scan_intervals;
    vigra::detail::createScanIntervals(p, scan_intervals);

    for(unsigned int k=0; k < scan_intervals.size(); k+=2)
    {

        MultiArrayIndex x    = (MultiArrayIndex)ceil(scan_intervals[k][0]),
                        y    = (MultiArrayIndex)scan_intervals[k][1],
                        xend = (MultiArrayIndex)floor(scan_intervals[k+1][0]) + 1;
        vigra_invariant(y == scan_intervals[k+1][1],
            "fillPolygon(): internal error - scan interval should have same y value.");
        // clipping
        if(y < 0)
            continue;
        if(y >= output_image.shape(1))
            break;
        if(x < 0)
            x = 0;
        if(xend > output_image.shape(0))
            xend = output_image.shape(0);
        // drawing
        for(; x < xend; ++x)
            N++;
            // output_image(x,y) = value;
    }
    return N;
} // end of function


template<class IMAGE1>
void maxima(IMAGE1 const & imin, IMAGE1 & imout){
    using namespace cecog::morpho;
    using namespace vigra::functor;
    IMAGE1 imtemp1 (imin.size());
    neighborhood2D nb(WITHOUTCENTER8, imin.size());
    ImSubtractConst(imin , imtemp1, 1);
    ImUnderBuild(destImageRange(imtemp1), srcImage(imin), nb);
    vigra::combineTwoImages(srcImageRange(imin), srcImage(imtemp1),
                           destImage(imout), Arg1()-Arg2());
} // end of function


namespace cecog {
	

  // Keep one (randomly) object (connected component) in the binary input image (imin) under a binary mask image (immask),
  // by comparing the grey level in reference image (imref).
  template<class IMAGE1>
  void objectSelection(IMAGE1 const & imin, IMAGE1 const & immask, IMAGE1 const & imref, IMAGE1 & imout, const int dist=-1){
      using namespace cecog::morpho;
      using namespace vigra;
      typedef vigra::UInt16Image IMAGE2;

      // exportImage(imref.upperLeft(), imref.lowerRight(), imref.accessor(), "/home/zhang/work/image/temp/imCref.png");
      // exportImage(imin.upperLeft(), imin.lowerRight(), imin.accessor(), "/home/zhang/work/image/temp/imCin.png");
      // exportImage(immask.upperLeft(), immask.lowerRight(), immask.accessor(), "/home/zhang/work/image/temp/imCmask.png");

      neighborhood2D nb (WITHOUTCENTER8, imin.size());

      IMAGE2 imLabel1(imin.size());
      IMAGE2 imLabel2(imin.size());

      int nObj1 = ImLabel(imin, imLabel1, nb);
      int nObj2 = ImLabel(immask, imLabel2, nb);
      // cout<<"LJLF "<<nObj1<<" "<<nObj2<<endl;

      int *cc = new int[nObj2]; // min value
      int *pp = new int[nObj2]; // min value position
      std::fill_n(cc, nObj2, 255);
      std::fill_n(pp, nObj2, -1);

      int w = imin.lowerRight().x - imin.upperLeft().x;
      int h = imin.lowerRight().y - imin.upperLeft().y;
      typename IMAGE1::const_traverser itr_imin = imin.upperLeft();
      typename IMAGE1::const_traverser itr_immask = immask.upperLeft();
      typename IMAGE1::const_traverser itr_imref = imref.upperLeft();
      typename IMAGE1::traverser itr_imout = imout.upperLeft();
      typename IMAGE2::traverser itr_label1 = imLabel1.upperLeft();
      typename IMAGE2::traverser itr_label2 = imLabel2.upperLeft();

      for (int y=0; y<h; ++y){
        for (int x=0; x<w; ++x){
            if ( *(itr_imin + Diff2D(x,y)) == 0 || *(itr_immask + Diff2D(x,y)) == 0)
                continue;
            if ( *(itr_imref + Diff2D(x,y)) <= cc[ *(itr_label2 + Diff2D(x,y)) - 1 ] ){
                cc[ *(itr_label2 + Diff2D(x,y)) - 1 ] = int(*(itr_imref + Diff2D(x,y))) ;
                pp[ *(itr_label2 + Diff2D(x,y)) - 1 ] = *(itr_label1 + Diff2D(x,y)) - 1 ;
            }
        }
      }

      int *pp2 = new int[nObj1];
      memset(pp2, 0, sizeof(int)*nObj1);
      for (int k=0; k<nObj2; ++k){
          if (pp[k] == -1) continue;
          pp2[pp[k]] = 255;
      }


      for (int y=0; y<h; ++y){
        for (int x=0; x<w; ++x){
            if ( *(itr_label1 + Diff2D(x,y)) == 0 ) continue;
            *(itr_imout + Diff2D(x,y)) = pp2[*(itr_label1 + Diff2D(x,y)) - 1];
        }
      }


      // selection based on distance
      if (dist > 0){
        vigra::FImage imtempf(imin.size()); IMAGE1 imtemp1(imin.size());
        IMAGE1 imtemp2(imin.size());
        imtemp1.init(0);
        imLabel1.init(0);
        itr_label1 = imLabel1.upperLeft();
        nObj1 = ImLabel(imout, imLabel1, nb);
        if (nObj1>0){
            vigra::distanceTransform(srcImageRange(imout), destImage(imtempf), 255, 2);
            exportImage(imout.upperLeft(), imout.lowerRight(), imout.accessor(), "/home/zhang/work/image/temp/imtempout.png");

            typename vigra::FImage::traverser itr_imtempf = imtempf.upperLeft();
            typename IMAGE1::traverser itr_imtemp = imtemp1.upperLeft();
            for (int y=0; y<h; ++y){
              for (int x=0; x<w; ++x){
                  if ( *(itr_imout + Diff2D(x,y)) == 0) continue;
                  if ( *(itr_imtempf + Diff2D(x,y)) > 255 ) *(itr_imtemp + Diff2D(x,y)) = 255;
                  else *(itr_imtemp + Diff2D(x,y)) = int( *(itr_imtempf + Diff2D(x,y)) );
              }
            }
            maxima(imtemp1, imtemp2);
            exportImage(imtemp2.upperLeft(), imtemp2.lowerRight(), imtemp2.accessor(), "/home/zhang/work/image/temp/imtempp1.png");

            // start scan
            int **nbMatrix = new int * [nObj1]; 
            bool *visited = new bool [nObj1];
            int *refValue = new int [nObj1];
            std::fill_n(visited, nObj1, false);
            std::fill_n(refValue, nObj1, 255);
            for (int i=0; i<nObj1; ++i){
                nbMatrix[i] = new int [nObj1];
                std::fill_n(nbMatrix[i], nObj1, 0);
            }

            typename IMAGE1::traverser itr_imtemp2 = imtemp2.upperLeft();
            for (int y=0; y<h; ++y){
              for (int x=0; x<w; ++x){
                  if ( *(itr_imtemp2 + Diff2D(x,y)) == 0) continue;
                  if ( visited[ (*(itr_label1 + Diff2D(x,y)) - 1) ]) continue;
                  else{
                    visited[ (*(itr_label1 + Diff2D(x,y)) - 1) ]  = true;
                    refValue[ (*(itr_label1 + Diff2D(x,y)) - 1) ]  = *(itr_imref + Diff2D(x,y));
                    int currentCandi = *(itr_label1 + Diff2D(x,y)) - 1;
                    for ( int xx = -dist; xx <= dist; ++xx){
                        for ( int yy = -dist; yy <= dist; ++yy){
                            int x_ = x + xx;
                            int y_ = y + yy;
                            if (x_<0 || x_>=w || y_<0 || y_>=h) continue; // outof range
                            if (*(itr_imtemp2 + Diff2D(x_,y_)) == 0) continue; // no candidates
                            if ( (*(itr_label1 + Diff2D(x_,y_)) - 1) == currentCandi) continue; // inside same candidate
                            nbMatrix[currentCandi][*(itr_label1 + Diff2D(x_,y_)) - 1] = 1;
                        }
                    }
                  }
              }
            }
            // cout<<"AAAA2"<<endl;
            // for (int i=0; i<nObj1; ++i){
            //     for (int j=0; j<nObj1; ++j){
            //         cout<<nbMatrix[i][j]<<" ";
            //     }
            //     cout<<endl;
            // }
            // for (int i=0; i<nObj1; ++i){
            //     cout<<refValue[i]<<" ";
            // }
            // cout<<endl;

            
            // eliminate
            bool *iskeep = new bool [nObj1];
            std::fill_n(iskeep, nObj1, true);
            for (int i=0; i<nObj1; ++i){
                if (iskeep[i] == false) continue;
                int maxP(i), maxV(refValue[i]);
	            std::queue<int> Qc;
                Qc.push(i);

                std::fill_n(visited, nObj1, false);
                visited[i] = true;
                while (!Qc.empty()){
                    int ci = Qc.front();
                    Qc.pop();
                    for (int j=0; j<nObj1; ++j){
                        if (nbMatrix[ci][j] != 0 && !visited[j]){
                            Qc.push(j);
                            visited[j] = true;
                            if (maxV > refValue[j]){
                                maxV = refValue[j];
                                iskeep[maxP] = false;
                                maxP = j;
                            }
                            else{
                                iskeep[j] = false;
                            }
                        }
                    }
                }
            }


            // for (int i=0; i<nObj1; ++i){
            //     cout<<int(iskeep[i])<<" ";
            // }
            // cout<<endl;

            // output
            for (int y=0; y<h; ++y){
              for (int x=0; x<w; ++x){
                  if ( *(itr_label1 + Diff2D(x,y)) == 0 ) continue;
                  *(itr_imout + Diff2D(x,y)) = int (iskeep[*(itr_label1 + Diff2D(x,y)) - 1]) * 255;
              }
            }



            // free ram
            for (int i=0; i<nObj1; ++i)
                delete[] nbMatrix[i];
            delete[] nbMatrix;
            delete[] visited;
            delete[] refValue;
            delete[] iskeep;
        }
      }

      delete[] cc;
      delete[] pp;
      delete[] pp2;

      
  }// end of function


  template<class IMAGE1>
  void adaptiveThreshold(IMAGE1 const & imin, IMAGE1 const & imCandi, IMAGE1 & imout, double c_low, double c_high){
      /***
       * Objective: Using previous segmented candidates to calculate thresholds, then applied on the original image to get more cell nuclei.
       * imin - original H-channel
       * imCandi - previously segmented nuclei mask
       * imout - output
       * c_low and c_higt - ratios of the histogram, used to compute 2 thresholds
       * ***/
      using namespace cecog::morpho;
      using namespace std;
      // double c_hist = 0.04;
      // double c_hist2 = 0.5;
      double S(0), cS(0), c_intensity1(255), c_intensity2(255);
      bool f1(true), f2(true);

      IMAGE1 imtemp(imin.size());
      IMAGE1 imtemp1(imin.size());
      IMAGE1 imtemp2(imin.size());
      IMAGE1 imtemp3(imin.size());

      int w = imin.lowerRight().x - imin.upperLeft().x;
      int h = imin.lowerRight().y - imin.upperLeft().y;

      imtemp.init(0);
      typename IMAGE1::const_traverser itr_imin = imin.upperLeft();
      typename IMAGE1::const_traverser itr_imCandi = imCandi.upperLeft();
      typename IMAGE1::traverser itr_imtemp = imtemp.upperLeft();

      for (int y=0; y<h; ++y){
        for (int x=0; x<w; ++x){
            if (*(itr_imCandi + Diff2D(x,y)) > 0)
                *(itr_imtemp + Diff2D(x,y)) = *(itr_imin + Diff2D(x,y));
        }
      }
          
      cecog::FindHistogram<typename IMAGE1::value_type> histogram(256);
      vigra::inspectImage(srcImageRange(imtemp), histogram);

      for (int k=1; k<histogram.size(); ++k){
          S += double(histogram[k]);
      }

      if (S==0) {
          imout.init(0);
      }
      else{
          for (int k=1; k<histogram.size(); ++k){
              cS += double(histogram[k]);
              if (cS / S > c_low && f1){
                  c_intensity1 = k;
                  f1 = false;
          }
              if (cS / S > c_high && f2){
                  c_intensity2 = k;
                  f2 = false;
              }
          }

          vigra::transformImage(srcImageRange(imin), destImage(imtemp1),
                  vigra::Threshold<typename IMAGE1::PixelType,
                                    typename IMAGE1::PixelType>
                  (0, c_intensity1, 0, 255));
    
          vigra::transformImage(srcImageRange(imin), destImage(imtemp2),
                  vigra::Threshold<typename IMAGE1::PixelType,
                                    typename IMAGE1::PixelType>
                  (0, c_intensity2, 0, 255));
    

          //######
          // std::cout<<c_low<<" "<<c_intensity1<<" "<<c_high<<" "<<c_intensity2<<endl;
          // exportImage(imtemp1.upperLeft(), imtemp1.lowerRight(), imtemp1.accessor(), "/home/zhang/work/image/temp/imtempp1.png");
          // exportImage(imtemp2.upperLeft(), imtemp2.lowerRight(), imtemp2.accessor(), "/home/zhang/work/image/temp/imtempp2.png");
          //######

          neighborhood2D nb (WITHOUTCENTER8, imin.size());
          ImInfimum(srcImageRange(imtemp1), srcImage(imtemp2), destImage(imtemp3));
          ImUnderBuild(destImageRange(imtemp3), srcImage(imtemp2), nb);
          

          ImInfimum(srcImageRange(imCandi), srcImage(imtemp3), destImage(imtemp1));
          ImUnderBuild(destImageRange(imtemp1), srcImage(imtemp3), nb);

          combineTwoImages(srcImageRange(imtemp3), srcImage(imtemp1), 
                            destImage(imtemp2), Arg1()-Arg2());

          copyImage(srcImageRange(imtemp2), destImage(imout) );

      } // end of else
  } // end of function
 

template <class T1, class S1>
void CandidateAnalysis(const MultiArrayView<2, T1, S1> imCandi, const MultiArrayView<2, T1, S1> imOrig, MultiArrayView<2, T1, S1> imOut, const int cls, const double (&coef)[10]){

const int nl6[2][6][2] = { { {0,-1},{1,0},{0,1},{-1,1},{-1,0},{-1,-1}},
                            {{1,-1},{1,0},{1,1},{0,1},{-1,0},{0,-1}} };
const int nl8[2][8][2] = { { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} },
                           { {1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1} } };
	
	class candidate{
		public:
			int p[2];
			double mean;
			double area;
			double areaConvex;
			ArrayVector<TinyVector<double,2> > pix;
			
			candidate(){
				p[0] = -1;
				p[1] = -1;
				mean = 0;
				area = 0;
				areaConvex = 0;
			}
	};
	
	class frontier{
		public:
			int p[2];
			int cat;
			double mean;
			double area;
			double areaRatioNb;
			double diffmean1;
			double diffmean2;
			double diffmean3;
			std::vector<int> neighbor;
			double areaConvex;
			double convex;
			double convexN1;
			double convexN2;
			ArrayVector<TinyVector<double,2> > pix;
			
			frontier(){
				p[0] = -1;
				p[1] = -1;
				cat = -1;
				mean = 0;
				area = 0;
				diffmean1 = -1;
				diffmean2 = -1;
				diffmean3 = -1;
				areaConvex = -1;
				convex = -1;
				convexN1 = -1;
				convexN2 = -1;
			}
	};	
	 
	int width = imCandi.width();
    int height = imCandi.height();
    int imsize[2] = {width, height};
    
    MultiArray<2, UInt8> imtemp1(width, height);
    MultiArray<2, UInt8> imtemp2(width, height);
    MultiArray<2, UInt8> imContour(width, height);
    
	MultiArray<2, int> imLabel1(width, height); 
	MultiArray<2, int> imLabel2(width, height); 
	
	MultiArray<2, vigra::RGBValue<UInt8> > imoutC(width, height); 
	
	 
    Label(imCandi, imLabel1, 8);
    // imtemp1 = imLabel1 % 256;
	// exportImage(imtemp1, ImageExportInfo("z4_label.png"));
    int N_candi = labelCount(imLabel1);
    candidate *candis = new candidate[N_candi];

    TinyVector<double, 2> pix;
    for (int i=0; i<imsize[0]; ++i){
        for (int j=0; j<imsize[1]; ++j){
            if (imLabel1(i,j) == 0) continue;
            candis[imLabel1(i,j) - 1].mean += imOrig(i,j);
            candis[imLabel1(i,j) - 1].area ++;
            pix[0] = i;
            pix[1] = j;
            candis[imLabel1(i,j) - 1].pix.push_back(pix);
        }
    }

    for (int k=0; k<N_candi; ++k){
        candis[k].mean /= candis[k].area;

        ArrayVector<TinyVector<double,2> > bb;
        vigra::Polygon< TinyVector<double, 2> > poly;
        if (candis[k].pix.size()<10)
            candis[k].areaConvex = candis[k].pix.size();
        else {
            convexHull(candis[k].pix, bb);
            for (int l=0; l<bb.size(); ++l){
                poly.push_back(bb[l]);
            }
            candis[k].areaConvex = areaPolygon(poly, imtemp1);
        }
    }

    // 5. frontier analysis
    int **neighborList = new int*[N_candi];
    for (int k=0; k<N_candi; ++k){
        neighborList[k] = new int[N_candi];
    }

    imtemp1 = imCandi;
    std::queue<int> Qx, Qy;
    int x,y,x0,y0;
	MultiArray<2, int> imstate(imOrig.shape());
    for (int j=0; j<imsize[1]; ++j){
        for (int i=0; i<imsize[0]; ++i){
            if (imLabel1(i,j)==0) continue;
            for (int k=0; k<8; ++k){
                x = i+nl8[0][k][0];
                y = j+nl8[0][k][1];
                if (x<0 || x>=imsize[0]) continue;
                if (y<0 || y>=imsize[1]) continue;
                if (imstate(x,y) != 0) continue;
                if (imLabel1(x,y) == 0){
                    Qx.push(x);
                    Qy.push(y);
                    imstate(x,y) = 1;
                    imtemp1(x,y) = 100;
                }
            }
        }
    }

    std::list<int> temp;
    std::list<int>::iterator it;
    while (!Qx.empty()){
        x0 = Qx.front();
        y0 = Qy.front();
        Qx.pop();
        Qy.pop();
        temp.clear();
        for (int k=0; k<8; ++k){
            x = x0+nl8[0][k][0];
            y = y0+nl8[0][k][1];
            if (x<0 || x>=imsize[0]) continue;
            if (y<0 || y>=imsize[1]) continue;
            if (imLabel1(x,y) == 0) continue;
            bool f=true;
            for (it = temp.begin(); it != temp.end(); ++it){
                if (*it == imLabel1(x,y)) {f=false; break;}
            }
            if (f) {
                temp.push_back(imLabel1(x,y));
            }
        }
        if (temp.size() == 2)
            imtemp1(x0,y0) = 50;
        else if (temp.size() > 2)
            imtemp1(x0,y0) = 51;
    }
    imContour = imtemp1;
	// exportImage(imContour, ImageExportInfo("z5_temp.png"));

        //#####################################
        for (int k=0; k<imOrig.size(); ++k){
            if (imtemp1[k] == 50){
                imoutC[k].red() = 255;
                imoutC[k].green() = 0;
                imoutC[k].blue() = 0;
            }
            else if (imtemp1[k] == 51){
                imoutC[k].red() = 0;
                imoutC[k].green() = 0;
                imoutC[k].blue() = 255;
            }
            else if (imtemp1[k] == 100){
                imoutC[k].red() = 0;
                imoutC[k].green() = 255;
                imoutC[k].blue() = 0;
            }
            else {
                imoutC[k].red() = imOrig[k];
                imoutC[k].green() = imOrig[k];
                imoutC[k].blue() = imOrig[k];
            }
        }
	    
	    // exportImage(imoutC, ImageExportInfo("z5_result.png"));
        //#####################################


    imtemp1.init(0);
    for (int k=0; k<imOrig.size(); ++k){
        if (imContour[k] == 50 || imContour[k]==51)
            imtemp1[k] = 255;
    }
    Label(imtemp1,imLabel2,8);
    int N_lines = labelCount(imLabel2);
    // imtemp2 = imLabel2 % 256; 
	// exportImage(imtemp2, ImageExportInfo("z5_frontier_label.png"));

    frontier *lines = new frontier[N_lines];


    for (int j=0; j<imsize[1]; ++j){
        for (int i=0; i<imsize[0]; ++i){
            if (imLabel2(i,j)==0) continue;
            lines[imLabel2(i,j) - 1].mean += imOrig(i,j);
            lines[imLabel2(i,j) - 1].area += 1;
            pix[0] = i;
            pix[1] = j;
            lines[imLabel2(i,j) - 1].pix.push_back(pix);

            for (int k=0; k<8; ++k){
                x = i+nl8[0][k][0];
                y = j+nl8[0][k][1];
                if (x<0 || x>=imsize[0]) continue;
                if (y<0 || y>=imsize[1]) continue;
                if (imLabel1(x,y) == 0) continue;
                
                bool f=true;
                for (int k=0; k<lines[imLabel2(i,j) - 1].neighbor.size(); ++k){
                    if (lines[imLabel2(i,j) - 1].neighbor[k] == imLabel1(x,y)){
                        f = false;
                        break;
                    }
                }
                if (f) lines[imLabel2(i,j) - 1].neighbor.push_back(imLabel1(x,y));
            }
        }
    }

    // std::ofstream myfile;
    // myfile.open("/home/zhang/work/image/temp/features.txt");

    for (int k=0; k<N_lines; ++k){
        lines[k].mean /= lines[k].area;

        if (lines[k].neighbor.size() == 2){
            int candi1 = lines[k].neighbor[0] - 1;
            int candi2 = lines[k].neighbor[1] - 1;
            double maxCandi = max(candis[candi1].mean, 
                    candis[candi2].mean);
            double minCandi = min(candis[candi1].mean, 
                    candis[candi2].mean);

            double maxArea = max(candis[candi1].area, 
                    candis[candi2].area);
            double minArea = min(candis[candi1].area, 
                    candis[candi2].area);

            lines[k].diffmean1 = lines[k].mean - minCandi;
            lines[k].diffmean2 = lines[k].mean - maxCandi;
            lines[k].diffmean3 = maxCandi- minCandi;

            lines[k].areaRatioNb = minArea / maxArea;

            double convx1 = candis[candi1].area / candis[candi1].areaConvex;
            double convx2 = candis[candi2].area / candis[candi2].areaConvex;

            ArrayVector<TinyVector<double,2> > mergePix;
            for (int l=0; l<candis[candi1].pix.size(); ++l){
                mergePix.push_back(candis[candi1].pix[l]);
            }
            for (int l=0; l<candis[candi2].pix.size(); ++l){
                mergePix.push_back(candis[candi2].pix[l]);
            }
            for (int l=0; l<lines[k].pix.size(); ++l){
                mergePix.push_back(lines[k].pix[l]);
            }

            ArrayVector<TinyVector<double,2> > bb;
            vigra::Polygon< TinyVector<double, 2> > poly;
            if (mergePix.size()<10)
                lines[k].areaConvex = mergePix.size();
            else {
                convexHull(mergePix, bb);
                for (int l=0; l<bb.size(); ++l){
                    poly.push_back(bb[l]);
                }
                
                lines[k].areaConvex = areaPolygon(poly,imtemp1);
            }
            lines[k].convex = mergePix.size() / lines[k].areaConvex;
            if (convx1 > convx2) {
                lines[k].convexN1 = convx1;
                lines[k].convexN2 = convx2;
            }
            else{
                lines[k].convexN1 = convx2;
                lines[k].convexN2 = convx1;
            }

            // myfile << lines[k].diffmean1<<" "<<lines[k].diffmean2<<" "<<lines[k].diffmean3
            //     <<" "<<lines[k].convex<<" "<<lines[k].convexN1<<" "<<lines[k].convexN2
            //     <<" "<<lines[k].convex - lines[k].convexN1<<" "
            //     <<lines[k].convex - lines[k].convexN2<<" "<<lines[k].areaRatioNb<<" C1\n";

            //// Classification Logistic regression
            double features[9] = { lines[k].diffmean1, lines[k].diffmean2, lines[k].diffmean3
                , lines[k].convex, lines[k].convexN1, lines[k].convexN2
                , lines[k].convex - lines[k].convexN1, lines[k].convex - lines[k].convexN2
                , lines[k].areaRatioNb };
            double mean_norm[9] = {19.9194, -2.9981, 22.9174, 0.8164, 0.9226, 0.8065, -0.0548,
                -0.0415, 0.4792};
            double std_norm[9] = {16.3533, 14.1942, 17.3133, 0.1094, 0.0609, 0.0948, 0.1175, 
                0.1205, 0.2820};

            if (cls==0){
                // double coefs_norm[10] = {0.506, -0.1509, 0.6016, -1.3171, -0.2314, -0.017, 
                //     -1.0371, -1.1807, 0.5046, 2.675};
                double coefs_norm[10] = {0.5034, -0.1516, 0.5997, -1.3089, -0.1904, -0.0265, 
                    -0.9521, -1.3303, 0.5, 2.6748};

                double f(0);
                for (int kk=0; kk<9; ++kk){
                    f += coefs_norm[kk] * ((features[kk] - mean_norm[kk]) / std_norm[kk]);
                }
                f += coefs_norm[9];

                double p = 1 / (1 + exp(-f));
                
                if (p<0.5) lines[k].cat = 1;
                else lines[k].cat = 0;
            }

            else if (cls==1){
                double coefs_norm[10] = {-3.8721, -1.5319, -2.4014, 5.1876, -1.9299, -0.3491, 4.7345, 
                    6.0479, 0.5598, -7};
                double f(0);
                for (int kk=0; kk<9; ++kk){
                    f += coef[kk] * ((features[kk] - mean_norm[kk]) / std_norm[kk]);
                }
                f += coefs_norm[9];

                if (f>0.0) lines[k].cat = 1;
                else lines[k].cat = 0;
            }
            else {
                std::cout<<"WRONG CLASSIFIER TYPE!!!"<<std::endl;
            }
        }
        else{
            // myfile <<"Delete this line\n";
        }
    }
    // myfile.close();


    // AreaOpening(imCandi, imtemp1, 8, 9);
    // imCandi = imtemp1;
        
    copyImage(imCandi, imOut);
	for (int k=0; k<imOrig.size(); ++k){
		if (imLabel2[k] == 0) continue;
		if (lines[imLabel2[k] - 1].cat != 1) continue;
		else {
			imoutC[k].red() = 0;
			imoutC[k].green() = 0;
			imoutC[k].blue() = 255;
			imOut[k] = 255;
		}
	}


    for (int k=0; k<N_candi; ++k){
        delete[] neighborList[k];
    }
    delete[] neighborList;
    delete[] candis;
    delete[] lines;
    // exportImage(imoutC, ImageExportInfo("/home/zhang/work/image/temp/z6_result_LR.png"));
    // exportImage(imCandi, ImageExportInfo("/home/zhang/work/image/temp/z6_final_candi.png"));
 } // end of function
 
 
template <class BIMAGE>
void candidateAnalysis(BIMAGE const & imCandi, BIMAGE const & imOrig, BIMAGE & dest, const int cls, const double (&coef)[10]){
    int width = imCandi.width();
    int height = imCandi.height();

	MultiArray<2, UInt8> maCandi(width, height);
	MultiArray<2, UInt8> maOrig(width, height);
	MultiArray<2, UInt8> maDest(width, height);

    typename BIMAGE::const_traverser it1 = imCandi.upperLeft();
    typename BIMAGE::const_traverser it2 = imOrig.upperLeft();
    typename BIMAGE::traverser it3 = dest.upperLeft();

    // exportImage(src.upperLeft(), src.lowerRight(), src.accessor(), "/home/zhang/work/image/temp/imFRSTz1.png");

    for (int y=0; y<height; ++y){
        for (int x=0; x<width; ++x){
            maCandi(x, y) = *(it1 + Diff2D(x,y));
            maOrig(x, y) = *(it2 + Diff2D(x,y));            
        }
    }

    CandidateAnalysis(maCandi, maOrig, maDest, cls, coef);
    
    for (int y=0; y<height; ++y){
        for (int x=0; x<width; ++x){
            *(it3 + Diff2D(x,y)) = maDest(x, y);
        }
    }
}


}; // end of namespace cecog
#endif /*nuclearsegmentation_hxx*/
