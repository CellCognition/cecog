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


namespace cecog {


  // Keep one (randomly) object (connected component) in the binary input image (imin) under a binary mask image (immask),
  // by comparing the grey level in reference image (imref).
  template<class IMAGE1>
  void objectSelection(IMAGE1 const & imin, IMAGE1 const & immask, IMAGE1 const & imref, IMAGE1 & imout){
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

      int xx = 638, yy = 17;
      int pxy = *(itr_label1 + Diff2D(xx,yy)) - 1;

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


      delete[] cc;
      delete[] pp;
      delete[] pp2;

      
  }


}; // end of namespace cecog
#endif /*nuclearsegmentation_hxx*/
