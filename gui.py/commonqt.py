#!/usr/bin/python

#$Id: commonqt.py,v 1.4 2006-12-17 20:24:59 jorn Exp $

from PyQt4 import QtGui,QtCore
import datetime
import common

import matplotlib.figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg

def getTopLevelWidget(child):
    parent = child.parent()
    if parent==None or (child.windowFlags() & QtCore.Qt.Window): return child
    return getTopLevelWidget(parent)

# =======================================================================
# Functions for converting between Qt date/time object and Python
# date/time objects
# =======================================================================

# qtdate2datetime: Convert Qt QDate object to Python datetime object
def qtdate2datetime(qtdate):
    return datetime.datetime(qtdate.year(),qtdate.month(),qtdate.day())

# datetime2qtdate: Convert Python datetime object to Qt QDate object
def datetime2qtdate(dt):
    return QtCore.QDate(dt.year,dt.month,dt.day)

# qtdatetime2datetime: Convert Qt QDateTime object to Python datetime object
def qtdatetime2datetime(qtdatetime):
    d = qtdatetime.date()
    t = qtdatetime.time()
    return datetime.datetime(d.year(),d.month(),d.day(),t.hour(),t.minute(),t.second())

# datetime2qtdatetime: Convert Python datetime object to Qt QDateTime object
def datetime2qtdatetime(dt):
    return QtCore.QDateTime(QtCore.QDate(dt.year,dt.month,dt.day),QtCore.QTime(dt.hour,dt.minute,dt.second))

# =======================================================================
# PathEditor: a Qt widget for editing paths, combines line-edit widget
# for path name, and a browse button.
# =======================================================================

class PathEditor(QtGui.QWidget):
    def __init__(self,parent=None,compact=False,header=None,getdirectory=False,save=False):
        QtGui.QWidget.__init__(self, parent)

        if compact:
            text = '...'
        else:
            text = 'Browse...'

        lo = QtGui.QHBoxLayout()

        if header!=None:
            self.header = QtGui.QLabel(header,self)
            lo.addWidget(self.header)

        self.lineedit = QtGui.QLineEdit(self)
        lo.addWidget(self.lineedit)

        self.browsebutton = QtGui.QPushButton(text,self)
        lo.addWidget(self.browsebutton)

        self.setLayout(lo)

        self.connect(self.lineedit, QtCore.SIGNAL('textChanged(const QString &)'), self.onChanged)
        self.connect(self.lineedit, QtCore.SIGNAL('editingFinished()'), self.onEditingFinished)
        self.connect(self.browsebutton, QtCore.SIGNAL("clicked()"), self.onBrowse)

        self.getdirectory = getdirectory
        self.save = save

        self.filter=''
        self.forcedextension = ''

    def setPath(self,path):
        return self.lineedit.setText(path)

    def path(self):
        return unicode(self.lineedit.text())

    def onBrowse(self):
        if self.getdirectory:
            path = unicode(QtGui.QFileDialog.getExistingDirectory(self))
        elif self.save:
            path = unicode(QtGui.QFileDialog.getSaveFileName(self,'','',self.filter))
        else:
            path = unicode(QtGui.QFileDialog.getOpenFileName(self,'','',self.filter))

        # If the browse dialog was cancelled, just return.
        if path=='': return
        
        if self.forcedextension!='' and (not path.endswith(self.forcedextension)):
            # Append imposed extension
            path += self.forcedextension
        self.lineedit.setText(path)

    def hasPath(self):
        return (len(unicode(self.lineedit.text()))>0)

    def onChanged(self,text):
        self.emit(QtCore.SIGNAL('onChanged()'))

    def onEditingFinished(self):
        self.emit(QtCore.SIGNAL('editingFinished()'))


class LinkedFilePlotDialog(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self,parent)

        lo = QtGui.QHBoxLayout()

        lolist = QtGui.QVBoxLayout()

        self.label = QtGui.QLabel('Available variables:',self)
        lolist.addWidget(self.label)

        self.list = QtGui.QListWidget(self)
        self.list.setMaximumWidth(200)
        lolist.addWidget(self.list)
        
        lo.addLayout(lolist)

        self.panel = FigurePanel(self)
        lo.addWidget(self.panel)

        self.setLayout(lo)

        self.connect(self.list, QtCore.SIGNAL('itemSelectionChanged()'), self.onSelectionChanged)

        self.resize(700, 450)

    def setStore(self,varstore):
        self.varstore = varstore

        namedict = varstore.getVariableLongNames()
        for name in varstore.getVariableNames():
            item = QtGui.QListWidgetItem(namedict[name],self.list)
            item.setData(QtCore.Qt.UserRole,QtCore.QVariant(name))

        self.setWindowTitle('Variables in %s' % self.varstore.datafile.getName())

    def onSelectionChanged(self):
        items = self.list.selectedItems()
        varname = unicode(items[0].data(QtCore.Qt.UserRole).toString())
        self.panel.plot(self.varstore,varname)

class LinkedFileEditor(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self, parent)

        lo = QtGui.QHBoxLayout()

        self.patheditor = PathEditor(self,compact=True)
        self.patheditor.layout().setSpacing(0)
        self.patheditor.layout().setMargin(0)
        lo.addWidget(self.patheditor)

        self.plotbutton = QtGui.QPushButton('Plot',self)
        lo.addWidget(self.plotbutton)

        self.setLayout(lo)

        self.connect(self.patheditor, QtCore.SIGNAL('onChanged()'), self.onChanged)
        self.connect(self.plotbutton, QtCore.SIGNAL('clicked()'), self.onPlot)

    def onChanged(self):
        self.emit(QtCore.SIGNAL('onChanged()'))

    def setNode(self,node):
        self.node = node
        datafile = node.getValue()
        self.plotbutton.setEnabled(datafile.isValid())
        self.patheditor.setPath(datafile.getName())

    def path(self):
        return self.patheditor.path()

    def onPlot(self):
        dialog = LinkedFilePlotDialog(self)
        varstore = common.LinkedFileVariableStore(self.node)
        dialog.setStore(varstore)
        dialog.exec_()

