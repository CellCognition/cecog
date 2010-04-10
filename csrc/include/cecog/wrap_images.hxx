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


#ifndef CECOG_WRAP_IMAGES
#define CECOG_WRAP_IMAGES

#include <memory>

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/str.hpp>
#include <boost/python/overloads.hpp>
#include <boost/python/args.hpp>
#include <boost/shared_ptr.hpp>

#include "Python.h"

#include "numpy/arrayobject.h"

#include "vigra/stdimage.hxx"
#include "vigra/impex.hxx"
#include "vigra/diff2d.hxx"
#include "vigra/array_vector.hxx"
#include "vigra/flatmorphology.hxx"
#include "vigra/labelimage.hxx"
#include "vigra/inspectimage.hxx"
#include "vigra/resizeimage.hxx"
#include "vigra/stdconvolution.hxx"
#include "vigra/separableconvolution.hxx"
#include "vigra/resampling_convolution.hxx"
#include "vigra/rational.hxx"
#include "vigra/functorexpression.hxx"

#include "cecog/shared_objects.hxx"
#include "cecog/thresholds.hxx"
#include "cecog/readout.hxx"
#include "cecog/inspectors.hxx"
#include "cecog/transforms.hxx"

#include "cecog/seededregion.hxx"



using namespace boost::python;

BOOST_PYTHON_FUNCTION_OVERLOADS(pyOverloads_RGBImageToArray, pyRGBImageToArray, 1, 2)
BOOST_PYTHON_FUNCTION_OVERLOADS(pyOverloads_ImageToArray, pyImageToArray, 1, 2)



    template <class T>
    struct TypeAsNumPyType
    {
      static int result() { return NPY_DOUBLE; }
    };

    template <>
    struct TypeAsNumPyType<char>
    {
      static int result() { return NPY_UBYTE; }
    };

    template <>
    struct TypeAsNumPyType<signed char>
    {
      static int result() { return NPY_BYTE; }
    };

    template <>
    struct TypeAsNumPyType<unsigned char>
    {
      static int result() { return NPY_UBYTE; }
    };

    template <>
    struct TypeAsNumPyType<short>
    {
      static int result() { return NPY_SHORT; }
    };

    template <>
    struct TypeAsNumPyType<unsigned short>
    {
      static int result() { return NPY_USHORT; }
    };

    template <>
    struct TypeAsNumPyType<int>
    {
      static int result() { return NPY_INT; }
    };

    template <>
    struct TypeAsNumPyType<unsigned int>
    {
      static int result() { return NPY_UINT; }
    };

    template <>
    struct TypeAsNumPyType<float>
    {
      static int result() { return NPY_FLOAT; }
    };

    template <>
    struct TypeAsNumPyType<double>
    {
      static int result() { return NPY_DOUBLE; }
    };



template <class IMAGE>
object pyImageToArray(IMAGE const & img, bool copy=false)
{
  npy_intp n = img.width() * img.height();
  npy_intp dims[] = { img.height(), img.width() };
  if(copy)
  {
    object obj(handle<>(PyArray_SimpleNew(2, &dims[0],
           TypeAsNumPyType<typename IMAGE::PixelType>::result())));
    char *arr_data = ((PyArrayObject*) obj.ptr())->data;
    ((PyArrayObject*) obj.ptr())->strides[0] = img.width() * sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->strides[1] = sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->nd = 2;
    memcpy(arr_data, img[0], sizeof(typename IMAGE::PixelType) * n);
    return obj;
  }
  else
  {
    object obj(handle<>(PyArray_SimpleNewFromData(2, &dims[0],
            TypeAsNumPyType<typename IMAGE::PixelType>::result(), (char *)img[0])));
    ((PyArrayObject*) obj.ptr())->strides[0] = img.width() * sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->strides[1] = sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->nd = 2;
    return obj;
  }
}


template <class IMAGE>
numeric::array
pyRgbImageToArray(IMAGE & img, bool copy=true)
{
  npy_intp dims[] = { img.width(), img.height(), 3 };
  if (copy)
  {
    object obj(handle<>(PyArray_SimpleNew(3, &dims[0],
                                          TypeAsNumPyType<typename IMAGE::PixelType::value_type>::result())));
    char *arr_data = ((PyArrayObject*) obj.ptr())->data;
    ((PyArrayObject*) obj.ptr())->strides[2] = sizeof(typename IMAGE::PixelType::value_type);
    ((PyArrayObject*) obj.ptr())->strides[0] = sizeof(typename IMAGE::PixelType::value_type) * sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->strides[1] = sizeof(typename IMAGE::PixelType::value_type) * sizeof(typename IMAGE::PixelType) * img.width();
    ((PyArrayObject*) obj.ptr())->nd = 3;
    memcpy(arr_data, img[0], sizeof(typename IMAGE::PixelType::value_type) * sizeof(typename IMAGE::PixelType) * img.width() * img.height());
    return extract<numeric::array>(obj);
  }
  else
  {
    object obj(handle<>(PyArray_SimpleNewFromData(3, &dims[0],
                                                  TypeAsNumPyType<typename IMAGE::PixelType::value_type>::result(), (char *)img[0])));
    ((PyArrayObject*) obj.ptr())->strides[2] = sizeof(typename IMAGE::PixelType::value_type);
    ((PyArrayObject*) obj.ptr())->strides[0] = sizeof(typename IMAGE::PixelType::value_type) * sizeof(typename IMAGE::PixelType);
    ((PyArrayObject*) obj.ptr())->strides[1] = sizeof(typename IMAGE::PixelType::value_type) * sizeof(typename IMAGE::PixelType) * img.width();
    ((PyArrayObject*) obj.ptr())->nd = 3;
    return extract<numeric::array>(obj);
  }
}

template <class IMAGE1, class IMAGE2>
PyObject * pyDiscMedian(IMAGE1 const &imgIn, int radius)
{
  std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
  vigra::discMedian(srcImageRange(imgIn), destImage(*imgPtr), radius);
  return incref(object(imgPtr).ptr());
}

template <class IMAGE1, class IMAGE2>
PyObject * pyToggleMapping(IMAGE1 const &imgIn, int size)
{
  std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
  using namespace cecog::morpho;
  structuringElement2D se(WITHCENTER8, size);
  ImFastToggleMapping(srcImageRange(imgIn), destImage(*imgPtr), se);
  return incref(object(imgPtr).ptr());
}

template <class IMAGE1, class IMAGE2>
PyObject * pyGaussian(IMAGE1 const &imgIn, int size)
{
  std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
  vigra::gaussianSmoothing(srcImageRange(imgIn), destImage(*imgPtr), (double)size);
  return incref(object(imgPtr).ptr());
}

template <class IMAGE1, class IMAGE2>
PyObject * pyThreshold(IMAGE1 const &imgIn,
                       typename IMAGE1::PixelType lower,
                       typename IMAGE1::PixelType higher,
                       typename IMAGE2::PixelType noresult,
                       typename IMAGE2::PixelType yesresult)
{
  std::auto_ptr< IMAGE2 > imgPtr(new IMAGE2(imgIn.size()));
  vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                        vigra::Threshold<typename IMAGE1::PixelType,
                                         typename IMAGE2::PixelType>
                        (lower, higher, noresult, yesresult));
  return incref(object(imgPtr).ptr());
}

