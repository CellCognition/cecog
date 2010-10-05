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


#ifndef CECOG_WRAP_MAP
#define CECOG_WRAP_MAP

#include <map>
#include <memory>
#include <ostream>

#include <boost/python.hpp>
#include <boost/python/register_ptr_to_python.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/str.hpp>

#include <boost/shared_ptr.hpp>


using namespace boost::python;


template<class Key, class Val>
struct map_item
{
  typedef std::map<Key,Val> Map;

  static Val& get(Map & self, const Key idx)
  {
    if (self.find(idx) != self.end())
      return self[idx];
    PyErr_SetString(PyExc_KeyError,"Map key not found");
    throw_error_already_set();
  }

  static void set(Map& self, const Key idx, const Val val)
  {
    self[idx] = val;
  }

  static void del(Map& self, const Key n)
  {
    self.erase(n);
  }

  static bool in(Map const& self, const Key n)
  {
    return self.find(n) != self.end();
  }

  static list keys(Map const& self)
  {
    list t;
    for (typename Map::const_iterator it=self.begin(); it!=self.end(); ++it)
      t.append(it->first);
    return t;
  }

  static list values(Map const& self)
  {
    list t;
    for (typename Map::const_iterator it=self.begin(); it!=self.end(); ++it)
      t.append(it->second);
    return t;
  }

  static list items(Map const& self)
  {
    list t;
    for (typename Map::const_iterator it=self.begin(); it!=self.end(); ++it)
      t.append( make_tuple(it->first, it->second) );
    return t;
  }

  static const str tostring(Map const& self)
  {
    dict d;
    for (typename Map::const_iterator it=self.begin(); it!=self.end(); ++it)
      d[it->first] = it->second;
    return str(d);
  }
};

template <class Key, class Val>
static void wrap_map(const std::string & pythonName)
{
  typedef std::map<Key,Val> Map;
  class_<Map>(pythonName.c_str())
  .def("__len__", &Map::size)
  .def("__getitem__", &map_item<Key,Val>().get, return_value_policy<copy_non_const_reference>())
  .def("__setitem__", &map_item<Key,Val>().set)
  .def("__delitem__", &map_item<Key,Val>().del)
  .def("__str__", &map_item<Key,Val>().tostring)
  .def("clear", &Map::clear)
  .def("__contains__", &map_item<Key,Val>().in)
  .def("has_key", &map_item<Key,Val>().in)
  .def("keys", &map_item<Key,Val>().keys)
  .def("values", &map_item<Key,Val>().values)
  .def("items", &map_item<Key,Val>().items)
  ;
  register_ptr_to_python< std::auto_ptr<Map> >();
}

#endif // CECOG_WRAP_MAP