# =======================================================================
# ScientificDoubleValidator: a Qt validator for floating point values
#   Less strict than the standard QDoubleValidator, in the sense that is
#   also accepts values in scientific format (e.g. 1.2e6)
#   Also has properties 'minimum' and 'maximum', used for validation and
#   fix-up.
# =======================================================================

class ScientificDoubleValidator(QtGui.QValidator):
    def __init__(self,parent=None):
        QtGui.QValidator.__init__(self,parent)
        self.minimum = None
        self.maximum = None
    
    def validate(self,input,pos):
        rx = QtCore.QRegExp('[^\d\-+eE,.]')
        if rx.indexIn(input)!=-1: return (QtGui.QValidator.Invalid,pos)
        
        try:
            v = float(input)
        except:
            return (QtGui.QValidator.Intermediate,pos)

        if self.minimum!=None and v<self.minimum: return (QtGui.QValidator.Intermediate,pos)
        if self.maximum!=None and v>self.maximum: return (QtGui.QValidator.Intermediate,pos)
        
        return (QtGui.QValidator.Acceptable,pos)

    def fixup(self,input):
        try:
            v = float(input)
        except:
            return

        if self.minimum!=None and v<self.minimum: input.replace(0,input.length(),str(self.minimum))
        if self.maximum!=None and v>self.maximum: input.replace(0,input.length(),str(self.maximum))

# =======================================================================
# PropertyDelegate: a Qt delegate used to create editors for property
# values.
#   Built to handle properties from our custom TypedXMLPropertyStore,
#   which stores typed properties in hierarchical structure (XML)
#   The internalPointer attribute of provided model indices must refer
#   to a node in the TypedXMLPropertyStore.
# =======================================================================

class PropertyDelegate(QtGui.QItemDelegate):

    def __init__(self,parent=None):
        QtGui.QItemDelegate.__init__(self,parent)

    # createEditor (inherited from QtGui.QItemDelegate)
    #   Creates the editor widget for the model item at the given index
    def createEditor(self, parent, option, index):
        node = index.internalPointer()

        editor = self.createNodeEditor(node,parent)

        lo = editor.layout()
        if lo!=None:
            lo.setMargin(0)
            lo.setSpacing(0)

        # Install event filter that captures key events for view from the editor (e.g. return press).
        editor.installEventFilter(self)
        
        return editor

    def createNodeEditor(self,node,parent):
        templatenode = node.templatenode
        nodetype = node.getValueType()
        editor = None
        if nodetype=='string':
            editor = QtGui.QLineEdit(parent)
        elif nodetype=='int':
            editor = QtGui.QSpinBox(parent)
            if templatenode.hasAttribute('minimum'): editor.setMinimum(int(templatenode.getAttribute('minimum')))
            if templatenode.hasAttribute('maximum'): editor.setMaximum(int(templatenode.getAttribute('maximum')))
        elif nodetype=='float':
            editor = QtGui.QLineEdit(parent)
            validator = ScientificDoubleValidator(editor)
            if templatenode.hasAttribute('minimum'): validator.minimum = float(templatenode.getAttribute('minimum'))
            if templatenode.hasAttribute('maximum'): validator.maximum = float(templatenode.getAttribute('maximum'))
            editor.setValidator(validator)
            self.currentvalidator = validator
        elif nodetype=='bool':
            editor = QtGui.QComboBox(parent)
            editor.addItem('True',QtCore.QVariant(True))
            editor.addItem('False',QtCore.QVariant(False))
        elif nodetype=='select':
            editor = QtGui.QComboBox(parent)
            options = common.findDescendantNode(templatenode,['options'])
            if options==None: raise 'Node is of type "select" but lacks "options" childnode.'
            for ch in options.childNodes:
                if ch.nodeType==ch.ELEMENT_NODE and ch.localName=='option':
                    editor.addItem(ch.getAttribute('label'),QtCore.QVariant(int(ch.getAttribute('value'))))
        elif nodetype=='datetime':
            editor = QtGui.QDateTimeEdit(parent)
        elif nodetype=='file':
            editor = LinkedFileEditor(parent)
            self.currenteditor = editor
        else:
            raise 'Unknown node type "'+str(nodetype)+'".'
        return editor

    # setEditorData (inherited from QtGui.QItemDelegate)
    #   Sets value in the editor widget, for the model item at the given index
    def setEditorData(self, editor,index):
        value = index.data(QtCore.Qt.EditRole)
        if not value.isValid(): return
        node = index.internalPointer()
        nodetype = node.getValueType()
        if nodetype=='string':
            editor.setText(value.toString())
        elif nodetype=='int':
            value,ret = value.toInt()
            editor.setValue(value)
        elif nodetype=='float':
            editor.setText(value.toString())
        elif nodetype=='bool':
            value = value.toBool()
            for ioption in range(editor.count()):
                optionvalue = editor.itemData(ioption).toBool()
                if optionvalue==value:
                    editor.setCurrentIndex(ioption)
                    break
        elif nodetype=='select':
            value,ret = value.toInt()
            for ioption in range(editor.count()):
                optionvalue,ret = editor.itemData(ioption).toInt()
                if optionvalue==value:
                    editor.setCurrentIndex(ioption)
                    break
        elif nodetype=='datetime':
            value = value.toDateTime()
            editor.setDateTime(value)
        elif nodetype=='file':
            editor.setNode(node)

    # setModelData (inherited from QtGui.QItemDelegate)
    #   Obtains the value from the editor widget, and set it for the model item at the given index
    def setModelData(self, editor, model, index):
        nodetype = index.internalPointer().getValueType()
        if nodetype=='string':
            model.setData(index, QtCore.QVariant(editor.text()))
        elif nodetype=='int':
            editor.interpretText()
            model.setData(index, QtCore.QVariant(editor.value()))
        elif nodetype=='float':
            tx = editor.text()
            if not editor.hasAcceptableInput(): editor.validator().fixup(tx)
            model.setData(index, QtCore.QVariant(tx))
        elif nodetype=='bool' or nodetype=='select':
            model.setData(index,editor.itemData(editor.currentIndex()))
        elif nodetype=='datetime':
            model.setData(index, QtCore.QVariant(editor.dateTime()))
        elif nodetype=='file':
            model.setData(index, QtCore.QVariant(editor.path()))