template <class IMAGE>
PyObject * pySubImage(IMAGE const & imgIn, vigra::Diff2D ul, vigra::Diff2D size)
{
  std::auto_ptr< IMAGE > imgPtr(new IMAGE(size));
  vigra::copyImage(imgIn.upperLeft()+ul,
                   imgIn.upperLeft()+ul+size,
                   imgIn.accessor(),
                   imgPtr->upperLeft(),
                   imgPtr->accessor());
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3>
PyObject * pyAddImages(Image1 const & imgIn1, Image2 const & imgIn2)
{
  using namespace vigra::functor;
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn1.size()));
  vigra::combineTwoImages(srcImageRange(imgIn1),
                          srcImage(imgIn2),
                          destImage(*imgPtr),
                          Arg1()+Arg2());
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3>
PyObject * pySubstractImages(Image1 const & imgIn1, Image2 const & imgIn2)
{
  using namespace vigra::functor;
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn1.size()));
  vigra::combineTwoImages(srcImageRange(imgIn1),
                          srcImage(imgIn2),
                          destImage(*imgPtr),
                          Arg1()-Arg2());
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3>
PyObject * pySubstractImages2(Image1 const & imgIn1, Image2 const & imgIn2, typename Image3::value_type minV, typename Image3::value_type maxV)
{
  using namespace vigra::functor;
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn1.size()));
  vigra::combineTwoImages(srcImageRange(imgIn1),
                          srcImage(imgIn2),
                          destImage(*imgPtr),
                          cecog::ImageSubstract2<typename Image1::value_type, typename Image2::value_type, typename Image3::value_type>(minV, maxV));
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2>
PyObject * pyFlatfieldCorrection(Image1 const & imgIn, Image2 const & imgBack, float offset, bool normalizeBackground)
{
  using namespace vigra::functor;
  typedef vigra::FImage Image3;

  float normV = 1.0;
  if (normalizeBackground)
  {
    vigra::FindMinMax<typename Image2::value_type> minmax;
    inspectImage(srcImageRange(imgBack), minmax);
    normV = (float)minmax.max;
  }

  Image3 imgBack2(imgIn.size());
  vigra::copyImage(srcImageRange(imgBack), destImage(imgBack2));

  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
  vigra::combineTwoImages(srcImageRange(imgIn),
                          srcImage(imgBack2),
                          destImage(*imgPtr),
                          Arg1() / Arg2() * Param(normV) + Param(offset));
  return incref(object(imgPtr).ptr());
}


template <class Image1, class Image2>
PyObject * pyLinearTransform(Image1 const &imgIn, double ratio, typename Image1::value_type offset)
{
   std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
   vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                         vigra::linearIntensityTransform(ratio, offset));
   return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2>
PyObject * pyLinearTransform2(Image1 const &imgIn, typename Image1::value_type srcMin, typename Image1::value_type srcMax, typename Image2::value_type destMin, typename Image2::value_type destMax, typename Image2::value_type minV, typename Image2::value_type maxV)
{
   std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
   vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                         cecog::ImageLinearTransform<typename Image1::value_type, typename Image2::value_type>(srcMin, srcMax, destMin, destMax, minV, maxV));
   return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2>
PyObject * pyLinearRangeMapping(Image1 const &imgIn, typename Image1::value_type srcMin, typename Image1::value_type srcMax, typename Image2::value_type destMin, typename Image2::value_type destMax)
{
   std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
   vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                         vigra::linearRangeMapping(srcMin, srcMax, destMin, destMax));
   return incref(object(imgPtr).ptr());
}

template <class Image1>
PyObject * pyHistogramEqualization(Image1 const &imgIn, typename Image1::value_type minV, typename Image1::value_type maxV)
{
   std::auto_ptr< Image1 > imgPtr(new Image1(imgIn.size()));
   cecog::FindHistogram<typename Image1::value_type> histogram(maxV+1);
   vigra::inspectImage(srcImageRange(imgIn), histogram);
   vigra::transformImage(srcImageRange(imgIn), destImage(*imgPtr),
                         cecog::HistogramEqualization<typename Image1::value_type>(histogram.probabilities(), minV, maxV));
   return incref(object(imgPtr).ptr());
}


template <class IMAGE>
double pyImageMean(IMAGE const & img)
{
  vigra::FindAverage<typename IMAGE::PixelType> functor;
  vigra::inspectImage(srcImageRange(img), functor);
  return double(functor());
}

template <class IMAGE>
PyObject * pyImageMinmax(IMAGE const & imin)
{
   vigra::FindMinMax<typename IMAGE::value_type> minmax;
   inspectImage(srcImageRange(imin), minmax);
   return incref(make_tuple(minmax.min, minmax.max).ptr());
}

template <class IMAGE1>
list pyImageHistogram(IMAGE1 const &imin, unsigned int valueCount)
{
   cecog::FindHistogram<typename IMAGE1::value_type> hist(valueCount);
   inspectImage(srcImageRange(imin), hist);
   std::vector<double> p(hist.probabilities());
   list h;
   for (int i=0; i<p.size(); i++)
     h.append(p[i]);
   return h;
}

