/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Thomas Walter
// $Date$
// $Rev$
// $URL$


#ifndef MORPHO_LABEL_HXX_
#define MORPHO_LABEL_HXX_

#include "project_definitions.hxx"

namespace cecog {
namespace morpho {

  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  int ImLabel(Iterator1 srcUpperLeft, Iterator1 srcLowerRight, Accessor1 srca,
          Iterator2 destUpperLeft, Accessor2 desta,
        NBTYPE & nbOffset)
  {
    std::queue<Diff2D> Q;

    int label = 1;

    int width  = srcLowerRight.x - srcUpperLeft.x;
      int height = srcLowerRight.y - srcUpperLeft.y;

    typedef typename NBTYPE::ITERATORTYPE ITERATORTYPE;
    typedef typename NBTYPE::SIZETYPE SIZETYPE;

    Diff2D o0(0,0);

    for(o0.y = 0; o0.y < height; ++o0.y)
    {
      for(o0.x = 0; o0.x < width; ++o0.x)
      {
        if( (desta(destUpperLeft,o0) == 0) && (srca(srcUpperLeft, o0) != 0))
        {
          desta.set(label, destUpperLeft, o0);
          Q.push(o0);
          while(!Q.empty())
          {
            // take the first pixel out of the queue.
            Diff2D o1 = Q.front(); Q.pop();

            // look to the neighborhood.
            for(ITERATORTYPE iter = nbOffset.begin();
              iter != nbOffset.end();
              ++iter)
            {
              Diff2D o2 = o1 + *iter;
              // if the neighbor is not outside the image
              if(!nbOffset.isOutsidePixel(o2))
              {
                if( (srca(srcUpperLeft,o2) != 0) && (desta(destUpperLeft,o2) == 0))
                {
                  desta.set(label, destUpperLeft, o2);
                  Q.push(o2);
                }
              }  // end if not outside pixel
            }  // end for (neighborhood)
          } // end while !Q.empty()

          label++;
        } // end if controlimage != DONE
      } // end x-loop
    }  // end y-loop

    return(label-1);
  } // end of function ImLabel

  // ImLabel
  template<class Iterator1, class Accessor1,
       class Iterator2, class Accessor2,
       class NBTYPE>
  inline
  int ImLabel(vigra::triple<Iterator1, Iterator1, Accessor1> src,
        vigra::pair<Iterator2, Accessor2> dest,
        NBTYPE & neighborOffset)
  {
    return(ImLabel(src.first, src.second, src.third,
                 dest.first, dest.second,
                neighborOffset));
  }

  template<class Image1, class Image2, class NB>
  inline
  int ImLabel(const Image1 & imin, Image2 & imout, NB & nb)
  {
    return(ImLabel(srcImageRange(imin), destImage(imout), nb));
  }



};
};

#endif /*MORPHO_LABEL_HXX_*/
