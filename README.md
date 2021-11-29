# The CellCognition Project

 Copyright (c) 2006 - 2018 Gerlich Lab, IMBA Vienna, Austria  
 The software is released under the terms of LGPL. 

 [www.cellcognition-project.org](www.cellcognition-project.org)  
 [doc.cellcognition-project.org](http://doc.cellcognition-project.org)
 
 :warning: **This project is orphaned and not actively developed anymore**. Windows binaries might not work on Win10

## Development build

The Extension depends on libtiff and libvigra. Adopt the library/include
paths in the setup.cfg accordingly. On Unix (including OSX) like systems type:

### Unixoides System

```bash  
python setup.py build_ext --inplace
```

There's also am make file:

* ```make clean``` 
* ```make inplace``` - install the C++-extenstion inplace ad builds \*.rc and help files
* ```make dmg``` - Binary installer for MacOSX

### Windoze (7/8)

```bat
build_win64_bin.bat
```

## System installation (e.g. on a cluster):
  
```python
python setup.py install --prefix=<path-to-prefix>
```

**Note:**
If you are using Windows an can not use the make fils, removethe *build*- and *dist* directories and also the file
*./cecog/ccore/_cecog.pyd*


### Demo data (battery package)

The demo data contains:

* a small set of raw images.
* two classifiers for H2b and aTubulin.
* a pre-configured settings file.

The demo data allows to try out image image segmentation, feature extraction, classifcation. To try ou also tracking, event selection and error correction,
you need to download the full data set (206 frames, ~900Mb) from the [cellcogition website](https://www.cellcognition-project.org/demo_data)
