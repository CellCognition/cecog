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

  /**
   * return a vector of filenames of a given `directory`
   * and a suffix `file_type`
   */
  //StringVector get_filenames_from_dir(std::string const & directory,
  //                                    std::string const & file_type)
  //{
  //  StringVector names;
  //  struct dirent **namelist;
  //  struct stat st;
  //  int n;

  //  n = scandir(directory.c_str(), &namelist, 0, alphasort);
  //  if (n < 0)
  //    perror("scandir");
  //  else
  //  {
  //    while(n--)
  //    {
  //      std::string name = namelist[n]->d_name;
  //      std::string full_name = join_filename(directory, name);
  //      stat(full_name.c_str(), &st);

  //      // ignore sub-directories
  //      if (!S_ISDIR(st.st_mode))
  //      {
  //        // check, if the file has given suffix `file_type`
  //        int pos = name.find_last_of(".");
  //        if ((pos > 0) && (name.substr(pos+1) == file_type))
  //          names.push_back(name);
  //      }
  //      free(namelist[n]);
  //    }
  //    free(namelist);
  //  }
  //  if (!names.size())
  //    terminate_error("No '*."+file_type+"' files found in directory '"+
  //                    directory+"'.");
  //  return names;
  //}

  ///**
  // * return a subset of filenames matching a given `pattern`
  // * IN FRONT OF the suffix
  // *
  // * example:
  // * "abcdefgXXX.suffix": will match (where "XXX" is the pattern)
  // * "abcdXXXefg.suffix": will NOT match!
  // */
  //StringVector get_files_from_pattern(StringVector const & names,
  //                                    std::string const & pattern)
  //{
  //  StringVector l_names;
  //  for (int i=0; i<names.size(); i++)
  //  {
  //    int pos = names[i].find_last_of(".");
  //    int len = pattern.length();
  //    if (names[i].substr(pos-len, len) == pattern)
  //      l_names.push_back(names[i]);
  //  }
  //  if (!l_names.size())
  //    terminate_error("No files found with matching pattern '"+
  //                    pattern+"'.");
  //  return l_names;
  //}

  StringVector split_path_to_pattern(std::string directory)
  {
    int pos = directory.find_last_of("/");
    if (pos == directory.size() - 1)
    {
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