# =======================================================================
# PropertyData: a Qt item model that encapsulates our custom
# TypedXMLPropertyStore, used for hierarchical storage of typed properties
# =======================================================================

class PropertyStoreModel(QtCore.QAbstractItemModel):
    
    def __init__(self,typedstore,nohide = False):
        QtCore.QAbstractItemModel.__init__(self)

        self.typedstore = typedstore
        self.nohide = nohide

        self.typedstore.addVisibilityChangeHandler(self.beforeNodeVisibilityChange,self.afterNodeVisibilityChange)
        self.typedstore.addChangeHandler(self.onNodeChanged)
        self.typedstore.addStoreChangedHandler(self.reset)
        
    # index (inherited from QtCore.QAbstractItemModel)
    #   Supplies unique index for the node at the given (row,column) position
    #   below the given parent (specified as index).
    def index(self,irow,icolumn,parent):
        if not parent.isValid():
            parentnode = self.typedstore.root
        else:
            parentnode = parent.internalPointer()
        child = parentnode.getChildByIndex(irow,showhidden=self.nohide)
        return self.createIndex(irow,icolumn,child)

    # parent (inherited from QtCore.QAbstractItemModel)
    #   Supplies unique index for the parent of the given node (specified as index).
    def parent(self,index):
        # We must have a valid index
        if not index.isValid(): raise 'Asked for parent of root node, but Qt asker knows it is the root.'

        current = index.internalPointer()
        parent = current.parent

        if parent==None: raise 'We were asked for the parent of the actual root, but we should never have been able to get so far up the tree'
        
        if parent.parent==None: return QtCore.QModelIndex()
        return self.createIndex(parent.getOwnIndex(showhidden=self.nohide),0,parent)

    # rowCount (inherited from QtCore.QAbstractItemModel)
    #   Returns the number of child rows below the given parent (specified as index).
    def rowCount(self,parent=QtCore.QModelIndex()):
        if not parent.isValid():
            parentnode = self.typedstore.root
        else:
            parentnode = parent.internalPointer()

        return parentnode.getChildCount(showhidden=self.nohide)

    # columnCount (inherited from QtCore.QAbstractItemModel)
    #   Returns the number of child columns below the given parent (specified as index).
    def columnCount(self,parent):
        # We always have 2 columns (variable,value)
        return 2

    # data (inherited from QtCore.QAbstractItemModel)
    #   Returns data for the given node (specified as index), and the given role.
    def data(self,index,role=QtCore.Qt.DisplayRole):

        # First handle roles that are shared over the whole row.
        if role==QtCore.Qt.WhatsThisRole:
            node = index.internalPointer().templatenode
            if node.hasAttribute('description'):
                text = node.getAttribute('description')
            elif node.hasAttribute('label'):
                text = node.getAttribute('label').capitalize()
            else:
                text = node.getAttribute('id').capitalize()
            nodetype = node.getAttribute('type')
            if nodetype=='select':
                options = common.findDescendantNode(node,['options'])
                if options==None: raise 'variable with "select" type lacks "options" element below'
                for ch in options.childNodes:
                    if ch.nodeType==ch.ELEMENT_NODE and ch.localName=='option':
                        text += '\n- '
                        if ch.hasAttribute('description'):
                            text += ch.getAttribute('description')
                        else:
                            text += ch.getAttribute('label')
            elif nodetype=='int' or nodetype=='float':
                if node.hasAttribute('minimum'): text += '\nminimum value: '+node.getAttribute('minimum')
                if node.hasAttribute('maximum'): text += '\nmaximum value: '+node.getAttribute('maximum')
            return QtCore.QVariant(text)
        elif role==QtCore.Qt.TextColorRole:
            if self.nohide and index.internalPointer().isHidden():
                # If we should show 'hidden' nodes too, color them blue to differentiate.
                return QtCore.QVariant(QtGui.QColor(0,0,255))
            elif index.column()==1 and index.internalPointer().isReadOnly():
                # Color read-only nodes grey to differentiate.
                return QtCore.QVariant(QtGui.QColor(128,128,128))

        # Now handle column-specific roles.
        if index.column()==0:
            if role==QtCore.Qt.DisplayRole:
                # Get node (XML element) from given node index (QtCore.QModelIndex)
                node = index.internalPointer().templatenode
                label = ''
                if node.hasAttribute('label'):
                    label = node.getAttribute('label')
                else:
                    label = node.getAttribute('id')
                if label=='': raise 'Node to display does not have a "label" attribute, nor an "id" attribute.'

                return QtCore.QVariant(label)
            else:
                return QtCore.QVariant()
        else:
            # We only process the 'display' and 'edit' roles.
            if role!=QtCore.Qt.DisplayRole and role!=QtCore.Qt.EditRole: return QtCore.QVariant()

            # Get node (XML element) from given node index (QtCore.QModelIndex)
            node = index.internalPointer()
            templatenode = node.templatenode

            # Only variables can have a value.
            if templatenode.localName!='variable': return QtCore.QVariant()
            fieldtype = node.getValueType()
            
            # Get the current value of the variable
            value = node.getValue()

            # Now distinguish between display of value and editing of value.
            if role==QtCore.Qt.DisplayRole:
                if value==None: return QtCore.QVariant('')
                
                if fieldtype=='datetime':
                    # Format datetime according to our convention
                    value = value.strftime(common.datetime_displayformat)
                elif fieldtype=='file':
                    # Return filename only (not the path)
                    value = value.getName()
                elif fieldtype=='select':
                    # Get label of currently selected option
                    options = common.findDescendantNode(templatenode,['options'])
                    if options==None: raise 'variable with "select" type lacks "options" element below'
                    for ch in options.childNodes:
                        if ch.nodeType==ch.ELEMENT_NODE and ch.localName=='option':
                            if value==int(ch.getAttribute('value')):
                                # We found the currently selected option; its label will serve as displayed value.
                                value = ch.getAttribute('label')
                                break
                else:
                    value = unicode(value)

                # Append unit specifier (if available)
                if templatenode.hasAttribute('unit'):
                    value = value + ' ' + templatenode.getAttribute('unit')

                # Now return the current value (= string).
                return QtCore.QVariant(value)
            else:
                if value==None: return QtCore.QVariant()
                if fieldtype=='datetime':
                    # First convert Python datetime to QDateTime, then cast to variant.
                    return QtCore.QVariant(datetime2qtdatetime(value))
                elif fieldtype=='file':
                    # Return full path
                    return QtCore.QVariant(unicode(value))
                else:
                    # Simply cast the current value to variant.
                    return QtCore.QVariant(value)

    # setData (inherited from QtCore.QAbstractItemModel)
    #   Set data for the given node (specified as index), and the given role.
    def setData(self,index,value,role=QtCore.Qt.EditRole):
        if index.column()!=1:
            raise 'Column '+str(index.column())+' is being set, but should not be editable (only column 1 should)'

        # Get node (XML element) from given node index (QtCore.QModelIndex)
        node = index.internalPointer()
        templatenode = node.templatenode

        if not value.isValid():
            node.clearValue()
            return True
        
        # Get the type of the variable
        fieldtype = node.getValueType()

        # Convert given variant to the type we need.
        if fieldtype=='string':
            value = value.toString()
        elif fieldtype=='file':
            value = common.DataFile(value.toString())
        elif fieldtype=='int':
            value,converted = value.toInt()
            if not converted: return False
            if templatenode.hasAttribute('minimum'):
                if value<int(templatenode.getAttribute('minimum')): return False
            if templatenode.hasAttribute('maximum'):
                if value>int(templatenode.getAttribute('maximum')): return False
        elif fieldtype=='float':
            value,converted = value.toDouble()
            if not converted: return False
            if templatenode.hasAttribute('minimum'):
                if value<float(templatenode.getAttribute('minimum')): return False
            if templatenode.hasAttribute('maximum'):
                if value>float(templatenode.getAttribute('maximum')): return False
        elif fieldtype=='bool':
            value = value.toBool()
        elif fieldtype=='datetime':
            value = qtdatetime2datetime(value.toDateTime())
        elif fieldtype=='select':
            value,converted = value.toInt()
            if not converted: return False
        else:
            raise 'unknown variable type "' + fieldtype + '" in XML scenario template'

        node.setValue(value)

        return True

    # flags (inherited from QtCore.QAbstractItemModel)
    #   Returns flags applicable to the given node.
    def flags(self,index):
        # If we do not have a valid index, return the default.
        if not index.isValid(): return QtCore.QAbstractItemModel(self,index)

        # Default flags: selectable and enabled
        f = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if index.column()==1:
            node = index.internalPointer()
            
            # If this is a variable, its value is also editable.
            if node.isVariable() and (not node.isReadOnly()): f = f | QtCore.Qt.ItemIsEditable
            
        return f

    # headerData (inherited from QtCore.QAbstractItemModel)
    #   Returns the header for the given row or column (in our case columns only).
    def headerData(self,section,orientation,role):
        if role==QtCore.Qt.DisplayRole:
            if section==0:
                return QtCore.QVariant('variable')
            elif section==1:
                return QtCore.QVariant('value')
        return QtCore.QVariant()

    def beforeNodeVisibilityChange(self,node,newvisibility,showhide):
        if self.nohide and showhide: return
        irow = node.getOwnIndex(showhidden=self.nohide)
        index = self.createIndex(irow,1,node)
        par = self.parent(index)
        if newvisibility:
            self.beginInsertRows(par,irow,irow)
        else:
            self.beginRemoveRows(par,irow,irow)

    def afterNodeVisibilityChange(self,node,newvisibility,showhide):
        if self.nohide and showhide: return self.onNodeChanged(node)
        if newvisibility:
            self.endInsertRows()
        else:
            self.endRemoveRows()

    def onNodeChanged(self,node):
        index = self.createIndex(node.getOwnIndex(showhidden=self.nohide),1,node)
        self.emit(QtCore.SIGNAL('dataChanged(const QModelIndex&,const QModelIndex&)'),index,index)

        # For debugging purposes only: write current scenario values to XML
        # self.typedstore.save('./scenario.xml')

