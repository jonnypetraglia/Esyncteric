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
        
        def createAction(label, icon, shortcut, desc, slot):
            action = QtGui.QAction(QtGui.QIcon.fromTheme(_fromUtf8(icon)), label, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.setStatusTip(desc)
            action.triggered.connect(slot)
            return action
        
        menubar = self.menuBar()
        newAction = createAction("&New", "document-new", "Ctrl+N", 'Create new sync config', self.fileNew)
        openAction = createAction("&Open", "document-open", "Ctrl+O", 'Open existing sync config', self.fileOpen)
        saveAction = createAction("&Save", "document-save", "Ctrl+S", 'Save config to disk', self.fileSave)
        exitAction = createAction("&Quit", "application-exit", "Ctrl+Q", 'Exit application', QtGui.qApp.quit)
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)
        fileMenu.addAction(exitAction)
        
        refreshAction = createAction("&Refresh", "view-refresh", "Ctrl+R", 'Rescan the source and destination directories', self.refresh)
        optionsAction = createAction("&Options", "document-properties", None, 'Adjust settings for this sync configuration', self.showOptions)
        toolMenu = menubar.addMenu('&Tools')
        toolMenu.addAction(refreshAction)
        toolMenu.addAction(optionsAction)
        
        
        self.actionsRequiringAFileBeOpen = [
            saveAction, refreshAction, optionsAction
            ]
        
        aboutAction = createAction("&About", "help-about", None, 'About Subsonic', self.about)
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
        self.resize(800, 600)
        self.show()
        
        self.red = QtCore.Qt.darkRed
        self.green = QtCore.Qt.darkGreen
        self.orange = QtCore.Qt.darkYellow
        self.default = QtCore.Qt.white
    
    def refresh(self):
        self.sourceTree.clear()
        self.destinationTree.clear()
        self.loadData(self.data.refresh())
        
    def fileNew(self):
        #TODO: New dialog
        pass
    def fileSave(self):
        #TODO: Save
        pass
    
    def showOptions(self):
        #TODO: Options (CPU Cores, sourceDir, destDir, filetypes{cmd,to}
        pass
    
    def about(self):
        #TODO: About
        pass
        
    def fileOpen(self):
        x = QtGui.QFileDialog.getOpenFileName(self, 'Open Existing Sync File', None, "JSON (*.json)")
        if not x:
            return
        self.data._dataFile = x
        self.sourceTree.clear()
        self.destinationTree.clear()
        self.loadData(self.data.reload())
        
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
        
    def _colorItem(self, item):
        def doColoring(item, destItem):
            if destItem:
                if item.checkState(0) == QtCore.Qt.Unchecked:
                    setBg(destItem, self.red)
                else:
                    setBg(item, self.default)
                    setBg(destItem, self.default)
            else:
                if item.checkState(0) == QtCore.Qt.Unchecked:
                    setBg(item, self.default)
                else:
                    setBg(item, self.green)
        def getParents(item):
            parentList = []
            p = item.parent()
            while p:
                parentList.append(p)
                p = p.parent()
            parentList.reverse()
            return parentList
        def setBg(item, bg):
            item.setBackgroundColor(0, bg)
            item.setTextColor(0, QtCore.Qt.black if bg == QtCore.Qt.white else QtCore.Qt.white)
        parents = getParents(item)
        parents.append(item)
        destParents = []
        destSearch = self.destinationTree
        for p in parents:
            destSearch = self._findChild(destSearch, p.text(0))
            if not destSearch:
                break
            destParents.append(destSearch)
        for x in range(0, len(parents)):
            doColoring(parents[x], destParents[x] if x < len(destParents) else None)
            
    def _clickItem(self, item):
        self.sourceTree.itemChanged.disconnect(self._clickItem)
        self._colorItem(item)
        self.sourceTree.itemChanged.connect(self._clickItem)
                
            
    def loadData(self, data):
        def load(tree, fileList, parent, checkList={}):
            def createItem(text, parent, tristate=False):
                item = QtGui.QTreeWidgetItem(parent)
                item.setText(0, text)
                if tristate:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)
                return item
            
            for key, value in fileList.items():
                if key==".":
                    continue
                item = createItem(key, parent, tree==self.sourceTree)
                item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
                load(tree, value, item, checkList[key] if key in checkList else {})
            if "." in fileList:
                for key, value in fileList["."].items():
                    item = createItem(key, parent, tree==self.sourceTree)
                    if "." in checkList and key in checkList["."]:
                        item.setCheckState(0, QtCore.Qt.Checked)
                    self._colorItem(item)
                if not isinstance(parent, QtGui.QTreeWidget):
                    self._colorItem(parent)

        
        if self.data:
            self.sourceTree.itemChanged.disconnect(self._clickItem)
        self.data = data
        load(self.destinationTree, data.dest.fileList, self.destinationTree)
        load(self.sourceTree, data.source.fileList, self.sourceTree, data.config.fileList)
        for action in self.actionsRequiringAFileBeOpen:
            action.setEnabled(True)
        self.sourceTree.itemChanged.connect(self._clickItem)

