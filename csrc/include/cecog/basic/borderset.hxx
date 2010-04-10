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


#ifndef BORDERSET_HXX_
#define BORDERSET_HXX_

namespace cecog{
namespace morpho{

    template<class Iterator, class Accessor>
    void ImBorderSet(Iterator destUpperLeft, Iterator destLowerRight, Accessor desta,
                unsigned borderWidth, typename Accessor::value_type value)
    {
        vigra::Diff2D imgSize(destLowerRight - destUpperLeft);

        Iterator destul(destUpperLeft);

        for(int y = 0; y < borderWidth; ++y, ++destul.y)
        {
            Iterator dcurrent(destul);
            for(; dcurrent.x < destLowerRight.x; ++dcurrent.x)
                desta.set(value, dcurrent);
        }

        destul = destUpperLeft + vigra::Diff2D(0,imgSize.y - borderWidth);

        for(; destul.y < destLowerRight.y; ++destul.y)
        {
            Iterator dcurrent(destul);
            for(; dcurrent.x < destLowerRight.x; ++dcurrent.x)
                desta.set(value, dcurrent);
        }

        destul = destUpperLeft;
        for(int x = 0; x < borderWidth; ++x, ++destul.x)
        {
            Iterator dcurrent(destul);
            for(; dcurrent.y < destLowerRight.y; ++dcurrent.y)
                desta.set(value, dcurrent);
        }

        destul = destUpperLeft + vigra::Diff2D(imgSize.x - borderWidth, 0);
        for(; destul.x < destLowerRight.x; ++destul.x)
        {
            Iterator dcurrent(destul);
            for(; dcurrent.y < destLowerRight.y; ++dcurrent.y)
                desta.set(value, dcurrent);
        }

    }

    ////////////////////////
    // using factories:
    template<class Iterator1, class Accessor1>
    inline
    void ImBorderSet(vigra::triple<Iterator1, Iterator1, Accessor1> src,
                     unsigned borderWidth, typename Accessor1::value_type value)
    {

        ImBorderSet(src.first, src.second, src.third, borderWidth, value);

    } // end of ImBorderSet


};
};
#endif /*BORDERSET_HXX_*/