# =======================================================================
# ExtendedTreeView: based on Qt QTreeView, additionally supports batch
# collapse/expand.
# =======================================================================

class ExtendedTreeView(QtGui.QTreeView):

    def __init__(self,parent=None):
        QtGui.QTreeView.__init__(self,parent)

    def setExpandedAll(self,value=True,maxdepth=1000,root=None,depth=0):
        model = self.model()
        if root==None: root=QtCore.QModelIndex()
        rc = model.rowCount(root)
        if rc>0:
            self.setExpanded(root,value)
            if depth<maxdepth:
                for ich in range(rc):
                    ch = model.index(ich,0,root)
                    self.setExpandedAll(value=value,root=ch,depth=depth+1,maxdepth=maxdepth)

    def contextMenuEvent(self,e):
        index = self.indexAt(e.pos())
        model = self.model()
        if (model.flags(index) & QtCore.Qt.ItemIsEditable) and index.isValid():
            menu = QtGui.QMenu(self)
            actReset = menu.addAction('Reset value')
            actChosen = menu.exec_(e.globalPos())
            if actChosen is actReset:
                model.setData(index,QtCore.QVariant())
            e.accept()

class PropertyEditorDialog(QtGui.QDialog):
    
    def __init__(self,parent,store,title='',instructions=''):
        QtGui.QDialog.__init__(self, parent)

        self.model = PropertyStoreModel(store,nohide=False)

        self.tree = ExtendedTreeView(self)
        self.delegate = PropertyDelegate()
        self.tree.setItemDelegate(self.delegate)
        self.tree.setModel(self.model)
        self.tree.setExpandedAll(maxdepth=1)

        layout = QtGui.QVBoxLayout()

        if instructions!='':
            lab = QtGui.QLabel(instructions,self)
            lab.setWordWrap(True)
            layout.addWidget(lab)

        layout.addWidget(self.tree)
        self.setLayout(layout)

        if title!='':
            self.setWindowTitle(title)

# =======================================================================
# Wizard: dialog for hosting series of 'wizard' pages
#   based on Qt example of a complex wizard
#   pages must inherit from class WizardPage below.
# =======================================================================

