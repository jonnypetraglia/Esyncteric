import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

app = QtGui.QApplication([])

class GuiApp(QtGui.QMainWindow):
    def __init__(self):
        super(GuiApp, self).__init__()
        self.data = None
        try:
            _fromUtf8 = QtCore.QString.fromUtf8
        except AttributeError:
            _fromUtf8 = lambda s: s
        self.setWindowTitle('Subsonic')
        #self.setWindowIcon(QtGui.QIcon('web.png'))
        
        menubar = self.menuBar()
        newAction = QtGui.QAction('&New', self)
        newAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8("document-new")))
        newAction.setShortcut('Ctrl+N')
        newAction.setStatusTip('Create new sync config')
        #TODO: New dialog
        openAction = QtGui.QAction('&Open', self)
        openAction.setEnabled(False)
        openAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8("document-open")))
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open existing sync config')
        #TODO: Open dialog
        exitAction = QtGui.QAction('&Quit', self)
        exitAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8("application-exit")))
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QtGui.qApp.quit)
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        
        self.refreshAction = QtGui.QAction('&Refresh', self)
        self.refreshAction.setEnabled(False)
        self.refreshAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8("view-refresh")))
        self.refreshAction.setShortcut('Ctrl+R')
        self.refreshAction.setStatusTip('Rescan the source and destination directories')
        #TODO: Refresh
        self.optionsAction = QtGui.QAction('&Options', self)
        self.optionsAction.setEnabled(False)
        self.optionsAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8('document-properties')))
        self.optionsAction.setStatusTip('Adjust settings for this sync configuration')
        #TODO: Options (CPU Cores, sourceDir, destDir, filetypes{cmd,to}
        toolMenu = menubar.addMenu('&Tools')
        toolMenu.addAction(self.refreshAction)
        toolMenu.addAction(self.optionsAction)
        
        aboutAction = QtGui.QAction('&About', self)
        aboutAction.setIcon(QtGui.QIcon.fromTheme(_fromUtf8("help-about")))
        aboutAction.setStatusTip('About Subsonic')
        helpMenu = menubar.addMenu('&Help')
        helpMenu.addAction(aboutAction)
        
        self.sourceTree = QtGui.QTreeWidget()
        self.sourceTree.setHeaderLabel("Source")
        self.sourceTree.setSortingEnabled(True)
        self.sourceTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.destinationTree = QtGui.QTreeWidget()
        self.destinationTree.setHeaderLabel("Destination")
        self.destinationTree.sortByColumn(0, QtCore.Qt.AscendingOrder)

        layout = QtGui.QGridLayout()
        layout.setDefaultPositioning
        layout.addWidget(self.sourceTree, 0, 0)
        layout.addWidget(self.destinationTree, 0, 1)
        widget = QtGui.QWidget(self)
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.show()
        
        self.red = QtCore.Qt.darkRed
        self.green = QtCore.Qt.darkGreen
        self.orange = QtCore.Qt.darkYellow
        self.default = QtCore.Qt.white
        
    def _createItem(self, text, parent, tristate=False):
        item = QtGui.QTreeWidgetItem(parent)
        item.setText(0, text)
        if tristate:
            item.setCheckState(0, QtCore.Qt.Unchecked)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)
        return item
    
    def _setBg(self, item, bg):
        item.setBackgroundColor(0, bg)
        item.setTextColor(0, QtCore.Qt.black if bg == QtCore.Qt.white else QtCore.Qt.white)
        
    def _getChild(self, item, ind):
        if isinstance(item, QtGui.QTreeWidget):
            return item.topLevelItem(ind)
        else:
            return item.child(ind)
        
    def _getChildCount(self, item):
        if isinstance(item, QtGui.QTreeWidget):
            return item.topLevelItemCount()
        else:
            return item.childCount()
    
    def _findChild(self, item, childText):
        low = 0
        high = self._getChildCount(item) -1
        mid = int((low+high) / 2)
        
        while low <= high and self._getChild(item, mid).text(0) != childText:
            if self._getChild(item, mid).text(0) < childText:
                low = mid + 1
            else:
                high = mid -1
            mid = int((low+high) / 2)
        if low > high:
            return None
        return self._getChild(item, mid)
        
        
    def _findItemInTree(self, item, tree):
        parents = self._getParents(item)
        parents.append(item)
        search = tree
        for p in parents:
            nextSearch = self._findChild(search, p.text(0))
            if not nextSearch:
                #break
                return None
            search = nextSearch
        return search if search != tree else None
        
    def _colorItem(self, item):
        parents = self._getParents(item)
        parents.append(item)
        destParents = []
        destSearch = self.destinationTree
        for p in parents:
            destSearch = self._findChild(destSearch, p.text(0))
            if not destSearch:
                break
            destParents.append(destSearch)
        d = 0
        for p in parents:
            self._doColoring(p, destParents[d] if d < len(destParents) else None)
            d += 1

    def _doColoring(self, item, destItem):
        if destItem:
            if item.checkState(0) == QtCore.Qt.Unchecked:
                self._setBg(destItem, self.red)
            else:
                self._setBg(item, self.default)
                self._setBg(destItem, self.default)
        else:
            if item.checkState(0) == QtCore.Qt.Unchecked:
                self._setBg(item, self.default)
            else:
                self._setBg(item, self.green)
            
    def _clickItem(self, item):
        self.sourceTree.itemChanged.disconnect(self._clickItem)
        self._colorItem(item)
        self.sourceTree.itemChanged.connect(self._clickItem)

    def _getParents(self, item):
        parentList = []
        p = item.parent()
        while p:
            parentList.append(p)
            p = p.parent()
        parentList.reverse()
        return parentList
                
            

    def loadData(self, data):
        if self.data:
            self.sourceTree.itemChanged.disconnect(self._clickItem)
        self.data = data
        self._load(self.sourceTree, data.source.fileList, self.sourceTree)
        self._load(self.destinationTree, data.dest.fileList, self.destinationTree)
        self.refreshAction.setEnabled(True)
        self.optionsAction.setEnabled(True)
        self.sourceTree.itemChanged.connect(self._clickItem)
    
    def _load(self, tree, fileList, parent, checkList={}):
        for key, value in fileList.items():
            if key==".":
                continue
            item = self._createItem(key, parent, tree==self.sourceTree)
            item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
            self._load(tree, value, item, checkList[key] if key in checkList else {})
        if "." in fileList:
            for key, value in fileList["."].items():
                item = self._createItem(key, parent, tree==self.sourceTree)
                self._colorItem(item)
                if "." in checkList and key in checkList["."]:
                    item.setCheckState(0, QtCore.Qt.Checked)
            if not isinstance(parent, QtGui.QTreeWidget):
                self._colorItem(parent)