template <class Image1, class Image2>
PyObject * pyScaleImage1(Image1 const &imgIn, vigra::Diff2D const &size, std::string method="linear")
{
  std::auto_ptr< Image2 > imgPtr(new Image2(size));
  if (method == "no")
    resizeImageNoInterpolation(srcImageRange(imgIn), destImageRange(*imgPtr));
  else if (method == "linear")
    resizeImageLinearInterpolation(srcImageRange(imgIn), destImageRange(*imgPtr));
  else if (method == "spline")
    resizeImageSplineInterpolation(srcImageRange(imgIn), destImageRange(*imgPtr));
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2>
PyObject * pyScaleImage2(Image1 const &imgIn, double scale, std::string method="linear")
{
  vigra::Diff2D size((int)(imgIn.width() * scale), (int)(imgIn.height() * scale));
  return pyScaleImage1<Image1, Image2>(imgIn, size, method);
}


template <class IMAGE_IN, class IMAGE_OUT, class T>
void pyConvolveImage1(IMAGE_IN const &imgIn,
                      IMAGE_OUT &imgOut,
                      vigra::Kernel2D<T> const &oKernel2D)
{
  convolveImage(srcImageRange(imgIn), destImage(imgOut), kernel2d(oKernel2D));
}


template <class IMAGE_IN, class IMAGE_OUT, class TX, class TY>
void pyConvolveImage2(IMAGE_IN const &imgIn,
                      IMAGE_OUT &imgOut,
                      vigra::Kernel1D<TX> const &oKernelX,
                      vigra::Kernel1D<TY> const &oKernelY)
{
  convolveImage(srcImageRange(imgIn), destImage(imgOut), oKernelX, oKernelY);
}


template <class IMAGE_IN, class IMAGE_OUT>
PyObject * pyBinImage(IMAGE_IN const &imgIn,
                      int iFactor)
{
  std::auto_ptr< IMAGE_OUT > imgPtr(new IMAGE_OUT(imgIn.size()));
  vigra::Kernel2D<float> oKernel;
  oKernel.initExplicitly(vigra::Diff2D(0,0), vigra::Diff2D(iFactor-1,iFactor-1)) = 1.0 / float(iFactor*iFactor);
  convolveImage(srcImageRange(imgIn), destImage(*imgPtr), kernel2d(oKernel));
  return incref(object(imgPtr).ptr());
}

//template <class IMAGE_IN, class IMAGE_OUT>
//void pyBinResampleImage(IMAGE_IN const &imgIn,
//                        IMAGE_OUT &imgOut,
//                        int iFactor)
//{
//  vigra::Kernel1D<float> oKernel;
//  oKernel.initExplicitly(0, iFactor-1) = 1.0 / iFactor;
//  vigra::Rational<float> oRational(1.0 / iFactor);
//  vigra::Rational<int> oOffset(0);
//  resamplingConvolveImage(srcImageRange(imgIn), destImage(imgOut),
//                          oKernel, oRational, oOffset,
//                          oKernel, oRational, oOffset);
//}


template <class IMAGE1, class IMAGE2>
void pyLocalThreshold(IMAGE1 const & imin, IMAGE2 & imout, unsigned int region_size, typename IMAGE1::value_type limit)
{
  cecog::ImLocalThreshold(imin, imout, vigra::Diff2D(region_size, region_size), limit);
}

template <class IMAGE1, class IMAGE2>
void pyBackgroundSubtraction(IMAGE1 const & imin, IMAGE2 & imout, unsigned int region_size)
{
  cecog::ImBackgroundSubtraction(imin, imout, vigra::Diff2D(region_size, region_size));
}


template <class IMAGE1, class IMAGE2>
unsigned int pyLabelImage(IMAGE1 const & img1,
                          IMAGE2 & img2,
                          bool eightNbh, typename IMAGE1::PixelType background)
{
  return vigra::labelImageWithBackground(srcImageRange(img1),
                                         destImage(img2),
                                         eightNbh,
                                         background);
}

template <class PixelType>
inline static PyObject * pyReadImage(std::string strFilename, int imageIndex=-1)
//inline static PyObject * pyReadImage(std::string strFilename)
{
  typedef vigra::BasicImage< PixelType > ImageType;
  vigra::ImageImportInfo oInfo(strFilename.c_str());
  if (imageIndex > -1)
    oInfo.setImageIndex(imageIndex);
  std::auto_ptr< ImageType > imgPtr(new ImageType(oInfo.size()));
  vigra::importImage(oInfo, vigra::destImage(*imgPtr));
  return incref(object(imgPtr).ptr());
}


vigra::BImage pyReadImageMito(char const * fileName)
{
  vigra::ImageImportInfo oInfo(fileName);
  vigra::BasicImage<signed short> imgTemp(oInfo.size());
  vigra::importImage(oInfo, vigra::destImage(imgTemp));

  vigra::BImage imgOut(oInfo.size());

  double ratio = 255.0 / 4096.0 ;
  unsigned int offset = 32768;
  vigra::transformImage(srcImageRange(imgTemp), destImage(imgOut),
                        vigra::linearIntensityTransform(ratio, offset));
  return imgOut;
}


template <class IMAGE>
void pyWriteImage(IMAGE const &imgIn,
                  std::string strFilename, std::string strCompression="100")
{
  vigra::exportImage(vigra::srcImageRange(imgIn),
                     vigra::ImageExportInfo(strFilename.c_str()).setCompression(strCompression.c_str()));
}




template <class IMAGE1, class IMAGE2>
void pyGlobalThreshold(IMAGE1 const &imin, IMAGE2 & imout, typename IMAGE1::value_type thresh)
{
    vigra::transformImage(srcImageRange(imin), destImage(imout),
                          vigra::Threshold<typename IMAGE1::value_type, typename IMAGE2::value_type>(thresh, 255, 0, 255));
}


template <class IMAGE>
typename IMAGE::PixelType pyGetPixel(IMAGE const &image, typename IMAGE::difference_type const &pos)
{
  vigra_precondition(pos.x >= 0 && pos.x < image.width() && pos.y >= 0 && pos.y < image.height(),
                     "coordinates out of range for getPixel()");
  return image[pos];
}

template <class IMAGE>
void pySetPixel(IMAGE &image, typename IMAGE::difference_type const &pos, typename IMAGE::PixelType value)
{
  vigra_precondition(pos.x >= 0 && pos.x < image.width() && pos.y >= 0 && pos.y < image.height(),
                     "coordinates out of range for setPixel()");
  image[pos] = value;
}

template <class VALUE_TYPE>
VALUE_TYPE RGBValue__getitem__(vigra::RGBValue<VALUE_TYPE> const & rgbvalue, int idx)
{
  if (idx >= 0 && idx < 3)
    return rgbvalue[idx];
  else
  {
    PyErr_SetString(PyExc_IndexError, "RGBValue.__getitem__(): component index out of bounds.");
    throw_error_already_set();
    return 0; // unreachable
  }
}

template <class VALUE_TYPE>
void RGBValue__setitem__(vigra::RGBValue<VALUE_TYPE> & rgbvalue, int idx, VALUE_TYPE value)
{
  if (idx >= 0 && idx < 3)
    rgbvalue[idx] = value;
  else
  {
    PyErr_SetString(PyExc_IndexError, "RGBValue.__setitem__(): component index out of bounds.");
    throw_error_already_set();
  }
}

template <class VALUE_TYPE>
std::string RGBValue__str__(vigra::RGBValue<VALUE_TYPE> const & rgbvalue)
{
  char s[100];
  if (boost::is_same<VALUE_TYPE, uint8>() || boost::is_same<VALUE_TYPE, unsigned char>())
  {
    long int hex = (rgbvalue.red() << 16) + (rgbvalue.green() << 8) + rgbvalue.blue();
    sprintf(s, "RGBValue(<%d,%d,%d> = #%06X)", rgbvalue.red(), rgbvalue.green(), rgbvalue.blue(), hex);
  }
  else
    sprintf(s, "RGBValue(%d,%d,%d)", rgbvalue.red(), rgbvalue.green(), rgbvalue.blue());
  return std::string(s);
}

template <class IMAGE>
std::auto_ptr< vigra::BasicImageView<typename IMAGE::PixelType> >
pyImageGetView1(IMAGE &imgIn)
{
  return std::auto_ptr< vigra::BasicImageView<typename IMAGE::PixelType> >
           (new vigra::BasicImageView<typename IMAGE::PixelType>(imgIn.data(), imgIn.size()));
}

template <class IMAGE>
std::auto_ptr< vigra::BasicImageView<typename IMAGE::PixelType> >
pyImageGetView2(IMAGE &imgIn,
            typename IMAGE::difference_type const &upperLeft,
            typename IMAGE::difference_type const &size)
{
  return std::auto_ptr< vigra::BasicImageView<typename IMAGE::PixelType> >
           (new vigra::BasicImageView<typename IMAGE::PixelType>(imgIn[upperLeft.y]+upperLeft.x,
                                                                 size, imgIn.width()));
}

template <class IMAGE>
std::auto_ptr< vigra::BasicImageView<typename IMAGE::PixelType> >
pyImageGetView3(IMAGE &imgIn, int x1, int y1, int x2, int y2)
{
  return pyImageGetView2(imgIn,
              vigra::Diff2D(x1,y1),
              vigra::Diff2D(x2-x1, y2-y1));
}


template<class T>
struct PySequenceToArrayVector
{
  typedef vigra::ArrayVector<T> Type;

  PySequenceToArrayVector()
  {
    converter::registry::push_back(&convertibleFromSequence, &constructFromSequence, type_id<Type>());
  }

  static void* convertibleFromSequence(PyObject* obj)
  {
    if (!PySequence_Check(obj)) return false;
    object oSequence = extract<object>(obj)();
    int iNumberElements = (int)PySequence_Size(obj);
    for(int iIndex=0;iIndex<iNumberElements;iIndex++)
      if(!extract<T>(oSequence.attr("__getitem__")(iIndex)).check())
        return false;
    return obj;
  }

  static void constructFromSequence(PyObject *obj, converter::rvalue_from_python_stage1_data* data)
  {
    object oSequence = extract<object>(obj)();
    int iNumberElements = (int)PySequence_Size(obj);
    void* const oStorage = ((converter::rvalue_from_python_storage<Type>*)data)->storage.bytes;
    new (oStorage) Type(iNumberElements);
    data->convertible = oStorage;
    Type& oResult = *((Type*)oStorage);
    for (int iIndex=0;iIndex<iNumberElements;iIndex++)
      oResult[iIndex] = extract<T>(oSequence.attr("__getitem__")(iIndex))();
  }

};



template <class KEY, class VALUE>
inline
void convert_dict_to_map(dict const &d, std::map<KEY, VALUE> &m)
{
    list lstKeys = d.keys();
    list lstValues = d.values();
    KEY iSize = extract<KEY>(lstKeys.attr("__len__")());
    KEY k;
    VALUE v;
    for (int i = 0; i < iSize; i++)
    {
      k = extract<KEY>(lstKeys[i])();
      v = extract<VALUE>(lstValues[i])();
      m[k] = v;
    }
}

//template <class IMAGE>
//PyObject* pyProjectImage(PyObject * lstImages, cecog::ProjectionType pType)
//{
//  typedef vigra::ArrayVector< IMAGE > ImageVector;
//  ImageVector oImageVector = extract<ImageVector>(lstImages)();
//  if (oImageVector.size() > 0)
//  {
//    std::auto_ptr< IMAGE >
//      imgPtr(new IMAGE(oImageVector[0].size()));
//    cecog::projectImage(oImageVector, *imgPtr, pType);
//    return incref(object(imgPtr).ptr());
//  }
//  else
//    return Py_None;
//}

template <class IMAGE>
PyObject* pyProjectImage(vigra::ArrayVector< IMAGE > oImageVector, cecog::ProjectionType pType)
{
  if (oImageVector.size() > 0)
  {
    std::auto_ptr< IMAGE >
      imgPtr(new IMAGE(oImageVector[0].size()));
    cecog::projectImage(oImageVector, *imgPtr, pType);
    return incref(object(imgPtr).ptr());
  }
  else
    return Py_None;
}

template <class T>
  vigra::BasicImage< vigra::RGBValue<T> > pyMakeRGBImage1(PyObject * lstImages, PyObject * lstRGBValues)
  {
    //typedef vigra::BasicImageView<T> ImageType;
    //int iSize = extract< ImageType >(lstImages.attr("__len__")());

    typedef vigra::ArrayVector< vigra::BasicImageView<T> > ImageVector;
    ImageVector oImageVector = extract<ImageVector>(lstImages)();

    vigra_precondition(oImageVector.size() > 0,
                       "pyMakeRGBImage: List of images must contain at least one item!");

    //vigra::BasicImageView<T> iview2D = makeBasicImageView(view2D);
    //vigra::exportImage(vigra::srcImageRange(iview2D), vigra::ImageExportInfo("moo2d.png"));

    typedef vigra::ArrayVector< vigra::RGBValue<T> > RGBValueVector;
    RGBValueVector oRGBValueVector = extract<RGBValueVector>(lstRGBValues)();

    return cecog::makeRGBImage(oImageVector, oRGBValueVector);
  }

template <class T>
  vigra::BasicImage< vigra::RGBValue<T> > pyMakeRGBImage2(PyObject * lstImages, PyObject * lstRGBValues,
                                                          PyObject * lstAlphas)
  {
    //typedef vigra::BasicImageView<T> ImageType;
    //int iSize = extract< ImageType >(lstImages.attr("__len__")());

    typedef vigra::ArrayVector< vigra::BasicImageView<T> > ImageVector;
    ImageVector oImageVector = extract<ImageVector>(lstImages)();

    vigra_precondition(oImageVector.size() > 0,
                       "pyMakeRGBImage: List of images must contain at least one item!");

    //vigra::BasicImageView<T> iview2D = makeBasicImageView(view2D);
    //vigra::exportImage(vigra::srcImageRange(iview2D), vigra::ImageExportInfo("moo2d.png"));

    typedef vigra::ArrayVector< vigra::RGBValue<T> > RGBValueVector;
    RGBValueVector oRGBValueVector = extract<RGBValueVector>(lstRGBValues)();

    typedef vigra::ArrayVector< float > AlphaVector;
    AlphaVector oAlphas = extract<AlphaVector>(lstAlphas)();

    return cecog::makeRGBImage(oImageVector, oRGBValueVector, oAlphas);
  }

//vigra::BasicImage<vigra::RGBValue<uint8> > pyMakeRGBImage1(vigra::ArrayVector< vigra::BasicImageView<uint8> > const & oImageVector,
//                                                           vigra::ArrayVector< vigra::RGBValue<uint8> > const & oChannelVector)
//{
//  cecog::makeRGBImage(oImageVector, oChannelVector);
//}
//
//vigra::BasicImage<vigra::RGBValue<uint8> > pyMakeRGBImage2(vigra::ArrayVector< vigra::BasicImageView<uint8> > const & oImageVector,
//                                                           vigra::ArrayVector< vigra::RGBValue<uint8> > const & oChannelVector,
//                                                           vigra::ArrayVector< float > const & oAlphaVector)
//{
//  cecog::makeRGBImage(oImageVector, oChannelVector, oAlphaVector);
//}


void pyMaxIntensityRGB(vigra::BRGBImage const &imgIn, vigra::BRGBImage &imgOut, float fAlpha)
{
  vigra::BRGBImage::ConstScanOrderIterator itRGBIn = imgIn.begin();
  vigra::BRGBImage::ScanOrderIterator itRGBOut = imgOut.begin();
  for (; itRGBIn != imgIn.end() && itRGBOut != imgOut.end(); itRGBIn++, itRGBOut++)
  // loop over r,g,b: do the RGB-blending
    for (int m=0; m < 3; m++)
    {
      // scale the current pixel by means of its channel component
      // FIXME: scaling is limited to uint8, so template generalization is broken here
      unsigned char iValue = fAlpha * (*itRGBIn)[m];
      // do a max-blending with any value already assigned to this pixel
      (*itRGBOut)[m] = std::max((*itRGBOut)[m], iValue);
    }
}

void pyMaxIntensity(vigra::BImage const &imgIn, vigra::BImage &imgOut, float fAlpha)
{
  vigra::BImage::ConstScanOrderIterator itIn = imgIn.begin();
  vigra::BImage::ScanOrderIterator itOut = imgOut.begin();
  for (; itIn != imgIn.end() && itOut != imgOut.end(); itIn++, itOut++)
  {
    unsigned char iValue = fAlpha * *itIn;
    // do a max-blending with any value already assigned to this pixel
    *itOut = std::max(*itOut, iValue);
  }
}

template <class ImageOrView1, class ImageOrView2>
dict pyFindStddev(ImageOrView1 const &viewIn,
                  ImageOrView2 const &viewLabels,
                  int iLabelCount)
{
  vigra::ArrayOfRegionStatistics< cecog::FindStdDev< typename ImageOrView1::PixelType > > oFunctor(iLabelCount);
  inspectTwoImages(srcImageRange(viewIn), srcImage(viewLabels), oFunctor);

  dict dctResults;
  for (int i=0; i < iLabelCount; i++)
    dctResults[i] = make_tuple(oFunctor[i].average(), oFunctor[i].stddev());

  return dctResults;

}

template <class ImageOrView1, class ImageOrView2>
dict pyFindMinmax(ImageOrView1 const &viewIn,
                  ImageOrView2 const &viewLabels,
                  int iLabelCount)
{
  vigra::ArrayOfRegionStatistics< vigra::FindMinMax< typename ImageOrView1::PixelType > > oFunctor(iLabelCount);
  inspectTwoImages(srcImageRange(viewIn), srcImage(viewLabels), oFunctor);

  dict dctResults;
  for (int i=0; i < iLabelCount; i++)
    dctResults[i] = make_tuple(oFunctor[i].min, oFunctor[i].max);

  return dctResults;

}

template <class ImageOrView1, class ImageOrView2>
dict pyFindAverage(ImageOrView1 const &viewIn,
                   ImageOrView2 const &viewLabels,
                   int iLabelCount)
{
  vigra::ArrayOfRegionStatistics< vigra::FindAverage< typename ImageOrView1::PixelType > > oFunctor(iLabelCount);
  inspectTwoImages(srcImageRange(viewIn), srcImage(viewLabels), oFunctor);

  dict dctResults;
  for (int i=0; i < iLabelCount; i++)
    dctResults[i] = oFunctor[i]();

  return dctResults;

}

template <class ImageOrView1, class ImageOrView2>
void pyDrawContour(ImageOrView1 const &imgIn, ImageOrView2 &imgOut, typename ImageOrView2::PixelType value, bool quad=false)
{
  cecog::drawContour(srcImageRange(imgIn), destImage(imgOut), value, quad);
}

template <class Image1, class Image2>
PyObject * pyWindowAverageThreshold(Image1 const &imgIn,
                                    unsigned size,
                                    typename Image1::value_type contrastLimit=vigra::NumericTraits<typename Image1::value_type>::zero(),
                                    typename Image1::value_type lower=vigra::NumericTraits<typename Image1::value_type>::min(),
                                    typename Image1::value_type higher=vigra::NumericTraits<typename Image1::value_type>::max())
{
  std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
  cecog::windowAverageThreshold(imgIn, *imgPtr, size, contrastLimit, lower, higher);
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2>
PyObject * pyWindowStdThreshold(Image1 const &imgIn,
                                unsigned size,
                                float threshold,
                                typename Image1::value_type contrastLimit=vigra::NumericTraits<typename Image1::value_type>::zero())
{
  std::auto_ptr< Image2 > imgPtr(new Image2(imgIn.size()));
  cecog::windowStdThreshold(imgIn, *imgPtr, size, threshold, contrastLimit);
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3, class RegionStatisticsArray>
PyObject * pySeededRegionExpansion(Image1 const &imgIn,
                                   Image2 const &imgSeeds,
                                   const cecog::SRGType srgType,
                                   unsigned labelNumber,
                                   typename RegionStatisticsArray::value_type::cost_type costThreshold,
                                   int expansionRounds,
                                   int sepExpandRounds=0)
{
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
  RegionStatisticsArray stats(labelNumber);
  cecog::seededRegionExpansion(srcImageRange(imgIn),
                              maskImage(imgSeeds),
                              destImage(*imgPtr),
                              srgType,
                              stats,
                              costThreshold,
                              expansionRounds,
                              sepExpandRounds);
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3, class RegionStatisticsArray>
PyObject * pySeededRegionShrinking(Image1 const &imgIn,
                                   Image2 const &imgSeeds,
                                   unsigned labelNumber,
                                   int shrinkingRounds)
{
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
  RegionStatisticsArray stats(labelNumber);
  cecog::seededRegionShrinking(srcImageRange(imgIn),
                              maskImage(imgSeeds),
                              destImage(*imgPtr),
                              stats,
                              shrinkingRounds);
  return incref(object(imgPtr).ptr());
}


template <class Image1, class Image2>
void pyCopyImage(Image1 const &imgIn, Image2 &imgOut)
{
  vigra::copyImage(srcImageRange(imgIn), destImage(imgOut));
}

template <class Image1, class Image2>
void pyCopyImageGray(Image1 const &imgIn, Image2 &imgOut)
{
  vigra::copyImage(imgIn.upperLeft(), imgIn.lowerRight(), vigra::RGBToGrayAccessor<typename Image1::PixelType>(),
                   imgOut.upperLeft(), imgOut.accessor());
}

template <class Image1>
void pyDrawLine(vigra::Diff2D const &p1, vigra::Diff2D const &p2,
                Image1 &imgIn, typename Image1::value_type const &color,
                bool thick)
{
  cecog::drawLine(p1, p2, imgIn.upperLeft(), imgIn.accessor(), color, thick);
}

template <class Image1>
void pyDrawFilledCircle(vigra::Diff2D const &p, int radius,
                        Image1 &imgIn, typename Image1::value_type const &color)
{
  cecog::drawFilledCircle(p, radius,
                         imgIn.upperLeft(), imgIn.lowerRight(), imgIn.accessor(),
                         color);
}

template <class Image1, class Image2>
void pyCopySubImage1(Image1 const &imgIn, vigra::Diff2D const &ulIn, vigra::Diff2D const &lrIn,
                    Image2 &imgOut, vigra::Diff2D const &ulOut)
{
  vigra::copyImage(imgIn.upperLeft() + ulIn,
                   imgIn.upperLeft() + lrIn,
                   imgIn.accessor(),
                   imgOut.upperLeft() + ulOut,
                   imgOut.accessor());
}

template <class Image1, class Image2>
void pyCopySubImage2(Image1 const &imgIn, Image2 &imgOut, vigra::Diff2D const &ulOut)
{
  pyCopySubImage1(imgIn, vigra::Diff2D(0,0), imgIn.size(),
                  imgOut, ulOut);
}

template <class Image1, class Image2, class Image3>
PyObject* pyCopyImageIf(Image1 const &imgIn, Image2 const &imgMask)
{
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
  vigra::copyImageIf(srcImageRange(imgIn), maskImage(imgMask), destImage(*imgPtr));
  return incref(object(imgPtr).ptr());
}

template <class Image1, class Image2, class Image3>
PyObject* pyCopyImageIfLabel(Image1 const &imgIn, Image2 const &imgMask, typename Image2::value_type label)
{
  std::auto_ptr< Image3 > imgPtr(new Image3(imgIn.size()));
  cecog::copyImageIfLabel(srcImageRange(imgIn), maskImage(imgMask), destImage(*imgPtr), label);
  return incref(object(imgPtr).ptr());
}

//template <class VALUE_TYPE>
//static void wrapKernel1D(const char * name)
//{
//  typedef vigra::Kernel1D<VALUE_TYPE> Kernel;
//  class_< Kernel > oKernelWrapper(name);
//  baseKernelWrapper(oKernelWrapper);
//}
//
//template <class VALUE_TYPE>
//static void wrapKernel2D(const char * name)
//{
//  typedef vigra::Kernel2D<VALUE_TYPE> Kernel;
//  class_< Kernel >(name)
//    .def("initExplicitly", ((Kernel&)(vigra::Diff2D, vigra::Diff2D))&Kernel::initExplicitly)
//    ;
//  register_ptr_to_python< std::auto_ptr< Kernel > >();
//}


template <class IMAGE>
static void baseImageWrapper(class_< IMAGE > &oImageWrapper)
{
  oImageWrapper
    .add_property("width", &IMAGE::width)
    .add_property("height", &IMAGE::height)
    .add_property("size", &IMAGE::size)
    .def("init", (void (IMAGE::*)(const typename IMAGE::PixelType&) )&IMAGE::init)
    .def("__getitem__", &pyGetPixel< IMAGE >)
    .def("__setitem__", &pySetPixel< IMAGE >);
  register_ptr_to_python< std::auto_ptr< IMAGE > >();
}

template <class VALUE_TYPE>
static void wrapImage(const char * name)
{
  typedef vigra::BasicImage<VALUE_TYPE> ImageType;
  class_< ImageType > oImageWrapper(name);
  oImageWrapper
    .def(init< int, int >())
    .def(init< const vigra::Diff2D& >())
    .def("getView", &pyImageGetView1< ImageType >)
    .def("getView", &pyImageGetView2< ImageType >)
    .def("getView", &pyImageGetView3< ImageType >)
    .def("getMean", &pyImageMean< ImageType >)
    .def("getMinmax", &pyImageMinmax< ImageType >)
    .def("getHistogram", &pyImageHistogram< ImageType >)
    .def("toArray", &pyImageToArray< ImageType >, (arg("img"), arg("copy")=false), "Export image to numpy.array");
  baseImageWrapper(oImageWrapper);
}

template <class VALUE_TYPE>
static void wrapImageView(const char * name)
{
  typedef vigra::BasicImageView<VALUE_TYPE> ImageType;
  class_< ImageType > oImageWrapper(name);
  oImageWrapper
    .def("getView", &pyImageGetView1< ImageType >)
    .def("getView", &pyImageGetView2< ImageType >)
    .def("getView", &pyImageGetView3< ImageType >)
    .def("getMean", &pyImageMean< ImageType >)
    .def("getMinmax", &pyImageMinmax< ImageType >)
    .def("getHistogram", &pyImageHistogram< ImageType >)
    .def("toArray", &pyImageToArray< ImageType >, (arg("img"), arg("copy")=false), "Export image to numpy.array");
  baseImageWrapper(oImageWrapper);
}


template <class VALUE_TYPE>
static void wrapRGBImage(const char * name)
{
  typedef vigra::BasicImage< vigra::RGBValue<VALUE_TYPE> > ImageType;
  class_< ImageType > oImageWrapper(name);
  oImageWrapper
    .def(init< int, int >())
    .def(init< const vigra::Diff2D& >())
    .def("getView", &pyImageGetView1< ImageType >)
    .def("getView", &pyImageGetView2< ImageType >)
    .def("getView", &pyImageGetView3< ImageType >)
    .def("toArray", &pyRgbImageToArray< ImageType >, (arg("img"), arg("copy")=false), "Export image to numpy.array");
  baseImageWrapper(oImageWrapper);
}

template <class VALUE_TYPE>
static void wrapRGBImageView(const char * name)
{
  typedef vigra::BasicImageView< vigra::RGBValue< VALUE_TYPE > > ImageType;
  class_< ImageType > oImageWrapper(name);
  baseImageWrapper(oImageWrapper);
}


template <class VALUE_TYPE>
static void wrapRGBValue(const char * name)
{
  typedef vigra::RGBValue<VALUE_TYPE> RGBValue;
  class_< RGBValue >(name, init<VALUE_TYPE,VALUE_TYPE,VALUE_TYPE>())
    .def("__getitem__", &RGBValue__getitem__< VALUE_TYPE >)
    .def("__setitem__", &RGBValue__setitem__< VALUE_TYPE >)
    .def("__str__", &RGBValue__str__< VALUE_TYPE >)
    ;
  register_ptr_to_python< std::auto_ptr< RGBValue > >();
}

static void wrapFont(const char * name)
{
  class_< cecog::Font >(name, init< std::string >())
    .def("write", &cecog::Font::write< vigra::UInt8 >)
    .def("write", &cecog::Font::write< vigra::RGBValue< vigra::UInt8 > >)
    ;
  register_ptr_to_python< std::auto_ptr< cecog::Font > >();
}


static void wrap_images()
{
  import_array();
  numeric::array::set_module_and_type("numpy", "ndarray");


  class_< vigra::ImageImportInfo, boost::noncopyable >("ImageImportInfo", init<const char *>())
    .def(init<const char *, unsigned int>())
    .add_property("file_name", &vigra::ImageImportInfo::getFileName)
    .add_property("file_type", &vigra::ImageImportInfo::getFileType)
    .add_property("width", &vigra::ImageImportInfo::width)
    .add_property("height", &vigra::ImageImportInfo::height)
    .add_property("bands", &vigra::ImageImportInfo::numBands)
    .add_property("index", &vigra::ImageImportInfo::getImageIndex, &vigra::ImageImportInfo::setImageIndex)
    .add_property("images", &vigra::ImageImportInfo::numImages)
    .add_property("size", &vigra::ImageImportInfo::size)
    .add_property("is_grayscale", &vigra::ImageImportInfo::isGrayscale)
    .add_property("is_color", &vigra::ImageImportInfo::isColor)
    .add_property("is_byte", &vigra::ImageImportInfo::isByte)
    .add_property("pixel_type", &vigra::ImageImportInfo::getPixelType)
    .add_property("x_resolution", &vigra::ImageImportInfo::getXResolution)
    .add_property("y_resolution", &vigra::ImageImportInfo::getYResolution)
    ;
  register_ptr_to_python< std::auto_ptr<vigra::ImageImportInfo> >();

  enum_<vigra::ImageImportInfo::PixelType>("PIXEL_TYPECODES")
    .value("UINT8", vigra::ImageImportInfo::UINT8)
    .value("UINT16", vigra::ImageImportInfo::UINT16)
    .value("UINT32", vigra::ImageImportInfo::UINT32)
    .value("INT16", vigra::ImageImportInfo::INT16)
    .value("INT32", vigra::ImageImportInfo::INT32)
    .value("FLOAT", vigra::ImageImportInfo::FLOAT)
    .value("DOUBLE", vigra::ImageImportInfo::DOUBLE)
    .export_values()
    ;



  def("readImageMito", pyReadImageMito);

  def("readImage", pyReadImage< vigra::UInt8 >,
      ("strFilename", arg("imageIndex")=-1), "Read UInt8 image from file.");
  def("readImageUInt16", pyReadImage< vigra::UInt16 >,
      ("strFilename", arg("imageIndex")=-1), "Read UInt16 image from file.");
  def("readImageInt16", pyReadImage< vigra::Int16 >,
      ("strFilename", arg("imageIndex")=-1), "Read Int16 image from file.");
  def("readImageUInt32", pyReadImage< vigra::UInt32 >,
      ("strFilename", arg("imageIndex")=-1), "Read UInt32 image from file.");
  def("readImageInt32", pyReadImage< vigra::Int32 >,
      ("strFilename", arg("imageIndex")=-1), "Read Int32 image from file.");
  def("readImageFloat", pyReadImage< float >,
      ("strFilename", arg("imageIndex")=-1), "Read float image from file.");
  def("readImageRGB", pyReadImage< vigra::RGBValue< vigra::UInt8 > >,
      ("strFilename", arg("imageIndex")=-1), "Read RGB image (3xUInt8) from file.");

//  def("readImage", pyReadImage< vigra::UInt8 >,
//      ("strFilename"), "Read UInt8 image from file.");
//  def("readImageUInt16", pyReadImage< vigra::UInt16 >,
//      ("strFilename"), "Read UInt16 image from file.");
//  def("readImageInt16", pyReadImage< vigra::Int16 >,
//      ("strFilename"), "Read Int16 image from file.");
//  def("readRGBImage", pyReadImage< vigra::RGBValue< vigra::UInt8 > >,
//      ("strFilename"), "Read RGB image (3xUInt8) from file.");

  def("writeImage", pyWriteImage< vigra::UInt8Image >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write UInt8 image to file.");
  def("writeImage", pyWriteImage< vigra::UInt16Image >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write UInt16 image to file.");
  def("writeImage", pyWriteImage< vigra::Int16Image >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write Int16 image to file.");
  def("writeImage", pyWriteImage< vigra::UInt32Image >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write UInt32 image to file.");
  def("writeImage", pyWriteImage< vigra::Int32Image >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write Int32 image to file.");
  def("writeImage", pyWriteImage< vigra::UInt8RGBImage >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write RGB image (3xUInt8) to file.");
  def("writeImage", pyWriteImage< vigra::FImage >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write float image to file.");

  def("writeImage", pyWriteImage< vigra::BasicImageView< vigra::UInt8 > >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write UInt8 image to file.");
  def("writeImage", pyWriteImage< vigra::BasicImageView< vigra::UInt16 > >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write UInt16 image to file.");
  def("writeImage", pyWriteImage< vigra::BasicImageView< vigra::RGBValue< vigra::UInt8 > > >,
      ("imgIn", "strFilename", arg("strCompression")="100"), "Write RGB image (3xUInt8) to file.");



  wrapImage<vigra::UInt8>("Image");
  //wrapImage<vigra::UInt8>("ImageUInt8");
  wrapImage<vigra::UInt16>("ImageUInt16");
  wrapImage<vigra::Int16>("ImageInt16");
  wrapImage<vigra::UInt32>("ImageUInt32");
  wrapImage<vigra::Int32>("ImageInt32");

  wrapImage<float>("ImageFloat");

  wrapImageView<vigra::UInt8>("ImageViewUInt8");
  wrapImageView<vigra::UInt16>("ImageViewUInt16");
  wrapImageView<vigra::Int16>("ImageViewInt16");
  wrapImageView<vigra::UInt32>("ImageViewUInt32");
  wrapImageView<vigra::Int32>("ImageViewInt32");

  //pyWrapImage<int>("IImage");
  wrapRGBImage<vigra::UInt8>("ImageRGB");
  wrapRGBImageView<vigra::UInt8>("ImageViewRGB");

  //wrapRGBImage<uint8>("ImageRGB");

  //implicitly_convertible< vigra::BasicImage<uint8>, vigra::BasicImageView<uint8> >();


  wrapRGBValue<vigra::UInt8>("RGBValue");

  wrapFont("Font");

  PySequenceToArrayVector< vigra::BasicImage < vigra::UInt8 > >();
  PySequenceToArrayVector< vigra::BasicImage < vigra::UInt8 > const* >();
  PySequenceToArrayVector< vigra::BasicImage < vigra::UInt16 > >();
  PySequenceToArrayVector< vigra::BasicImage < vigra::UInt16 > const* >();
  PySequenceToArrayVector< vigra::BasicImage < vigra::Int16 > >();
  PySequenceToArrayVector< vigra::BasicImage < vigra::Int16 > const* >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::UInt8 > >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::UInt8 > const* >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::UInt16 > >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::UInt16 > const* >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::Int16 > >();
  PySequenceToArrayVector< vigra::BasicImageView < vigra::Int16 > const* >();

  PySequenceToArrayVector< vigra::RGBValue<vigra::UInt8> >();

  PySequenceToArrayVector< float >();

  def("makeRGBImage", pyMakeRGBImage1<vigra::UInt8>);
  def("makeRGBImage", pyMakeRGBImage2<vigra::UInt8>);

  def("imageToArray", pyImageToArray<vigra::BImage>);
  def("rgbImageToArray", pyRgbImageToArray<vigra::BasicImage< vigra::RGBValue<uint8> > >);


  def("labelImage", pyLabelImage<vigra::BImage, vigra::Int16Image>);

  def("windowAverageThreshold", pyWindowAverageThreshold<vigra::BImage, vigra::BImage>,
      (arg("imgIn"), arg("size"), arg("contrastLimit")=0, arg("lower")=0, arg("higher")=255),
      "Window Average Threshold of window size.");

  def("windowStdThreshold", pyWindowStdThreshold<vigra::BImage, vigra::BImage>,
      (arg("imgIn"), arg("size"), arg("threshold"), arg("contrastLimit")=0),
      "Window Stddev Threshold of window size and stddev threshold.");

  //  def("localAdaptiveThreshold_NewLimit", cecog::localAdaptiveThresholdNewLimit<vigra::BImage, vigra::BImage>);

  //def("localThreshold", pyLocalThreshold<vigra::BImage, vigra::BImage>);
  //def("globalThreshold", pyGlobalThreshold<vigra::BImage, vigra::BImage>);
  //def("backgroundSubtraction", pyBackgroundSubtraction<vigra::BImage, vigra::BImage>);

 // def("imageMean", pyImageMean< vigra::BImage >);
 // def("imageMax", pyImageMax< vigra::BImage >);
 // def("imageMin", pyImageMin< vigra::BImage >);

  def("discMedian", pyDiscMedian<vigra::UInt8Image, vigra::UInt8Image>);
  def("discMedian", pyDiscMedian<vigra::UInt16Image, vigra::UInt16Image>);
  def("discMedian", pyDiscMedian<vigra::Int16Image, vigra::Int16Image>);

  def("toggleMapping", pyToggleMapping<vigra::UInt8Image, vigra::UInt8Image>);
  def("toggleMapping", pyToggleMapping<vigra::UInt16Image, vigra::UInt16Image>);
  def("toggleMapping", pyToggleMapping<vigra::Int16Image, vigra::Int16Image>);

  def("gaussianFilter", pyGaussian<vigra::UInt8Image, vigra::UInt8Image>);
  def("gaussianFilter", pyGaussian<vigra::UInt16Image, vigra::UInt16Image>);
  def("gaussianFilter", pyGaussian<vigra::Int16Image, vigra::Int16Image>);

  def("scaleImage", pyScaleImage1< vigra::UInt8Image, vigra::UInt8Image >, (arg("imgIn"), arg("size"), arg("method")="linear"), "Scale image to size. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage1< vigra::UInt16Image, vigra::UInt16Image >, (arg("imgIn"), arg("size"), arg("method")="linear"), "Scale image to size. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage1< vigra::Int16Image, vigra::Int16Image >, (arg("imgIn"), arg("size"), arg("method")="linear"), "Scale image to size. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage1< vigra::UInt8RGBImage, vigra::UInt8RGBImage >, (arg("imgIn"), arg("size"), arg("method")="linear"), "Scale image to size. Interpolation methods: no, linear, spline");

  def("scaleImage", pyScaleImage2< vigra::UInt8Image, vigra::UInt8Image >, (arg("imgIn"), arg("scale"), arg("method")="linear"), "Scale image to scale factor. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage2< vigra::UInt16Image, vigra::UInt16Image >, (arg("imgIn"), arg("scale"), arg("method")="linear"), "Scale image to scale factor. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage2< vigra::Int16Image, vigra::Int16Image >, (arg("imgIn"), arg("scale"), arg("method")="linear"), "Scale image to scale factor. Interpolation methods: no, linear, spline");
  def("scaleImage", pyScaleImage2< vigra::UInt8RGBImage, vigra::UInt8RGBImage >, (arg("imgIn"), arg("scale"), arg("method")="linear"), "Scale image to scale factor. Interpolation methods: no, linear, spline");

  def("convolveImage", pyConvolveImage1< vigra::BImage, vigra::BImage, double >, (arg("imgIn"), arg("imgOut"), arg("oKernel2D")), "2D Kernel convolution");
  def("convolveImage", pyConvolveImage2< vigra::BImage, vigra::BImage, double, double >, (arg("imgIn"), arg("imgOut"), arg("oKernelX"), arg("oKernelY")), "1D Kernel convolution in X and Y");

  def("binImage", pyBinImage< vigra::BImage, vigra::BImage >, (arg("imgIn"), arg("iFactor")), "n times image binning");
//  def("binResampleImage", pyBinResampleImage< vigra::BImage, vigra::BImage >, (arg("imgIn"), arg("imgOut"), arg("iFactor")), "n times image binning and implicit resampling");


  def("watershedShape", cecog::watershedShape);
  def("watershedIntensity", cecog::watershedIntensity);

  def("linearTransform", pyLinearTransform<vigra::FImage, vigra::BImage>);
  def("linearTransform", pyLinearTransform<vigra::BImage, vigra::BImage>);
  def("linearTransform", pyLinearTransform<vigra::UInt16Image, vigra::BImage>);
  def("linearTransformU16", pyLinearTransform<vigra::UInt16Image, vigra::UInt16Image>);

  def("linearTransform2", pyLinearTransform2<vigra::FImage, vigra::UInt8Image>);
  def("linearTransform2", pyLinearTransform2<vigra::UInt8Image, vigra::UInt8Image>);
  def("linearTransform2", pyLinearTransform2<vigra::UInt16Image, vigra::UInt16Image>);

  def("linearTransform3", pyLinearTransform2<vigra::UInt16Image, vigra::UInt8Image>);

  def("linearRangeMapping", pyLinearRangeMapping<vigra::BImage, vigra::BImage>);
  //def("linearRangeMapping", pyLinearRangeMapping<vigra::UInt16Image, vigra::BImage>);
  def("linearRangeMapping", pyLinearRangeMapping<vigra::UInt16Image, vigra::UInt16Image>);

  def("histogramEqualization", pyHistogramEqualization<vigra::BImage>);
  def("histogramEqualization", pyHistogramEqualization<vigra::UInt16Image>);
  def("histogramEqualization", pyHistogramEqualization<vigra::Int16Image>);

  def("maxIntensityRGB", pyMaxIntensityRGB);
  def("maxIntensity", pyMaxIntensity);

  def("findStddev", pyFindStddev< vigra::UInt8Image, vigra::Int16Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of average and stddev for all labels of imgLabels measured in imIn.");
  def("findStddev", pyFindStddev< vigra::UInt8Image, vigra::UInt8Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of average and stddev for all labels of imgLabels measured in imIn.");

  def("findAverage", pyFindAverage< vigra::UInt8Image, vigra::Int16Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of average for all labels of imgLabels measured in imIn.");
  def("findAverage", pyFindAverage< vigra::UInt8Image, vigra::UInt8Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of average for all labels of imgLabels measured in imIn.");

  def("findMinmax", pyFindMinmax< vigra::UInt8Image, vigra::Int16Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of tuples(min,max) for all labels of imgLabels measured in imIn.");
  def("findMinmax", pyFindMinmax< vigra::UInt8Image, vigra::UInt8Image >,
      args("imgIn", "imgLabels", "iLabelCount"), "Return dict of tuples(min,max) for all labels of imgLabels measured in imIn.");

  def("drawContour", pyDrawContour< vigra::BImage, vigra::BRGBImage >, (arg("imgIn"), arg("imgOut"), arg("oValue"), arg("bQuad")=false), "Contours of input image. (8bit->RGB)");
  def("drawContour", pyDrawContour< vigra::BImage, vigra::BImage >, (arg("imgIn"), arg("imgOut"), arg("oValue"), arg("bQuad")=false), "Contours of input image. (8bit->8bit)");
  def("drawContour", pyDrawContour< vigra::Int16Image, vigra::BRGBImage >, (arg("imgIn"), arg("imgOut"), arg("oValue"), arg("bQuad")=false), "Contours of input image. (8bit->RGB)");
  def("drawContour", pyDrawContour< vigra::Int16Image, vigra::BImage >, (arg("imgIn"), arg("imgOut"), arg("oValue"), arg("bQuad")=false), "Contours of input image. (8bit->8bit)");
  //def("findStdDev", pyFindStdDev< vigra::BasicImageView<vigra::UInt8>, vigra::BasicImageView<vigra::Int32> >);

  def("copyImage", pyCopyImage< vigra::BImage, vigra::BImage >);
  def("copyImage", pyCopyImage< vigra::Int16Image, vigra::Int16Image >);
  def("copyImage", pyCopyImage< vigra::UInt16Image, vigra::UInt16Image >);
  def("copyImage", pyCopyImage< vigra::BRGBImage, vigra::BRGBImage >);
  def("copyImage", pyCopyImageGray< vigra::BRGBImage, vigra::BImage >);

  def("copySubImage", pyCopySubImage1< vigra::BImage, vigra::BImage >);
  def("copySubImage", pyCopySubImage1< vigra::Int16Image, vigra::Int16Image >);
  def("copySubImage", pyCopySubImage1< vigra::UInt16Image, vigra::UInt16Image >);
  def("copySubImage", pyCopySubImage1< vigra::BRGBImage, vigra::BRGBImage >);

  def("copySubImage", pyCopySubImage2< vigra::BImage, vigra::BImage >);
  def("copySubImage", pyCopySubImage2< vigra::Int16Image, vigra::Int16Image >);
  def("copySubImage", pyCopySubImage2< vigra::UInt16Image, vigra::UInt16Image >);
  def("copySubImage", pyCopySubImage2< vigra::BRGBImage, vigra::BRGBImage >);

  def("copyImageIf", pyCopyImageIf< vigra::BImage, vigra::BImage, vigra::BImage >);
  def("copyImageIf", pyCopyImageIf< vigra::BImage, vigra::Int16Image, vigra::BImage >);
  def("copyImageIf", pyCopyImageIf< vigra::Int16Image, vigra::BImage, vigra::Int16Image >);
  def("copyImageIf", pyCopyImageIf< vigra::Int16Image, vigra::Int16Image, vigra::Int16Image >);
  def("copyImageIf", pyCopyImageIf< vigra::BRGBImage, vigra::BImage, vigra::BRGBImage >);
  def("copyImageIf", pyCopyImageIf< vigra::BRGBImage, vigra::Int16Image, vigra::BRGBImage >);

  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::BImage, vigra::BImage, vigra::BImage >);
  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::BImage, vigra::Int16Image, vigra::BImage >);
  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::Int16Image, vigra::BImage, vigra::Int16Image >);
  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::Int16Image, vigra::Int16Image, vigra::Int16Image >);
  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::BRGBImage, vigra::BImage, vigra::BRGBImage >);
  def("copyImageIfLabel", pyCopyImageIfLabel< vigra::BRGBImage, vigra::Int16Image, vigra::BRGBImage >);

  def("subImage", pySubImage< vigra::BImage >);
  def("subImage", pySubImage< vigra::Int16Image >);
  def("subImage", pySubImage< vigra::UInt16Image >);
  def("subImage", pySubImage< vigra::UInt8RGBImage >);

  def("addImages", pyAddImages< vigra::UInt8Image, vigra::UInt8Image, vigra::UInt8Image>);
  def("addImages", pyAddImages< vigra::UInt16Image, vigra::UInt16Image, vigra::UInt16Image>);
  def("addImages", pyAddImages< vigra::Int16Image, vigra::Int16Image, vigra::Int16Image>);

  def("substractImages", pySubstractImages< vigra::UInt8Image, vigra::UInt8Image, vigra::UInt8Image>);
  def("substractImages", pySubstractImages< vigra::UInt16Image, vigra::UInt16Image, vigra::UInt16Image>);
  def("substractImages", pySubstractImages< vigra::Int16Image, vigra::Int16Image, vigra::Int16Image>);

  def("substractImages2", pySubstractImages2< vigra::UInt8Image, vigra::UInt8Image, vigra::UInt8Image >);
  def("substractImages2", pySubstractImages2< vigra::UInt16Image, vigra::UInt16Image, vigra::UInt16Image >);
  def("substractImages2", pySubstractImages2< vigra::Int16Image, vigra::Int16Image, vigra::Int16Image >);

  def("flatfieldCorrection", pyFlatfieldCorrection< vigra::UInt8Image, vigra::UInt8Image >);
  def("flatfieldCorrection", pyFlatfieldCorrection< vigra::UInt16Image, vigra::UInt16Image >);
  def("flatfieldCorrection", pyFlatfieldCorrection< vigra::Int16Image, vigra::Int16Image >);

  def("threshold", pyThreshold< vigra::UInt8Image, vigra::UInt8Image >);

  def("drawLine", pyDrawLine< vigra::BImage >, (arg("p1"), arg("p2"), arg("image"), arg("color"), arg("thick")=false), "Draws a line from p1 to p2.");
  def("drawLine", pyDrawLine< vigra::Int16Image >, (arg("p1"), arg("p2"), arg("image"), arg("color"), arg("thick")=false), "Draws a line from p1 to p2.");
  def("drawLine", pyDrawLine< vigra::UInt16Image >, (arg("p1"), arg("p2"), arg("image"), arg("color"), arg("thick")=false), "Draws a line from p1 to p2.");
  def("drawLine", pyDrawLine< vigra::BRGBImage >, (arg("p1"), arg("p2"), arg("image"), arg("color"), arg("thick")=false), "Draws a line from p1 to p2.");

  def("drawFilledCircle", pyDrawFilledCircle< vigra::BImage >, (arg("p"), arg("r"), arg("image"), arg("color")), "Draws a filled circle at point p with radius r.");
  def("drawFilledCircle", pyDrawFilledCircle< vigra::Int16Image >, (arg("p"), arg("r"), arg("image"), arg("color")), "Draws a filled circle at point p with radius r.");
  def("drawFilledCircle", pyDrawFilledCircle< vigra::UInt16Image >, (arg("p"), arg("r"), arg("image"), arg("color")), "Draws a filled circle at point p with radius r.");
  def("drawFilledCircle", pyDrawFilledCircle< vigra::BRGBImage >, (arg("p"), arg("r"), arg("image"), arg("color")), "Draws a filled circle at point p with radius r.");

  def("seededRegionExpansion", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                        vigra::ArrayOfRegionStatistics<cecog::SrgConstValueFunctor<double> > >,
      (arg("imgIn"), arg("imLabels"), arg("srgType"), arg("labelNumber"),
       arg("costThreshold"), arg("expansionRounds"), arg("sepExpandRounds")=0),
      "Expand an image of seeds (imgLabel) several rounds without overlapping different seeds.");

  def("seededRegionExpansionMean", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                            vigra::ArrayOfRegionStatistics<cecog::SrgMeanValueFunctor<double> > >,
      (arg("imgIn"), arg("imLabels"), arg("srgType"), arg("labelNumber"),
       arg("costThreshold"), arg("expansionRounds"), arg("sepExpandRounds")=0),
      "Expand an image of seeds (imgLabel) several rounds without overlapping different seeds by mean-functor of imgIn.");

  def("seededRegionExpansionNormMean", pySeededRegionExpansion< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                          vigra::ArrayOfRegionStatistics<cecog::SrgNormMeanValueFunctor<double> > >,
      (arg("imgIn"), arg("imLabels"), arg("srgType"), arg("labelNumber"),
       arg("costThreshold"), arg("expansionRounds"), arg("sepExpandRounds")=0),
      "Expand an image of seeds (imgLabel) several rounds without overlapping different seeds by norm. mean-functor of imgIn.");


  def("seededRegionShrinking", pySeededRegionShrinking< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                        vigra::ArrayOfRegionStatistics<cecog::SrgConstValueFunctor<double> > >,
      (arg("imgIn"), arg("imLabels"), arg("labelNumber"), arg("shrinkingRounds")),
      "Shrink an image of seeds (imgLabel) several rounds without overlapping different seeds.");

  def("seededRegionExpansionHalfSize", pySeededRegionShrinking< vigra::BImage, vigra::Int16Image, vigra::Int16Image,
                                                                vigra::ArrayOfRegionStatistics<cecog::ShrinkHalfSizeFunctor<double> > >,
      (arg("imgIn"), arg("imLabels"), arg("labelNumber"), arg("shrinkingRounds")),
      "Shrink an image of seeds (imgLabel) several rounds without overlapping different seeds.");


  enum_<cecog::ProjectionType>("ProjectionType")
  .value("MaxProjection",  cecog::MaxProjection)
  .value("MinProjection",  cecog::MinProjection)
  .value("MeanProjection", cecog::MeanProjection)
  ;

  def("projectImage", pyProjectImage< vigra::UInt8Image >);
  def("projectImage", pyProjectImage< vigra::Int16Image >);
  def("projectImage", pyProjectImage< vigra::UInt16Image >);

}


#endif // CECOG_WRAP_IMAGES