class Wizard(QtGui.QDialog):
    
    def __init__(self,parent=None,sequence=None,closebutton=False):
        QtGui.QDialog.__init__(self, parent, QtCore.Qt.Window|QtCore.Qt.WindowContextHelpButtonHint)

        layout = QtGui.QVBoxLayout()

        self.pm = QtGui.QPixmap('./logo.png','PNG')
        self.piclabel = QtGui.QLabel(self)
        self.piclabel.setPixmap(self.pm)
        self.piclabel.setScaledContents(True)
        layout.addWidget(self.piclabel)
        layout.setMargin(0)

        bnlayout = QtGui.QHBoxLayout()
        bnlayout.addStretch()

        self.bnHome = QtGui.QPushButton('&Home',self)
        self.connect(self.bnHome, QtCore.SIGNAL("clicked()"), self.onHome)
        bnlayout.addWidget(self.bnHome)

        self.bnBack = QtGui.QPushButton('< &Back',self)
        self.connect(self.bnBack, QtCore.SIGNAL("clicked()"), self.onBack)
        bnlayout.addWidget(self.bnBack)

        self.bnNext = QtGui.QPushButton('&Next >',self)
        self.connect(self.bnNext, QtCore.SIGNAL("clicked()"), self.onNext)
        bnlayout.addWidget(self.bnNext)

        if closebutton:
            self.bnClose = QtGui.QPushButton('&Close',self)
            self.connect(self.bnClose, QtCore.SIGNAL("clicked()"), self.onClose)
            bnlayout.addWidget(self.bnClose)

        bnlayout.setMargin(11)
        layout.addLayout(bnlayout)

        self.setLayout(layout)

        self.shared = {}

        self.sequence = sequence
        self.currentpage = None

    def unlink(self):
        for v in self.shared.values():
            try:
                v.unlink()
            except:
                pass

    def setSequence(self,sequence):
        self.sequence = sequence
        cls = self.sequence.getNextPage()
        self.switchPage(cls(self))

    def onNext(self):
        oldpage = self.currentpage
        if not oldpage.saveData(mustbevalid=True): return
        
        ready = False
        while not ready:
            cls = self.sequence.getNextPage()
            if cls==None:
                raise Exception('No next page available to show; the next button should have been disabled.')
            newpage = cls(self)
            ready = (not newpage.doNotShow())
        self.switchPage(newpage)

    def onBack(self):
        oldpage = self.currentpage
        if not oldpage.saveData(mustbevalid=False): return
        ready = False
        while not ready:
            cls = self.sequence.getPreviousPage()
            if cls==None:
                raise Exception('No previous page available to show; the back button should have been disabled.')
            newpage = cls(self)
            ready = (not newpage.doNotShow())
        self.switchPage(newpage)

    def onHome(self):
        oldpage = self.currentpage
        if not oldpage.saveData(mustbevalid=False): return
        cls = self.sequence.getPreviousPage()
        if cls==None:
            raise Exception('No previous page available to show; the home button should have been disabled.')
        while cls!=None:
            prevcls = cls
            cls = self.sequence.getPreviousPage()
        newpage = prevcls(self)
        self.switchPage(newpage)

    def onClose(self):
        self.close()

    def switchPage(self,newpage):
        layout = self.layout()
        if self.currentpage!=None:
            self.currentpage.hide()
            layout.removeWidget(self.currentpage)
            self.disconnect(self.currentpage, QtCore.SIGNAL("onCompleteStateChanged()"),self.onCompleteStateChanged)
        self.currentpage = newpage
        layout.insertWidget(1,self.currentpage)
        self.currentpage.show()
        self.connect(self.currentpage, QtCore.SIGNAL("onCompleteStateChanged()"),self.onCompleteStateChanged)
        cangoback = (self.sequence.getPreviousPage(stay=True)!=None)
        self.bnHome.setEnabled(cangoback)
        self.bnBack.setEnabled(cangoback)
        self.onCompleteStateChanged()

    def onCompleteStateChanged(self):
        curpage = self.currentpage
        enable = (curpage.isComplete() and self.sequence.getNextPage(stay=True)!=None)
        self.bnNext.setEnabled(enable)

# =======================================================================
# WizardPage: single page for the above Wizard class
#   based on Qt example of a complex wizard
# =======================================================================

class WizardPage(QtGui.QWidget):

    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.hide()

    def isComplete(self):
        return False

    def completeStateChanged(self):
        self.emit(QtCore.SIGNAL('onCompleteStateChanged()'))

    def saveData(self,mustbevalid):
        return True

    def doNotShow(self):
        return False

class WizardDummyPage(WizardPage):
    def doNotShow(self):
        return True

class WizardSequence:

    def __init__(self,items=[]):
        self.items = items
        self.index = -1

    def getCurrentPage(self):
        if self.index==-1: return None
        cur = self.items[self.index]
        if isinstance(cur,WizardSequence):
            return cur.getCurrentPage()
        else:
            return cur

    def getNextPage(self,stay=False):
        if self.index==-1:
            if len(self.items)==0: raise Exception('WizardSequence contains no items')
        elif isinstance(self.items[self.index],WizardSequence):
            new = self.items[self.index].getNextPage(stay=stay)
            if new!=None:
                return new
            elif not stay:
                self.items[self.index].reset()
        if self.index>=(len(self.items)-1): return None
        ind = self.index + 1
        if not stay: self.index = ind
        new = self.items[ind]
        if isinstance(new,WizardSequence):
            return new.getNextPage(stay=stay)
        else:
            return new

    def getPreviousPage(self,stay=False):
        if self.index==-1:
            if len(self.items)==0: raise Exception('WizardSequence contains no items')
        elif isinstance(self.items[self.index],WizardSequence):
            new = self.items[self.index].getPreviousPage(stay=stay)
            if new!=None:
                return new
            elif not stay:
                self.items[self.index].reset()
        if self.index==0: return None
        
        if self.index==-1:
            ind = len(self.items)-1
        else:
            ind = self.index - 1
        if not stay: self.index = ind
        new = self.items[ind]
        if isinstance(new,WizardSequence):
            return new.getPreviousPage(stay=stay)
        else:
            return new
        
    def reset(self):
        self.index = -1

