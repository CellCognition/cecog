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


#ifndef CECOG_UTILITY
#define CECOG_UTILITY

//#include "project_definitions.hxx"

#include <iostream>
#include <fstream>
#include <string>

#include <cstdlib>

#include <vigra/impex.hxx>

namespace cecog
{

    // converts int to string.
    std::string itos(int i, int digitNb = 3)    // convert int to string
    {
        std::stringstream s;
        s << i;

        std::string outputString = s.str();
        if((int)digitNb - (int)outputString.length() > 0)
        {
            std::string::size_type zeroNb = digitNb - outputString.length();
            std::string tempString(zeroNb, '0');
            outputString = tempString + outputString;
        }
        return outputString;
    } // end of itos

    // converts float to string.
    std::string ftos(float i, int digitNb = 2)  // convert float to string
    {

        std::stringstream s;
        float cut = (i*pow((float)10.0, digitNb));
        int cut_int = (int)cut;
        cut = (float)cut_int/(float)pow((float)10.0, digitNb);
        s << cut;

        std::string outputString = s.str();
        return outputString;

    } // end of itos

  inline
  bool in_range(const double value, const double cond,  const double range)
  {
    return ((value > cond-(1/range)) && (value < cond+(1/range)));
  }

  std::string int_to_string(int value)
  {
    char overhead[12];
    sprintf(overhead,"%d", value);
    std::string str = overhead;
    return str;
  }

  std::string unsigned_to_string(unsigned value)
  {
    char overhead[12];
    sprintf(overhead,"%u", value);
    std::string str = overhead;
    return str;
  }

  std::string double_to_string(double value)
  {
    char overhead[30];
    sprintf(overhead,"%.2f", value);
    std::string str = overhead;
    return str;
  }

  template <class NUM>
  std::string num_to_string(NUM in)
  {
    std::ostringstream stream;
    stream << in;
    std::string str(stream.str());
    return str;
  }

  void show_message(const std::string& msg)
  {
    std::cout << "***  " << msg << "  ***" << std::endl;
  }


  void terminate_error(std::string error_msg)
  {
    std::cerr << std::endl
    << "EXCEPTION!" << std::endl
    << "    " << error_msg << std::endl << std::endl;
    exit(-1);
  }


  std::string join_filename(std::string const & base,
                            std::string const & filename)
  {
    std::string path = base;
    if (!(base.compare(base.length()-1, 1, "/") == 0))
      path += "/";
    return path + filename;
  }


 class StopWatch
 {
 public:

   StopWatch()
   {
     reset();
   }

   void reset()
   {
     oStartTime = clock();
   }

   double measure()
   {
     return (double)(clock() - oStartTime) / CLOCKS_PER_SEC;
   }

//   clock_t stop()
//   {
//
//   }

 private:
   clock_t oStartTime;
 };

}
#endif // CECOG_UTILITY
