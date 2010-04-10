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


#ifndef CECOG_CONFIG
#define CECOG_CONFIG

namespace cecog
{

  class Config
  {
  public:
    static std::string strFontFilepath;

  };

  std::string Config::strFontFilepath = "font12.png";

} // namespace cecog

#endif // CECOG_CONFIG