class WizardFork(WizardSequence):
    def __init__(self,wiz):
        WizardSequence.__init__(self,[])
        self.wizard = wiz

    def getNextPage(self,stay=False):
        if stay: return WizardSequence()
        if self.index==-1:
            seq = self.getSequence()
            if seq==None: raise Exception('Fork did not return a new sequence')
            self.items = [seq]
        return WizardSequence.getNextPage(self,stay=False)

    def getSequence(self):
        return None

class PropertyEditorFactory:

    def __init__(self,typedstore,live=False):
        self.store = typedstore
        self.changed = False
        self.live = live
        self.editors = []

        if self.live:
            self.store.addChangeHandler(self.onStoreNodeChanged)
            self.store.addVisibilityChangeHandler(None,self.onStoreVisibilityChanged)
            self.store.addStoreChangedHandler(self.onStoreChanged)

    def createEditor(self,location,parent):
        node = self.store.root.getLocation(location)
        if node==None:
            raise Exception('Unable to create editor for '+str(location)+'; this node does not exist.')
        editor = PropertyEditor(node,parent)
        editor.addChangeHandler(self.onNodeEdited)
        self.editors.append(editor)
        return editor

    def updateStore(self):
        for editor in self.editors:
            editor.updateStore()

    def hasChanged(self):
        return self.changed

    def onStoreNodeChanged(self,node):
        for editor in self.editors:
            if editor.node is node:
                editor.updateEditorValue()
                break

    def onStoreVisibilityChanged(self,node,visible,showhide):
        if not showhide: return
        for editor in self.editors:
            editor.updateEditorEnabled()

    def onStoreChanged(self):
        for editor in self.editors:
            editor.node = self.store.root.getLocation(editor.location)
            editor.updateEditorValue()
            editor.updateEditorEnabled()

    def onNodeEdited(self,editor):
        self.changed = True
        if self.live:
            if not editor.updateStore(): editor.updateEditorValue()

class PropertyEditor:

    def __init__(self,node,parent):
        self.node = node
        self.editor = self.createEditor(node,parent)
        self.updateEditorValue()
        self.updateEditorEnabled()
        self.changehandlers = []
        self.suppresschangeevent = False
        self.location = node.location[:]

    def updateStore(self):
        return self.setNodeData(self.editor,self.node)

    def updateEditorValue(self):
        self.setEditorData(self.editor,self.node)

    def updateEditorEnabled(self):
        self.editor.setEnabled(not self.node.isHidden())

    def addChangeHandler(self,callback):
        self.changehandlers.append(callback)

    def onChange(self):
        if not self.suppresschangeevent:
            for callback in self.changehandlers:
                callback(self)

    def createEditor(self,node,parent):
        templatenode = node.templatenode
        nodetype = node.getValueType()
        editor = None
        if nodetype=='string':
            editor = QtGui.QLineEdit(parent)
            editor.connect(editor, QtCore.SIGNAL("editingFinished()"), self.onChange)
        elif nodetype=='int':
            editor = QtGui.QSpinBox(parent)
            if templatenode.hasAttribute('minimum'): editor.setMinimum(int(templatenode.getAttribute('minimum')))
            if templatenode.hasAttribute('maximum'): editor.setMaximum(int(templatenode.getAttribute('maximum')))
            editor.connect(editor, QtCore.SIGNAL("editingFinished()"), self.onChange)
        elif nodetype=='float':
            editor = QtGui.QLineEdit(parent)
            validator = ScientificDoubleValidator(editor)
            if templatenode.hasAttribute('minimum'): validator.minimum = float(templatenode.getAttribute('minimum'))
            if templatenode.hasAttribute('maximum'): validator.maximum = float(templatenode.getAttribute('maximum'))
            editor.setValidator(validator)
            self.currentvalidator = validator
            editor.connect(editor, QtCore.SIGNAL("editingFinished()"), self.onChange)
        elif nodetype=='bool':
            editor = QtGui.QComboBox(parent)
            editor.addItem('True',QtCore.QVariant(True))
            editor.addItem('False',QtCore.QVariant(False))
            editor.connect(editor, QtCore.SIGNAL("currentIndexChanged(int)"), self.onChange)
        elif nodetype=='select':
            editor = QtGui.QComboBox(parent)
            options = common.findDescendantNode(templatenode,['options'])
            if options==None: raise 'Node is of type "select" but lacks "options" childnode.'
            for ch in options.childNodes:
                if ch.nodeType==ch.ELEMENT_NODE and ch.localName=='option':
                    editor.addItem(ch.getAttribute('label'),QtCore.QVariant(int(ch.getAttribute('value'))))
            editor.connect(editor, QtCore.SIGNAL("currentIndexChanged(int)"), self.onChange)
        elif nodetype=='datetime':
            editor = QtGui.QDateTimeEdit(parent)
            editor.connect(editor, QtCore.SIGNAL("editingFinished()"), self.onChange)
        elif nodetype=='file':
            editor = PathEditor(parent,compact=True)
            self.currenteditor = editor
            editor.connect(editor, QtCore.SIGNAL("editingFinished()"), self.onChange)
        else:
            raise 'Unknown node type "'+str(nodetype)+'".'
        return editor

    def setEditorData(self,editor,node):
        self.suppresschangeevent = True
        value = node.getValue()
        nodetype = node.getValueType()
        if value==None:
            if nodetype=='string' or nodetype=='float':
                editor.setText('')
            elif nodetype=='int':
                editor.setValue(0)
            elif nodetype=='bool' or nodetype=='select':
                editor.setCurrentIndex(0)
            elif nodetype=='datetime':
                editor.setDateTime(QtCore.QDateTime())
            elif nodetype=='file':
                editor.setPath('')
        else:
            if nodetype=='string':
                editor.setText(value)
            elif nodetype=='int':
                editor.setValue(value)
            elif nodetype=='float':
                editor.setText(unicode(value))
            elif nodetype=='bool':
                for ioption in range(editor.count()):
                    optionvalue = editor.itemData(ioption).toBool()
                    if optionvalue==value:
                        editor.setCurrentIndex(ioption)
                        break
            elif nodetype=='select':
                for ioption in range(editor.count()):
                    optionvalue,ret = editor.itemData(ioption).toInt()
                    if optionvalue==value:
                        editor.setCurrentIndex(ioption)
                        break
            elif nodetype=='datetime':
                editor.setDateTime(datetime2qtdatetime(value))
            elif nodetype=='file':
                editor.setPath(value)
        self.suppresschangeevent = False

    # setModelData (inherited from QtGui.QItemDelegate)
    #   Obtains the value from the editor widget, and set it for the model item at the given index
    def setNodeData(self,editor,node):
        nodetype = node.getValueType()
        if nodetype=='string':
            return node.setValue(editor.text())
        elif nodetype=='int':
            editor.interpretText()
            return node.setValue(editor.value())
        elif nodetype=='float':
            tx = editor.text()
            if not editor.hasAcceptableInput(): editor.validator().fixup(tx)
            try:
                tx = float(tx)
            except Exception,e:
                tx = None
            return node.setValue(tx)
        elif nodetype=='bool':
            return node.setValue(editor.itemData(editor.currentIndex()).toBool())
        elif nodetype=='select':
            return node.setValue(editor.itemData(editor.currentIndex()).toInt())
        elif nodetype=='datetime':
            return node.setValue(qtdatetime2datetime(editor.dateTime()))
        elif nodetype=='file':
            return node.setValue(editor.path())

