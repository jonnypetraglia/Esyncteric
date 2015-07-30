# encoding: utf-8
from tinytag import TinyTag
import json, os, subprocess, shutil, multiprocessing, argparse

APP_NAME = "Subsonic"
VERSION = "0.0.1"
AUTHOR = "Qweex LLC"
AUTHOR_URL = "qweex.com"


class DirListing:
    def __str__(self):
        return json.dumps(self.fileList, sort_keys=True, indent=4, separators=(',', ': '))
    
    def __init__(self, dirPath):
        if isinstance(dirPath, dict):
            self.dirPath = None
            self.fileList = self.fromJSON(dirPath)
        else:
            self.dirPath = dirPath
            self.fileList = {}
            self.walkDir(self.dirPath, self.fileList)
    
    def fromJSON(self, json):
        if "." in json and isinstance(json["."], list):
            files = json["."]
            json["."] = {}
            for f in files:
                splitext = os.path.splitext(f)
                json["."][splitext[0]] = splitext[1]
        for key, value in json.items():
            if key!=".":
                value = self.fromJSON(value)
        return json
                

    def walkDir(self, dir, files):
        for f in os.listdir(dir):
            if os.path.isfile(os.path.join(dir, f)):
                files.setdefault('.',{})
                splitext = os.path.splitext(f)
                files["."][splitext[0]] = splitext[1]
            else:
                files[f] = {}
                self.walkDir(os.path.join(dir, f), files[f])
    
    def minus(self, other):
        def helper(myList, otherList):
            result = {}
            for key in myList:
                if key == ".":
                    for basename in myList[key]:
                        if key not in otherList or basename not in otherList[key]:
                            result.setdefault(key,{})[basename] = myList[key][basename]
                elif key in otherList:
                    if isinstance(myList[key], dict):
                        result[key] = helper(myList[key], otherList[key])
                        if result[key] == {}:
                            del result[key]
                else:
                    result[key] = myList[key]
            return result
        return DirListing(helper(self.fileList, other.fileList))
    
    def altered(self, other):
        def helper(myList, otherList):
            result = {}
            for key in myList:
                if key == ".":
                    for basename in myList[key]:
                        if key in otherList and basename in otherList[key] and myList[key][basename] != otherList[key][basename]:
                            result.setdefault(key,{})[basename] = myList[key][basename]
                elif key in otherList:
                    if isinstance(myList[key], dict):
                        result[key] = helper(myList[key], otherList[key])
                        if result[key] == {}:
                            del result[key]
                    elif myList[key] != otherList[key]:
                        result[key] = myList[key]
            return result
        return DirListing(helper(self.fileList, other.fileList))
    
    def intersection(self, other):
        def helper(myList, otherList):
            result = {}
            for key in myList:
                if key == ".":
                    for basename in myList[key]:
                        if key in otherList and basename in otherList[key] and myList[key][basename] == otherList[key][basename]:
                            result.setdefault(key,{})[basename] = myList[key][basename]
                elif key in otherList:
                    if isinstance(myList[key], dict):
                        result[key] = helper(myList[key], otherList[key])
                        if result[key] == {}:
                            del result[key]
                    elif myList[key] == otherList[key]:
                        result[key] = myList[key]
            return result
        return DirListing(helper(self.fileList, other.fileList))
    
    def toConfig(self):
        def helper(myList):
            result = {}
            for key in myList:
                if key == ".":
                    for basename, ext in myList[key].items():
                        result.setdefault(key,[]).append(basename + ext)
                else:
                    result[key] = helper(myList[key])
                    if result[key] == {}:
                            del result[key]
            return result
        return helper(self.fileList)


    def addFiles(self, sourcePath, destPath):
        def helper(fileList, path=""):
            if "." in fileList:
                srcDir = os.path.join(sourcePath, path)
                destDir = os.path.join(destPath, path)
                if not os.path.isdir(destDir):
                    os.makedirs(destDir)
                for name, ext in fileList["."].items():
                    if ext.lower() not in syncConfig['filetypes']:
                        if dry_run:
                            print("COPY:", os.path.join(path, name + ext), "->", os.path.join(path, name + ext))
                        else:
                            shutil.copy2(
                                os.path.join(srcDir, name + ext),
                                os.path.join(destDir, name + ext))
                        continue
                    filetype = syncConfig['filetypes'][ext.lower()]
                    cmd = list(filetype['cmd'])
                    cmd[cmd.index(None)] = os.path.join(srcDir, name + ext)
                    if None in cmd:
                        cmd[cmd.index(None)] = os.path.join(destDir, name + filetype['to'])
                    if dry_run:
                        print("CONVERT:", os.path.join(path, name + ext), "->", os.path.join(path, name + filetype['to']))
                    else:
                        processes.add(subprocess.check_call(cmd, stdout=subprocess.DEVNULL))
                        if len(processes) >= max_processes:
                            os.wait()
                            processes.difference_update([p for p in processes if p.poll() is not None])
            for name in fileList:
                if name != ".":
                    helper(fileList[name], os.path.join(path, name))
        return helper(self.fileList)

    def removeFiles(self, destPath):
        def helper(fileList, path=""):
            destDir = os.path.join(destPath, path)
            if "." in fileList:
                for name, ext in fileList["."].items():
                    if dry_run:
                        print("REMOVE:", os.path.join(path, name + ext))
                    else:
                        os.remove(os.path.join(destDir, name + ext))
            for name in fileList:
                if name != ".":
                    helper(fileList[name], os.path.join(path, name))
            if path!= "" and not os.listdir(destDir):
                if dry_run:
                    print("RMDIR:", destDir)
                else:
                    os.rmdir(destDir)
        return helper(self.fileList)

