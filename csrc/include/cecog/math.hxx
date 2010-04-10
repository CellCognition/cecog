/*******************************************************************************

                           The CellCognition Project
                   Copyright (c) 2006 - 2010 by Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                             www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL$


#ifndef CECOG_MATH
#define CECOG_MATH

#include <iostream>
#include <map>
#include <vector>
#include <string>
#include <algorithm>

#include "vigra/impex.hxx"
#include "vigra/mathutil.hxx"

// sqr macro: sqr((a + b)) = (a+b)*(a+b)
#define sqr(a) (a * a)

#define SQRT_PI sqrt(M_PI)

namespace cecog
{
    inline
    double diffDistanceNoSqrt(vigra::Diff2D const & a, vigra::Diff2D const & b)
    {
        vigra::Diff2D diff = b - a;
    return sqr(diff.x) + sqr(diff.y);
    }

    inline
    double diffDistance(vigra::Diff2D const & a, vigra::Diff2D const & b)
    {
    return sqrt(diffDistanceNoSqrt(a,b));
    }

}

#endif // CECOG_MATH