class FigurePanel(QtGui.QWidget):
    
    def __init__(self,parent,detachbutton=True):
        QtGui.QWidget.__init__(self,parent)

        bgcolor = self.palette().window().color()
        mplfigure = matplotlib.figure.Figure(facecolor=(bgcolor.red()/255., bgcolor.green()/255., bgcolor.blue()/255.),edgecolor=(bgcolor.red()/255., bgcolor.green()/255., bgcolor.blue()/255.))
        self.figure = common.Figure(mplfigure)

        self.canvas = FigureCanvas(mplfigure)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        self.canvas.setMinimumSize(300,250)
        self.figure.canvas = self.canvas

        self.factory = PropertyEditorFactory(self.figure.properties,live=True)

        # Controls for time range.
        self.dateeditStart = self.factory.createEditor(['TimeAxis','Minimum'],self)
        self.dateeditStop  = self.factory.createEditor(['TimeAxis','Maximum'],self)

        # Controls for depth range.
        self.lineeditStartDepth = self.factory.createEditor(['DepthAxis','Minimum'],self)
        self.lineeditStopDepth = self.factory.createEditor(['DepthAxis','Maximum'],self)

        layout = QtGui.QVBoxLayout()
        
        layoutOptions = QtGui.QGridLayout()

        layoutTime = QtGui.QHBoxLayout()
        layoutTime.addWidget(self.dateeditStart.editor)
        self.labelDateTo = QtGui.QLabel(self.tr(' to '),self)
        layoutTime.addWidget(self.labelDateTo)
        layoutTime.addWidget(self.dateeditStop.editor)
        self.labelDateRange = QtGui.QLabel(self.tr('Time range:'),self)
        layoutOptions.addWidget(self.labelDateRange,1,0)
        layoutOptions.addLayout(layoutTime,1,1)
        
        layoutDepth = QtGui.QHBoxLayout()
        layoutDepth.addWidget(self.lineeditStartDepth.editor)
        self.labelDepthTo = QtGui.QLabel(self.tr(' to '),self)
        layoutDepth.addWidget(self.labelDepthTo)
        layoutDepth.addWidget(self.lineeditStopDepth.editor)
        self.labelDepthRange = QtGui.QLabel(self.tr('Depth range:'),self)
        layoutOptions.addWidget(self.labelDepthRange,2,0)
        layoutOptions.addLayout(layoutDepth,2,1)

        self.layoutOptions = layoutOptions

        self.buttonAdvanced = QtGui.QPushButton(self.tr('Advanced...'),self)
        self.buttonAdvanced.setAutoDefault(False)
        self.buttonAdvanced.setDefault(False)
        self.connect(self.buttonAdvanced, QtCore.SIGNAL('clicked()'), self.onAdvancedClicked)
        layoutOptions.addWidget(self.buttonAdvanced,3,0,1,2)

        self.layoutButtons = QtGui.QHBoxLayout()

        # Button for showing/hiding properties
        self.buttonProperties = QtGui.QPushButton(self.tr('Edit plot &properties'),self)
        self.buttonProperties.setAutoDefault(False)
        self.buttonProperties.setDefault(False)
        self.connect(self.buttonProperties, QtCore.SIGNAL('clicked()'), self.onPropertiesClicked)
        self.layoutButtons.addWidget(self.buttonProperties)

        # Button for exporting to file
        self.buttonExport = QtGui.QPushButton(self.tr('&Export to file'),self)
        self.buttonExport.setAutoDefault(False)
        self.buttonExport.setDefault(False)
        self.connect(self.buttonExport, QtCore.SIGNAL('clicked()'), self.onExport)
        self.layoutButtons.addWidget(self.buttonExport)

        # Button for printing
        self.buttonPrint = QtGui.QPushButton(self.tr('&Print'),self)
        self.buttonPrint.setAutoDefault(False)
        self.buttonPrint.setDefault(False)
        self.connect(self.buttonPrint, QtCore.SIGNAL('clicked()'), self.onPrint)
        self.layoutButtons.addWidget(self.buttonPrint)

        # Detach button
        if detachbutton:
            self.buttonDetach = QtGui.QPushButton('&Detach figure',self)
            self.buttonDetach.setAutoDefault(False)
            self.buttonDetach.setDefault(False)
            self.connect(self.buttonDetach, QtCore.SIGNAL('clicked()'), self.onDetach)
            self.layoutButtons.addWidget(self.buttonDetach)

        self.widgetProperties = QtGui.QWidget(self)
        self.widgetProperties.setLayout(layoutOptions)
        self.widgetProperties.setVisible(False)

        layout.addWidget(self.canvas)
        layout.addLayout(self.layoutButtons)
        layout.addWidget(self.widgetProperties)

        self.setLayout(layout)

        self.dialogAdvanced = None

        # Initially disable all controls; we have no plot to configure yet...
        self.setEnabled(False)

        self.detachedfigures = []

    def plot(self,varstore,varname):
        self.figure.setUpdating(False)
        self.figure.clearSources()
        self.figure.clearProperties()
        self.figure.addDataSource('main',varstore)
        self.figure.addVariable(varname)
        self.figure.setUpdating(True)
        self.setEnabled(True)

    def plotFromProperties(self,properties):
        self.figure.setProperties(properties)    
        self.setEnabled(True)

    def onAdvancedClicked(self):
        if self.dialogAdvanced==None:
            self.dialogAdvanced = PropertyEditorDialog(self,self.figure.properties,title='Figure properties')
        self.dialogAdvanced.show()
        self.dialogAdvanced.activateWindow()

    def onPropertiesClicked(self):
        window = getTopLevelWidget(self)
        window.setUpdatesEnabled(False)
        sz = window.size()
        if not self.widgetProperties.isVisible():
            self.widgetProperties.setVisible(True)
            self.buttonProperties.setText('Hide plot &properties')
            self.propheight = self.widgetProperties.height()+self.layout().spacing()
            sz.setHeight(sz.height() + self.propheight)
        else:
            self.widgetProperties.setVisible(False)
            self.buttonProperties.setText('Edit plot &properties')
            sz.setHeight(sz.height() - self.propheight)
        window.resize(sz)
        window.setUpdatesEnabled(True)

    def onExport(self):
        fname = QtGui.QFileDialog.getSaveFileName(self,'Choose location to save plot to','','Portable Network Graphics (*.png);;Encapsulated PostScript (*.eps);;Scalable Vector Graphics (*.svg);;Bitmap (*.bmp)')
        if fname:
            QtGui.qApp.setOverrideCursor(QtCore.Qt.WaitCursor)
            agg = self.canvas.switch_backends(FigureCanvasAgg)
            agg.print_figure(str(fname.toLatin1()),dpi=150, facecolor='w', edgecolor='w', orientation='portrait')
            self.canvas.figure.set_canvas(self.canvas)
            QtGui.qApp.restoreOverrideCursor()

            #self.canvas.print_figure( str(fname.toLatin1()) )
        
    def onPrint(self):
        printer = QtGui.QPrinter(QtGui.QPrinter.HighResolution)
        printDialog = QtGui.QPrintDialog(printer, self)
        if printDialog.exec_() == QtGui.QDialog.Accepted:
            print 'Printing to '+printer.printerName()
            p = QtGui.QPainter(printer)
            
            canvas = self.canvas.switch_backends(FigureCanvasAgg)

            # Store current DPI and colors.
            origDPI       = canvas.figure.dpi.get()
            origfacecolor = canvas.figure.get_facecolor()
            origedgecolor = canvas.figure.get_edgecolor()

            res = printer.resolution()
            if res>600: res=600
            print 'Using resolution of '+ str(res) + ' dpi.'

            # Adjust DPI and colors for printer.
            canvas.figure.dpi.set(res)
            canvas.figure.set_facecolor('w')
            canvas.figure.set_edgecolor('w')


            # Draw the plot (in memory)
            print 'MatPlotLib: creating Agg in-memory bitmap.'
            canvas.draw()

            # matplotlib is in rgba byte order.
            # qImage wants to put the bytes into argb format and
            # is in a 4 byte unsigned int.  little endian system is LSB first
            # and expects the bytes in reverse order (bgra).
            print 'Converting in-memory bitmap to format suitable for Qt.'
            if (QtCore.QSysInfo.ByteOrder == QtCore.QSysInfo.LittleEndian):
                stringBuffer = canvas.renderer._renderer.tostring_bgra()
            else:
                stringBuffer = canvas.renderer._renderer.tostring_argb()
                
            print 'Creating QImage object from in-memory data. Using width = ' + str(canvas.renderer.width) + ', height = '+ str(canvas.renderer.height)
            qImage = QtGui.QImage(stringBuffer, canvas.renderer.width, canvas.renderer.height, QtGui.QImage.Format_ARGB32)
            #pixmap = QtGui.QPixmap.fromImage(qImage)
            #print 'Drawing pixmap to QPainter object connected to printer.'
            #p.drawPixmap(QtCore.QPoint(0, 0), pixmap )
            print 'Drawing bitmap to QPainter object connected to printer.'
            p.drawImage(QtCore.QPoint(0, 0), qImage)
            #p.drawImage(QtCore.QPoint(0, 0), qImage, QtCore.QRect(0,0,1000,1000))
            print 'Done drawing; closing painter.'
            p.end()

            print 'printing done; restoring original figure resolution and color.'

            # Restore original DPI and colors.
            canvas.figure.dpi.set(origDPI)
            canvas.figure.set_facecolor(origfacecolor)
            canvas.figure.set_edgecolor(origedgecolor)

            # Restore original canvas.
            self.figure.figure.set_canvas(self.canvas)

    def onDetach(self):
        fd = FigureDialog(self,sourcefigure=self.figure)
        fd.show()
        self.detachedfigures.append(fd)

    def closeEvent(self,ev):
        for ch in self.detachedfigures: ch.close()
        QtGui.QWidget.closeEvent(self,ev)

class FigureDialog(QtGui.QDialog):
    
    def __init__(self,parent,sourcefigure):
        QtGui.QDialog.__init__(self,parent,QtCore.Qt.Window | QtCore.Qt.WindowMaximizeButtonHint | QtCore.Qt.WindowSystemMenuHint )

        self.setSizeGripEnabled(True)
        layout = QtGui.QVBoxLayout(self)
        self.panel = FigurePanel(self,detachbutton=False)
        layout.addWidget(self.panel)

        properties = sourcefigure.getPropertiesCopy()
        self.panel.figure.sources = sourcefigure.sources
        self.panel.figure.defaultsource = sourcefigure.defaultsource
        self.panel.plotFromProperties(properties)

        title = self.panel.figure.properties.getProperty(['Title'])
        self.setWindowTitle(title)

        # Prevent this window from keeping the appliaction alive after the main window was closed.
        self.setAttribute(QtCore.Qt.WA_QuitOnClose,False)
        
        self.resize(500, 500)