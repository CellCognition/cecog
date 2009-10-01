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

#ifndef CECOG_TRANSFORMS_HXX_
#define CECOG_TRANSFORMS_HXX_

#include "vigra/numerictraits.hxx"

namespace cecog
{
  template <class SrcValueType, class DestValueType>
    class ProtectedLinearRangeMapping
    {
    public:
      typedef SrcValueType argument_type;
      typedef DestValueType result_type;
      typedef typename vigra::NumericTraits<DestValueType>::RealPromote Multiplier;

      ProtectedLinearRangeMapping(argument_type srcMin, argument_type srcMax,
                            result_type destMin, result_type destMax)
        : minV(destMin), maxV(destMax)
      {
        ratio = (srcMax == srcMin)
              ? vigra::NumericTraits<Multiplier>::one()
              : (destMax - destMin) / (srcMax - srcMin);
        offset = destMin / ratio - srcMin;
      }

      result_type operator()(argument_type s) const
      {
        float res = ratio * (s + offset);
        if (res > maxV)
          return maxV;
        else if (res < minV)
          return minV;
        else
          return vigra::NumericTraits<result_type>::fromRealPromote(res);
      }
    private:
      result_type minV, maxV;
      Multiplier offset, ratio;
    };

}

#endif /* CECOG_TRANSFORMS_HXX_ */