class Data(object):
    global syncConfig
    def __init__(self, dataFile):
        self._dataFile = dataFile
        self._loaded = False
        self.reload()
        
    def reload(self):
        global syncConfig
        with open(self._dataFile) if isinstance(self._dataFile, str) else self._dataFile as jsonContents: 
            syncConfig = json.load(jsonContents)
        if not isinstance(self._dataFile, str):
            self._dataFile = self._dataFile.name
        return self.refresh()
        
    def refresh(self):
        self.config = DirListing(syncConfig['sync'])
        self.source = DirListing(syncConfig['sourceDir'])
        self.dest = DirListing(syncConfig['destDir'])
        self.added = self.source.minus(self.dest)
        self.removed = self.dest.minus(self.source)
        self.missing = self.config.minus(self.source)
        self.toTransfer = self.config.intersection(self.added)
        self.toRemove = self.dest.minus(self.config)
        self._loaded = True
        return self

    def performSync(self):
        self.toTransfer.addFiles(self.source.dirPath, self.dest.dirPath)
        self.toRemove.removeFiles(self.dest.dirPath)
        for p in processes:
            if p.poll() is None:
                p.wait()



def printj(j):
    print(json.dumps(j, sort_keys=True, indent=4, separators=(',', ': ')))
    

def check_negative(value):
    ivalue = int(value)
    if ivalue <= 0:
         raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    return ivalue


################################################

parser = argparse.ArgumentParser(description='One-way file-based syncronization with per-file selection & custom commands')
parser.add_argument('jsonfile', type=argparse.FileType('r'), nargs="?",
                   help='path to a JSON file containing a sync configuration')
parser.add_argument('--print',
                   choices=['all', 'config', 'source', 'dest', 'added', 'removed', 'missing', 'toTransfer', 'toRemove'],
                   help='prints JSON data but does not perform sync')
parser.add_argument('-d', '--dry', action='store_true',
                   help='simulate the sync but do not perform')
parser.add_argument('-g', '--gui', action='store_true',
                   help='show a GUI instead of performing the sync')
parser.add_argument('-c', '--concurrent', metavar="N", type=check_negative, default=multiprocessing.cpu_count(),
                   help='maximum number of concurrent transcoding processes; defaults to number of cores')
args = parser.parse_args()
if args.gui is False and args.jsonfile is None:
    parser.error("the following arguments are required: jsonfile")




processes = set()
max_processes = args.concurrent
dry_run = args.dry


if args.gui:
    import gui
    try:
        gui.app.setApplicationDisplayName(APP_NAME)
    except:
        gui.app.setApplicationName(APP_NAME)
    gui.app.setOrganizationName(AUTHOR)
    gui.app.setOrganizationDomain(AUTHOR_URL)
    gui.app.setApplicationVersion(VERSION)
    guiapp = gui.GuiApp()
    if args.jsonfile:
        guiapp.loadData(Data(args.jsonfile))
    gui.app.exec_()
else:
    data = Data(args.jsonfile)
    if args.print:
        printables = {
            'config':   config,
            'source':   source,
            'dest':     dest,
            'added':    added,
            'removed':  removed,
            'missing':  missing,
            'toTransfer': toTransfer,
            'toRemove': toRemove
        }
        if args.print=="all":
            for p in printables:
                print(printables[p])
        else:
            print(printables[args.print])
        exit(0)
    else:
        data.performSync()