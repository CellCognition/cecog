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


#ifndef CECOG_DIR
#define CECOG_DIR

#include <iostream>
#include <vector>

#ifdef _WIN32
#include <io.h>
#else
#include <dirent.h>
#endif
#include <sys/types.h>
#include <sys/stat.h>

#include "cecog/utilities.hxx"
#include "cecog/shared_objects.hxx"

namespace cecog
{
  StringVector split_path_to_pattern(std::string directory)
  {
    size_t pos = directory.find_last_of("/");
    if (pos == directory.size() - 1) {
      directory = directory.substr(0, directory.size() - 1);
      pos = directory.find_last_of("/");
    }
    std::string sub = directory.substr(pos + 1, directory.npos);
    int pos2 = sub.rfind("--");
    std::string s1, s2;
    s1 = sub.substr(0, pos2);
    s2 = sub.substr(pos2 + 2, sub.npos - pos2 - 2);
    StringVector res;
    res.push_back(s1);
    res.push_back(s2);
    return res;
  }
}

#endif // CECOG_DIR
