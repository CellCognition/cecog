/*******************************************************************************

                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
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

#ifndef CECOG_PYTHON_WRAP_CONTAINERS_HXX_
#define CECOG_PYTHON_WRAP_CONTAINERS_HXX_

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/str.hpp>
#include <boost/python/overloads.hpp>
#include <boost/python/args.hpp>

#include "cecog/containers.hxx"

using namespace boost::python;

namespace cecog
{
  namespace python
  {
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(apply_feature_overloads, applyFeature, 1, 2)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(export_rgb_overloads, exportRGB, 1, 3)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(draw_ellipse_overloads, drawEllipse, 4, 6)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(connect_objects_overloads, connectObjects, 2, 4)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(mark_objects_overloads1, markObjects, 1, 6)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(mark_objects_overloads2, markObjects, 0, 5)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(show_labels_overloads, showLabels, 2, 3)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(export_image_overloads, exportImage, 1, 2)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(export_binary_overloads, exportBinary, 1, 2)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(export_object_overloads, exportObject, 3, 4)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(threshold_overloads, threshold, 1, 2)
    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(draw_contours_byids_overloads, drawContoursByIds, 3, 5)

    template <class OBJECT_CONTAINER>
    dict object_wrapper(OBJECT_CONTAINER &c)
    {
      dict result;
      typename OBJECT_CONTAINER::ObjectMap::iterator it;
      for (it = c.objects.begin(); it != c.objects.end(); ++it)
        result[(*it).first] = (*it).second;
      return result;
    }

    template <class OBJECT_CONTAINER>
    list pyCrackCoordinates(OBJECT_CONTAINER &c, unsigned objId)
    {
      list result;
      typename OBJECT_CONTAINER::PositionList posList = c.getCrackCoordinates(objId);
      typename OBJECT_CONTAINER::PositionList::iterator it = posList.begin();
      for (; it != posList.end(); it++)
        result.append(make_tuple((*it).x, (*it).y));
      return result;
    }
  }
}

//void setUnsignedParameterVector(std::vector<unsigned> const &params, std::string feature)

void wrap_containers()
{
  using namespace cecog::python;
  typedef cecog::ObjectContainerBase<8> _ObjectContainerBase;

  void (_ObjectContainerBase::*fx1)(std::vector<unsigned>, cecog::RGBValue, bool, bool, bool, bool) = &_ObjectContainerBase::markObjects;
  void (_ObjectContainerBase::*fx2)(cecog::RGBValue, bool, bool, bool, bool) = &_ObjectContainerBase::markObjects;

  class_< _ObjectContainerBase >("ObjectContainerBase")
    .def("applyFeature", &_ObjectContainerBase::applyFeature,
         apply_feature_overloads())
    .def("deleteFeature", &_ObjectContainerBase::deleteFeature)
    .def("deleteFeatureCategory", &_ObjectContainerBase::deleteFeatureCategory)
    .def("markObjects", fx1, mark_objects_overloads1(args("color", "quad", "showIds", "fill", "force")))
    .def("markObjects", fx2, mark_objects_overloads2(args("color", "quad", "showIds", "fill", "force")))
    .def("makeRGB", &_ObjectContainerBase::makeRGB)
    .def("eraseRGB", &_ObjectContainerBase::eraseRGB)
    .def("addExtraImage", &_ObjectContainerBase::addExtraImage)
    .def("combineExtraRGB", &_ObjectContainerBase::combineExtraRGB)
    .def("connectObjects", &_ObjectContainerBase::connectObjects,
         connect_objects_overloads())
    .def("drawEllipse", &_ObjectContainerBase::drawEllipse,
         draw_ellipse_overloads())
    .def("showLabels", &_ObjectContainerBase::showLabels,
         show_labels_overloads(args("ids", "labels", "force")))
    .def("drawContoursByIds", &_ObjectContainerBase::drawContoursByIds<vigra::UInt8Image>,
         (arg("ids"), arg("color"), arg("imgOut"), arg("quad")=false, arg("fill")=false),
         "draw contours by given ID list to separate image")
    .def("drawContoursByIds", &_ObjectContainerBase::drawContoursByIds<vigra::UInt8RGBImage>,
         (arg("ids"), arg("color"), arg("imgOut"), arg("quad")=false, arg("fill")=false),
         "draw contours by given ID list to separate image")
    .def("drawLabels", &_ObjectContainerBase::drawLabels<vigra::UInt8Image>)
    .def("drawLabels", &_ObjectContainerBase::drawLabels<vigra::UInt8RGBImage>)
    .def("drawLabelsByIds", &_ObjectContainerBase::drawLabelsByIds<vigra::UInt8Image>)
    .def("drawLabelsByIds", &_ObjectContainerBase::drawLabelsByIds<vigra::UInt8RGBImage>)
    .def("drawTextsByIds", &_ObjectContainerBase::drawTextsByIds<vigra::UInt8Image>)
    .def("drawTextsByIds", &_ObjectContainerBase::drawTextsByIds<vigra::UInt8RGBImage>)
    .def("exportRGB", &_ObjectContainerBase::exportRGB,
         export_rgb_overloads(args("filepath", "compression", "force")))
    .def("exportImage", &_ObjectContainerBase::exportImage,
         export_image_overloads())
    .def("exportLabelImage", &_ObjectContainerBase::exportLabelImage)
    .def("exportBinary", &_ObjectContainerBase::exportBinary,
         export_binary_overloads())
    .def("exportObject", &_ObjectContainerBase::exportObject,
         export_object_overloads())
    .def("getBinary", &_ObjectContainerBase::getBinary)
    .def("getCrackCoordinates", &pyCrackCoordinates<_ObjectContainerBase>)
    .def("getLabels", &_ObjectContainerBase::getLabels)
    .def("delObject", &_ObjectContainerBase::delObject)
    .def("getObjects", &object_wrapper<_ObjectContainerBase>)
    .def("resetHaralick", &_ObjectContainerBase::resetHaralick)
    .def("resetGranulometry", &_ObjectContainerBase::resetGranulometry)
    .def("addHaralickValue", &_ObjectContainerBase::addHaralickValue)
    .def("addGranulometryValue", &_ObjectContainerBase::addGranulometryValue)
    .def("printHaralickDist", &_ObjectContainerBase::printHaralickDist)
    .def("printGranulometrySizes", &_ObjectContainerBase::printGranulometrySizes)
    .def_readwrite("debug_folder",
                   &_ObjectContainerBase::debug_folder)
    .def_readwrite("debug_prefix",
                   &_ObjectContainerBase::debug_prefix)
    .def_readwrite("debug",
                   &_ObjectContainerBase::debug)
    .def_readwrite("spot_diameter",
                   &_ObjectContainerBase::spot_threshold)
    .def_readwrite("spot_threshold",
                   &_ObjectContainerBase::spot_diameter)
    .def_readwrite("haralick_levels",
                   &_ObjectContainerBase::haralick_levels)
    .def_readwrite("haralick_distance",
                   &_ObjectContainerBase::haralick_distance)
    .def_readwrite("levelset_levels",
                   &_ObjectContainerBase::levelset_levels)
    .def_readonly("width",
                  &_ObjectContainerBase::width)
    .def_readonly("height",
                  &_ObjectContainerBase::height)
    .def_readwrite("img_labels",
                   &_ObjectContainerBase::img_labels)
    .def_readwrite("img",
                   &_ObjectContainerBase::img)
    .def_readwrite("img_rgb",
                   &_ObjectContainerBase::img_rgb)
  ;
  register_ptr_to_python< std::auto_ptr<_ObjectContainerBase> >();



  typedef cecog::ObjectContainer<8> _ObjectContainer;

  class_< _ObjectContainer, bases<_ObjectContainerBase> >
    ("ObjectContainer", init< _ObjectContainer::image_type & >())
    .def("threshold", &_ObjectContainer::threshold,
         threshold_overloads())
    .def("localThresholdCaching", &_ObjectContainer::localThresholdCaching)
    .def("label", &_ObjectContainer::label)
  ;
  register_ptr_to_python< std::auto_ptr<_ObjectContainer> >();



  typedef cecog::SingleObjectContainer<8> _SingleObjectContainer;

  class_< _SingleObjectContainer, bases<_ObjectContainerBase> >
    ("SingleObjectContainer", init< std::string, std::string >())
  ;
  register_ptr_to_python< std::auto_ptr<_SingleObjectContainer> >();



  typedef cecog::ImageMaskContainer<8> _ImageMaskContainer;

  class_< _ImageMaskContainer, bases<_ObjectContainerBase> >
    ("ImageMaskContainer", init< std::string, std::string >())
    .def(init<vigra::BImage, vigra::BImage, bool>())
    .def(init<vigra::BImage, vigra::Int16Image, bool, bool, bool>())
  ;
  register_ptr_to_python< std::auto_ptr<_ImageMaskContainer> >();

}
#endif // CECOG_PYTHON_WRAP_CONTAINERS_HXX_
