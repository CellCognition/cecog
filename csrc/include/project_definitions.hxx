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


#ifndef PROJECT_DEFINITIONS_HXX_
#define PROJECT_DEFINITIONS_HXX_

#include <iostream>
#include <fstream>
#include <string>
#include <algorithm>
#include <vector>
#include <deque>
#include <list>
#include <queue>
#include <stack>
#include <time.h>
#include "vigra/imageiterator.hxx"
#include "vigra/stdimage.hxx"
#include "vigra/stdimagefunctions.hxx"
#include "vigra/impex.hxx"
#include "vigra/imageinfo.hxx"
#include "vigra/flatmorphology.hxx"

#include "cecog/images.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/dir.hxx"
#include "cecog/font.hxx"

using std::cout;
using std::endl;
using std::cin;
using std::string;

namespace cecog {

  struct ImageLabel
  {
    std::string text;
    Point p;
  };

  typedef std::vector<ImageLabel> LabelVec;

};

#endif /*PROJECT_DEFINITIONS_HXX_*/
