import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import os, re, signal, sys


class GuiApp(QtGui.QApplication):
    def __init__(self, APP_NAME, AUTHOR, AUTHOR_URL, VERSION, data):
        super(GuiApp, self).__init__([])
        try:
            self.setApplicationDisplayName(APP_NAME)
        except:
            self.setApplicationName(APP_NAME)
        self.setOrganizationName(AUTHOR)
        self.setOrganizationDomain(AUTHOR_URL)
        self.setApplicationVersion(VERSION)

        signal.signal(signal.SIGINT, self.terminate)

        timer = QtCore.QTimer()
        timer.start(500)  # You may change this if you wish.
        timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
        window = GuiWindow(self, data)
        sys.exit(self.exec_())

    def name(self):
        try:
            return self.applicationDisplayName()
        except:
            return self.applicationName()

    def terminate(self, *args):
        self.quit()

class GuiWindow(QtGui.QMainWindow):
    def __init__(self, guiApp, data):
        super(GuiWindow, self).__init__()
        self.app = guiApp
        self.data = data
        try:
            _fromUtf8 = QtCore.QString.fromUtf8
        except AttributeError:
            _fromUtf8 = lambda s: s
        self.setWindowTitle(self.app.name())
        self.setWindowIcon(QtGui.QIcon('esoteric-154605_640.png'))
        
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
        saveAsAction = createAction("Save &As", "document-save-as", "Ctrl+Shift+S", 'Save config as a new file', self.fileSaveAs)
        quitAction = createAction("&Quit", "application-exit", "Ctrl+Q", 'Exit application', self.closeEvent)
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)
        fileMenu.addAction(saveAsAction)
        fileMenu.addAction(quitAction)
        
        runAction = createAction("&Run", "system-run", None, 'Perform the sync', self.runSync)
        dryRunAction = createAction("&Dry run", None, None, 'Perform the sync', self.dryRunSync)
        settingsAction = createAction("&Settings", "document-properties", None, 'Adjust settings for this sync configuration', self.showSettings)
        settingsAction.setMenuRole(QtGui.QAction.NoRole)
        syncMenu = menubar.addMenu('&Sync')
        syncMenu.addAction(runAction)
        syncMenu.addAction(dryRunAction)
        syncMenu.addAction(settingsAction)
        
        refreshAction = createAction("&Refresh", "view-refresh", "Ctrl+R", 'Rescan the source and destination directories', self.refresh)
        aboutAction = createAction("&About", "help-about", None, 'About %s' % self.app.name(), self.about)
        aboutQtAction = createAction("About &Qt", "help-about", None, 'About Qt', self.aboutQt)
        toolMenu = menubar.addMenu('&Tools')
        toolMenu.addAction(refreshAction)
        toolMenu.addAction(aboutAction)
        toolMenu.addAction(aboutQtAction)
        
        
        self.actionsRequiringAFileBeOpen = [
            saveAction, refreshAction, runAction, dryRunAction, settingsAction
            ]
        
        self.sourceTree = QtGui.QTreeWidget()
        self.sourceTree.setHeaderLabel("Source")
        self.sourceTree.setSortingEnabled(True)
        self.sourceTree.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.destinationTree = QtGui.QTreeWidget()
        self.destinationTree.setHeaderLabel("Destination")
        self.destinationTree.setSortingEnabled(True)
        self.destinationTree.sortByColumn(0, QtCore.Qt.AscendingOrder)

        splitter = QtGui.QSplitter()
        splitter.addWidget(self.sourceTree)
        splitter.addWidget(self.destinationTree)
        self.setCentralWidget(splitter)


        self.statusBar = QtGui.QStatusBar()
        self.progress = QtGui.QProgressBar()
        self.progress.setMinimum(0)
        self.cancelBtn = QtGui.QPushButton("Cancel")
        self.statusBar.setStyleSheet("max-height: 32px")
        self.statusBar.addWidget(self.progress, 1)
        self.statusBar.addWidget(self.cancelBtn)
        self.statusBar.setEnabled(False)

        self.setStatusBar(self.statusBar)

        self.setAcceptDrops(True)
        self.resize(800, 600)
        self.show()
        
        self.disableOnSync = [
            newAction, openAction, runAction, dryRunAction, settingsAction, refreshAction, self.sourceTree, self.destinationTree
            ]
        
        self.red = QtCore.Qt.darkRed
        self.green = QtCore.Qt.darkGreen
        self.orange = QtCore.Qt.darkYellow
        self.default = QtCore.Qt.white
        
        if self.data._loaded:
            self.loadData()
        else:
            for x in self.actionsRequiringAFileBeOpen:
                x.setEnabled(False)

    
    def guiConfig(self, key):
        if key in self.data.getField('gui'):
            return self.data.getField('gui')[key]
        return None

    def updateSettings(self, newValues):
        err = None
        if not os.path.exists(newValues['sourceDir']):
            err = "sourceDir does not exist"
        elif not os.path.isdir(newValues['sourceDir']):
            err = "sourceDir is not a directory"
        elif not os.path.exists(newValues['destDir']):
            err = "destDir does not exist"
        elif not os.path.isdir(newValues['destDir']):
            err = "destDir is not a directory"
        else:
            if newValues['sourceDir'] != self.data.getField('sourceDir'):
                self.data.setField('files', None)
            for key, value in newValues.items():
                self.data.setField(key, value)
            self.refresh()
            return True

        QtGui.QMessageBox.critical(self, "Error", err)
        return False
       
    def fileNew(self):
        if not self._confirmDiscardChanges():
            return       
        def then():
            for x in self.actionsRequiringAFileBeOpen:
                x.setEnabled(True)
            self.data.jsonFile = None
            self.data.resetOriginals().refresh()
            self.loadData()
            pass

        settingsDialog = SettingsDialog(self, self.updateSettings, None)
        settingsDialog.accepted.connect(then)
        settingsDialog.exec()
    
    def fileSaveAs(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save sync config', "", '*.json')
        if filename:
            self.data.jsonFile = filename
            self.fileSave()
        
    def fileSave(self):
        if not self.data.jsonFile:
            return self.fileSaveAs()
        outputFile = QtCore.QFile(self.data.jsonFile);
        outputFile.open(QtCore.QFile.WriteOnly | QtCore.QFile.Truncate);
        self.data.setField('files', self.getSelected())
        self.data.originalDirs = {"sourceDir": self.data.getField('sourceDir'), "destDir": self.data.getField('destDir')}
        outputFile.write(self.data.toConfig())
        outputFile.resize(outputFile.pos())
 
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()
        
    def dropEvent(self, event):
        return self.fileOpen(event)
        
    def fileOpen(self, event):
        if not self._confirmDiscardChanges():
            return
        
        if event:
            filename = event.mimeData().urls()[0].toLocalFile()
        else:
            filename = QtGui.QFileDialog.getOpenFileName(self, 'Open Existing Sync File', None, "JSON (*.json)")
        if not filename:
            return
        oldFilename = self.data.jsonFile
        try:
            self.data.jsonFile = filename
            self.data.reload()
            self.loadData()
        except ValueError:
            self.data.jsonFile = oldFilename
            QtGui.QMessageBox.critical(self, "Error loading file", "File is not valid JSON")


    def closeEvent(self, event):
        if self.sourceTree.isEnabled() and not self._confirmDiscardChanges():
            return event.ignore() if event else None
        self.app.terminate()
    
    def refresh(self):
        self.data.rescan()
        self.loadData()
    
    def showSettings(self):
        settingsDialog = SettingsDialog(self, self.updateSettings, self.data.syncConfig)
        settingsDialog.accepted.connect(self.refresh)
        settingsDialog.exec()

    def runSync(self, dry=False):
        d = self.data.config.__class__(self.getSelected())
        for x in self.disableOnSync:
            x.setEnabled(False)
        self.statusBar.setEnabled(True)

        d = self.data.__class__(self.data.jsonFile)
        d.config = self.data.config.__class__(self.getSelected())
        d.rescan()

        self.pool = d.performSync(self.taskDone, self.taskError, dry)
        if not self.pool.running:
            self.syncFinished()
            return
        self.progress.setValue(0)
        self.progress.setMaximum(len(self.pool.commands))
        self.cancelBtn.clicked.connect(self.pool.kill_all)
    
    def dryRunSync(self):
        self.runSync(True)

   
    def taskDone(self, consistent_process):
        self.progress.setValue(len(self.pool.tasks))
        if len(self.pool.tasks) == len(self.pool.commands):
            self.syncFinished()

    def taskError(self, consistent_process):
        self.syncFinished()
        #print("<<<taskError", consistent_process.label)
        if not consistent_process.killed:
            m = "Encountered error:\n" + consistent_process.stderr()
            QtGui.QMessageBox.critical(self, "Error", m)
        if len(consistent_process.args)>1:
            if os.path.exists(consistent_process.args[1]):
                os.remove(consistent_process.args[1])

    def syncFinished(self):
        # Finished
        self.progress.setValue(self.progress.maximum())
        for x in self.disableOnSync:
            x.setEnabled(True)
        self.statusBar.setEnabled(False)
        self.data.rescan()
        #self.loadData()


    def about(self):
        message = self.app.organizationName() + "\n" + self.app.organizationDomain()
        #TODO: About
        QtGui.QMessageBox.about(self, self.app.name() + " " + self.app.applicationVersion(), message)

    def aboutQt(self):
        QtGui.QMessageBox.aboutQt(self, self.app.name() + " " + self.app.applicationVersion())


    def loadData(self):
        self.sourceTree.clear()
        self.destinationTree.clear()
        if self.data.jsonFile:
            self.setWindowTitle(self.app.name() + " - " + os.path.basename(self.data.jsonFile))
        else:
            self.setWindowTitle(self.app.name() + " - New File") 
        def createItem(text, parent, tristate=False):
            item = QtGui.QTreeWidgetItem()
            item.setText(0, text)
            if tristate:
                item.setCheckState(0, QtCore.Qt.Unchecked)
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)
            if isinstance(parent, QtGui.QTreeWidget):
                parent.invisibleRootItem().addChild(item)
            else:
                parent.addChild(item)
            return item

        def load(tree, fileList, parent, checkList={}):
            for key, value in fileList.items():
                if key==".":
                    continue
                item = createItem(key, parent, tree==self.sourceTree)
                item.setData(1, QtCore.Qt.EditRole, "folder")
                item.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
                load(tree, value, item, checkList[key] if key in checkList else {})
            if "." in fileList:
                for key, value in fileList["."].items():
                    # TODO: Better handling of filenameFilter if it is checked
                    ffilter = self.guiConfig('filenameFilter');
                    if ffilter:
                        if not ffilter.endswith("$"):
                            ffilter = ffilter + "$"
                        if not re.search(ffilter, key+value):
                            continue
                    item = createItem(key+value, parent, tree==self.sourceTree)
                    item.setData(1, QtCore.Qt.EditRole, "file")
                    if "." in checkList and key in checkList["."]:
                        item.setCheckState(0, QtCore.Qt.Checked)
                    self._colorItem(item)
            if not isinstance(parent, QtGui.QTreeWidget):
                if self.guiConfig('hideEmpty') and self._getChildCount(parent) == 0:
                    (parent.parent() or tree.invisibleRootItem()).removeChild(parent)
                else:
                    self._colorItem(parent)

        try: self.sourceTree.itemChanged.disconnect(self._clickItem)
        except Exception: pass

        self.sourceTree.setEnabled(False)
        self.destinationTree.setEnabled(False)
        load(self.destinationTree, self.data.dest.fileList, self.destinationTree)
        load(self.sourceTree, self.data.source.fileList, self.sourceTree, self.data.config.fileList)
        self.sourceTree.setEnabled(True)
        self.destinationTree.setEnabled(True)
        for action in self.actionsRequiringAFileBeOpen:
            action.setEnabled(True)
        self.sourceTree.itemChanged.connect(self._clickItem)

    def getSelected(self):
        def helper(node):
            result = {}
            for x in range(0, self._getChildCount(node)):
                child = self._getChild(node, x)
                name = child.text(0)
                if child.childIndicatorPolicy() == QtGui.QTreeWidgetItem.ShowIndicator:
                    res = helper(child)
                    if res != {}:
                        result[name] = res
                elif child.checkState(0) == QtCore.Qt.Checked:
                    result.setdefault('.',[]).append(name)
            return result
        return helper(self.sourceTree)

        
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
            if self._getChild(item, mid).text(0).lower() < childText.lower():
                low = mid + 1
            else:
                high = mid -1
            mid = int((low+high+1) / 2)
        if low > high or self._getChild(item, mid).text(0) != childText:
            return None
        return self._getChild(item, mid)
        
    def _colorItem(self, item):
        def doColoring(item, destItem):
            if destItem:
                setBg(item, self.default)
                if item.checkState(0) == QtCore.Qt.Unchecked:
                    setBg(destItem, self.red)
                else:
                    setBg(destItem, self.default)
            else:
                if item.checkState(0) == QtCore.Qt.Unchecked:
                    setBg(item, self.default)
                else:
                    setBg(item, self.green)
                    
        def setBg(item, bg):
            item.setBackgroundColor(0, bg)
            item.setTextColor(0, QtCore.Qt.black if bg == QtCore.Qt.white else QtCore.Qt.white)
                    
        def searchUp(item):
            parentList = []
            p = item.parent()
            while p:
                parentList.append(p)
                p = p.parent()
            parentList.reverse()
            parentList.append(item)
            return parentList
        
        searchText = item.text(0)
        
        def searchDown(item, searchPath):
            searchItems = []
            for p in searchPath:
                ptype = p.data(1, QtCore.Qt.EditRole)
                filename = p.text(0)
                spl = os.path.splitext(filename)
                if ptype == "file":
                    if spl[1] in self.data.filetypes:
                        filename = spl[0] + self.data.filetypes[spl[1]]['to']
                item = self._findChild(item, filename)
                if not item:
                    break
                searchItems.append(item)
            return searchItems
        
        sourceItems = searchUp(item) # Here we go up the sourceTree to get the parents of the item
        destItems = searchDown(self.destinationTree, sourceItems) # Here we go down the destinationTree as far as we can
        for x in range(0, len(sourceItems)):
            doColoring(sourceItems[x], destItems[x] if x < len(destItems) else None)
            
    def _clickItem(self, item):
        try: self.sourceTree.itemChanged.disconnect(self._clickItem)
        except Exception: pass
        self._colorItem(item)
        self.sourceTree.itemChanged.connect(self._clickItem)
        
    def _confirmDiscardChanges(self, current=None, data=None):
        def changesFound():
            reply = QtGui.QMessageBox.question(self, 'Message', 
                     "Are you sure you want to discard any unsaved changes?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            return reply == QtGui.QMessageBox.Yes

        if self.data.hasChanged():
            return changesFound()

        if not self.data._loaded or not self.data.getField('files'):
            return None

        def helper(current, data):
            if not data:
                return None
                
            if set(current.keys()) != set(data.keys()):
                return changesFound()
            for key in current:
                if type(current[key]) != type(data[key]):
                    return changesFound()
                if isinstance(current[key], dict):
                    childResult = helper(current[key], data[key])
                    if childResult!=None:
                        return childResult # Child already showed dialog and got a no
                elif isinstance(current[key], list):
                    if set(current[key]) != set(data[key]):
                        return changesFound()
                else:
                    if current[key] != data[key]:
                        return changesFound()
            return None # No changes, simulate a "yes"

        return helper(self.getSelected(), self.data.getField('files')) != False


class SettingsDialog(QtGui.QDialog):
    def __init__(self, parent, validationFunc, initialData):
        super(SettingsDialog, self).__init__(parent)
        self.validation = validationFunc
        self.initUI(initialData)


    def srcBrowse(self):
        chosen = QtGui.QFileDialog.getExistingDirectory(self, "Select source folder", None, QtGui.QFileDialog.ShowDirsOnly)
        if not chosen:
            return
        self.srcDir.setText(chosen)

    def destBrowse(self):
        chosen = QtGui.QFileDialog.getExistingDirectory(self, "Select destination folder", None, QtGui.QFileDialog.ShowDirsOnly)
        if not chosen:
            return
        self.destDir.setText(chosen)

    def performValidate(self):
        vals = {
            self.srcDir.objectName(): self.srcDir.text(),
            self.destDir.objectName(): self.destDir.text()
        }
        if self.validation(vals):
            self.accept();

    def initUI(self, data):
        self.setWindowIcon(QtGui.QIcon())
        layout = QtGui.QGridLayout()
        self.srcDir = QtGui.QLineEdit()
        self.destDir = QtGui.QLineEdit()
        self.filetypes = QtGui.QTreeWidget()
        self.filetypes.setColumnCount(2)
        self.filetypes.setHeaderLabels(["ext", "cmd"])

        self.srcDir.setObjectName("sourceDir")
        self.destDir.setObjectName("destDir")
        self.filetypes.setObjectName("filetypes")
        row = 0

        # Init the data
        if data:
            if self.srcDir.objectName() in data:
                self.srcDir.setText(data[self.srcDir.objectName()])
            if self.srcDir.objectName() in data:
                self.destDir.setText(data[self.destDir.objectName()])
            if self.filetypes.objectName() in data:
                for f in data[self.filetypes.objectName()]:
                    i = QtGui.QTreeWidgetItem([f, " ".join(data[self.filetypes.objectName()][f])])
                    i.setFlags(i.flags() | QtCore.Qt.ItemIsEditable)
                    self.filetypes.addTopLevelItem(i)
            if 'jsonFile' in data and data['jsonFile']:
                self.setWindowTitle("Sync Settings")
        else:
            self.setWindowTitle("New Settings")

        # Source
        srcDirTxt = QtGui.QLabel("Source Directory")
        srcDirBtn = QtGui.QPushButton("…")
        srcDirBtn.clicked.connect(self.srcBrowse);
        srcDirBtn.setAutoDefault(False);
        layout.addWidget(srcDirTxt, row, 0)
        layout.addWidget(self.srcDir, row, 1)
        layout.addWidget(srcDirBtn, row, 2)
        row+=1

        # Destination
        destDirTxt = QtGui.QLabel("Destination Directory")
        destDirBtn = QtGui.QPushButton("…")
        destDirBtn.clicked.connect(self.destBrowse);
        destDirBtn.setAutoDefault(False);
        layout.addWidget(destDirTxt, row, 0)
        layout.addWidget(self.destDir, row, 1)
        layout.addWidget(destDirBtn, row, 2)
        row+=1

        # Filetypes
        filetypesTxt = QtGui.QLabel("Filetypes")
        layout.addWidget(filetypesTxt, row, 0)
        layout.addWidget(self.filetypes, row, 1)
        row+=1

        # TODO: GUI section [filenameFilter, hideEmpty]

        # Save / Cancel
        buttonBox = QtGui.QDialogButtonBox()
        if data:
            saveBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Save)
        else:
            saveBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        cancelBtn = buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        saveBtn.clicked.connect(self.performValidate)
        cancelBtn.clicked.connect(self.reject)
        layout.addWidget(buttonBox, row, 1)
        row+=1

        # Finish
        layout.setColumnMinimumWidth(1, 300)
        self.setLayout(layout)

