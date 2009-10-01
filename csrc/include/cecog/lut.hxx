/*******************************************************************************

                          The CellCognition Project
                   Copyright (c) 2006 - 2009 Michael Held
                    Gerlich Lab, ETH Zurich, Switzerland

            CellCognition is distributed under the LGPL license.
                      See the LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.

*******************************************************************************/

// Author(s): Michael Held
// $Date$
// $Rev$
// $URL: https://svn.cellcognition.org/mito/trunk/include/mito/reader/wrap_lsm#$

#ifndef CECOG_LUT_HXX_
#define CECOG_LUT_HXX_

#include <algorithm>
#include <iostream>
#include <fstream>

#include "vigra/impex.hxx"
#include "vigra/basicimage.hxx"
#include "vigra/array_vector.hxx"
#include "vigra/transformimage.hxx"
#include "vigra/rgbvalue.hxx"

namespace cecog
{
  const static int LUT_SIZE = 768;
  typedef vigra::RGBValue< vigra::UInt8 > UInt8RGBValue;
  typedef vigra::ArrayVector< UInt8RGBValue > LutType;

  int readLut(std::string filename, LutType & lut)
  {
    std::ifstream file(filename.c_str(), std::ios::in | std::ios::binary);
    file.seekg(0, std::ios_base::end);
    int length = file.tellg();
    if (length >= LUT_SIZE)
    {
      file.seekg(0, std::ios_base::beg);
      char mem[LUT_SIZE];
      // set file pointer to the last 768 bytes!
      file.seekg(length-LUT_SIZE);
      file.read(mem, LUT_SIZE);
      file.close();
      for (int i=0; i < 256; i++)
        lut.push_back(UInt8RGBValue(mem[i], mem[i+256], mem[i+512]));
      return 0;
    }
    else
      return -1;
  }

  class LutFunctor
  {
    public:
      typedef vigra::UInt8 argument_type;
      typedef UInt8RGBValue result_type;

      LutFunctor(LutType const &lut)
      : lut_(lut)
      {
        if (lut_.size() != 256)
          throw "LUT size error. LUT must have 256 values!";
      }

      result_type operator()(argument_type s) const
      {
        return lut_[s];
      }

    private:
      LutType lut_;
  };


  void applyLut(vigra::UInt8Image const &imgIn, vigra::UInt8RGBImage &imgOut,
                LutType const &lut)
  {
    transformImage(srcImageRange(imgIn), destImage(imgOut),
                   LutFunctor(lut));
  }

  void lutFromSingleColor(UInt8RGBValue const & color,
                          LutType &lut)
  {
    for (int i=0; i<256; i++)
    {
      float f = i / 255.0;
      UInt8RGBValue new_color(vigra::UInt8(color.red() * f),
                              vigra::UInt8(color.green() * f),
                              vigra::UInt8(color.blue() * f));
      lut.push_back(new_color);
    }
  }

}

#endif /* CECOG_LUT_HXX_ */
