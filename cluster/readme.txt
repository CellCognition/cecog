INSTALLATION
============
python setup.py install --prefix <directory>

You might adjust the RCFILE variable in cecog-gateway and also write a
custom cellcognition.xx file.

Cluster setup for CellCognition

*) cecocg-gateway - is the init script which goes into /etc/init.d/
*) cellcognition  - shall be placed in /etc/default or $HOME. $HOME overwrites /etc/default.
*) gateway.py - is the actual clusterservice, started by the init script.
