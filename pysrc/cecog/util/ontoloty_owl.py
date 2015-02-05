import rdflib
from ontospy.ontospy import Ontology
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal
from cecog.environment import CecogEnvironment
import os
import sys
from functools import partial



def getPrefLabel(onto, uriref):
    props = onto.classProperties(uriref)
    f_props = filter(lambda xxx: xxx[0].endswith("#prefLabel"), props)
    if len(f_props) == 0:
        f_props = filter(lambda xxx: xxx[0].endswith("#label"), props)
    return f_props[0][1]

def getDescription(onto, uriref):
    props = onto.classProperties(uriref)
    f_props = filter(lambda xxx: xxx[0].endswith("IAO_0000115"), props)
    if len(f_props) == 0:
        return 'No description'
    return f_props[0][1]


            
def map_traverse_QTreeWidget(func, tw_root):
    func(tw_root)
    for c_i in range(tw_root.childCount()):
        child = tw_root.child(c_i)
        func(child)
        map_traverse_QTreeWidget(func, child)
    
    
class FilterableQTreeWidget(QtGui.QWidget): 
    trigger_add = pyqtSignal(str)
    def __init__(self, *args, **kwargs):
        super(FilterableQTreeWidget, self).__init__(*args, **kwargs)
        
        self.tw = QtGui.QTreeWidget()
        self.tw.header().close()

        self.line_label = QtGui.QLabel("Filter:")
        self.line_edit = QtGui.QLineEdit()
        
        top_widget = QtGui.QWidget()
        top_layout = QtGui.QHBoxLayout()
        top_widget.setLayout(top_layout)
        
        top_layout.addWidget(self.line_label)
        top_layout.addWidget(self.line_edit)
        
        bot_widget = QtGui.QWidget()
        bot_layout = QtGui.QHBoxLayout()
        bot_widget.setLayout(bot_layout)
        
        self.add_button = QtGui.QPushButton("Add")
        self.close_button = QtGui.QPushButton("Close")
        bot_layout.addWidget(self.add_button)
        bot_layout.addWidget(self.close_button)
        
        self.info_field = QtGui.QTextEdit()
        self.info_field.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.info_field.setMaximumHeight(80)
        
        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(top_widget)
        main_layout.addWidget(self.tw)
        main_layout.addWidget(self.info_field)
        main_layout.addWidget(bot_widget)
        
        self.setLayout(main_layout)
    
        
        self.init_connects()
    

    def fillTree(self, *args, **kwargs):
        pass
    
    def init_connects(self):
        pass
    
    
class CecogOntologyBrowserWidget(FilterableQTreeWidget):
    def __init__(self, *args, **kwargs):
        super(CecogOntologyBrowserWidget, self).__init__(*args, **kwargs)
        
    
    def init_connects(self):
        FilterableQTreeWidget.init_connects(self)
        
        self.close_button.clicked.connect(self.parent().close)
        
        self.line_edit.textChanged.connect(self.cb_editingFinished)
        self.tw.itemClicked.connect(self.cb_item_clicked)
    
        self.add_button.clicked.connect(self.cb_add_button)
        
    def fillTree(self):
        self.root_items = []
        for i, ontology_file in enumerate(filter(lambda xxx: xxx.endswith(".owl"), os.listdir(CecogEnvironment.ONTOLOGY_DIR))):
            ontology_path = os.path.join(CecogEnvironment.ONTOLOGY_DIR, ontology_file)
            o = Ontology(ontology_path)
            onto_root_item = QtGui.QTreeWidgetItem([ontology_file])
            onto_root_item.ref = ("Ontology" + str(onto_root_item), o)
            self.tw.insertTopLevelItem(i, onto_root_item)
            for top_level_class in o.toplayer:
                top_level_item = QtGui.QTreeWidgetItem(onto_root_item, [getPrefLabel(o, top_level_class)])
                top_level_item.ref = (top_level_class, o)
                onto_root_item.addChild(top_level_item)
                self._fillQTreeWidget(o, top_level_class, top_level_item)
                
            self.root_items.append(onto_root_item)
    
    
    def _fillQTreeWidget(self, onto, parent_class, parent_item):
        children =  onto.ontologyClassTree[parent_class]
        
        if len(children) == 0:
            return
        else:
            for c in children:
                label = getPrefLabel(onto, c)
                c_item = QtGui.QTreeWidgetItem(parent_item, [str(label)])
                c_item.ref = (c, onto)
                parent_item.addChild(c_item)
                self._fillQTreeWidget(onto, c, c_item)
                
                
    def cb_hide_expand(self, txt, tw_item):
        def rec_parents(item_):
            item_.setExpanded(True)
            item_.setHidden(False)
            if item_.parent() is not None:
                rec_parents(item_.parent())
                
        if tw_item.parent() is not None:
            if txt in tw_item.text(0):
                rec_parents(tw_item)  
#             if tw_item.text(0).contains(txt):
#                 rec_parents(tw_item)       

    def cb_editingFinished(self, cur_text):
        if len(cur_text) > 1:
            [map_traverse_QTreeWidget(lambda xxx: xxx.setHidden(True), onto_root_item) for onto_root_item in self.root_items]
            if len(cur_text) > 0:
                [map_traverse_QTreeWidget(lambda xxx: self.cb_hide_expand(cur_text, xxx), onto_root_item) for onto_root_item in self.root_items]
            else:
                [map_traverse_QTreeWidget(lambda xxx: xxx.setExpanded(True), onto_root_item) for onto_root_item in self.root_items]
        else:
            [map_traverse_QTreeWidget(lambda xxx: xxx.setHidden(False), onto_root_item) for onto_root_item in self.root_items]
            
    def cb_item_clicked(self, item, col):
        info = str(item.ref[0]) + "\n\n"
        info += getDescription(item.ref[1], item.ref[0])
        self.info_field.setText(info)
        if item.childCount() == 0:
            self.add_button.setEnabled(True)
        else:
            self.add_button.setEnabled(False)
           
    def cb_add_button(self):
        item = self.tw.currentItem()
        
        self.trigger_add.emit(str(item.text(0)))
        
class CecogOntologyBrowserDialog(QtGui.QDialog):
    def __init__(self, *args, **kwargs):
        super(CecogOntologyBrowserDialog, self).__init__(*args, **kwargs)
        diag_layout = QtGui.QHBoxLayout(self)
        self.tw = CecogOntologyBrowserWidget(parent=self)
        self.tw.fillTree()
        diag_layout.addWidget(self.tw)
        self.setWindowTitle("CellCognition Ontology Browser")
        self.setLayout(diag_layout)
    
if __name__ == "__main__":
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    
    app = QtGui.QApplication(sys.argv)
    
    diag = QtGui.QDialog()
    diag_layout = QtGui.QHBoxLayout()
    diag.setLayout(diag_layout)
    tw = CecogOntologyBrowserWidget(parent=diag)
    tw.fillTree()
    
    diag_layout.addWidget(tw)
    
    def slot_(t):
        print "Add clicked with", t
    
    tw.trigger_add.connect(slot_)

    print diag.exec_()
    

    
    