# encoding: utf-8
import json, os, subprocess, shutil, multiprocessing, argparse

APP_NAME = "Esyncteric"
VERSION = "0.0.1"
AUTHOR = "Qweex LLC"
AUTHOR_URL = "qweex.com"


class DirListing:
    def __str__(self):
        return json.dumps(self.fileList, sort_keys=True, indent=4, separators=(',', ': '))
    
    def __init__(self, dirPath):
        if not dirPath:
            self.fileList = {}
            return
        if isinstance(dirPath, dict):
            self.dirPath = None
            self.fileList = self.fromJSON(dirPath)
        else:
            self.dirPath = dirPath
            self.fileList = {}
            self.walkDir(self.dirPath, self.fileList)
    
    def fromJSON(self, json):
        result = {}
        if "." in json:
            result["."] = {}
            for f in json["."]:
                if isinstance(json["."], list):
                    splitext = os.path.splitext(f)
                    result["."][splitext[0]] = splitext[1]
                elif isinstance(json["."], dict):
                    result["."][f] = json["."][f]
        for key, value in json.items():
            if key!=".":
                result[key] = self.fromJSON(value)
        return result
                

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


    def addFiles(self, sourcePath, destPath, filetypes, dry_run=False):
        def helper(fileList, path=""):
            if "." in fileList:
                srcDir = os.path.join(sourcePath, path)
                destDir = os.path.join(destPath, path)
                if not os.path.isdir(destDir):
                    os.makedirs(destDir)
                for name, ext in fileList["."].items():
                    if ext.lower() not in filetypes:
                        if dry_run:
                            print("COPY:", os.path.join(path, name + ext), "->", os.path.join(path, name + ext))
                        else:
                            shutil.copy2(
                                os.path.join(srcDir, name + ext),
                                os.path.join(destDir, name + ext))
                        continue
                    filetype = filetypes[ext.lower()]
                    cmd = list(filetype['cmd'])
                    cmd[cmd.index("$1")] = os.path.join(srcDir, name + ext)
                    if "$2" in cmd:
                        cmd[cmd.index("$2")] = os.path.join(destDir, name + filetype['to'])
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

    def removeFiles(self, destPath, dry_run=False):
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
    def __init__(self, dataFile):
        self._loaded = False
        self.jsonFile = dataFile
        self.syncConfig = dict(jsonFile=None, files=None)
        if self.jsonFile:
            self.reload()
        else:
            self.original = None
        
    def reload(self):
        if self.jsonFile:
            with open(self.jsonFile) if isinstance(self.jsonFile, str) else self.jsonFile as jsonContents: 
                self.syncConfig = json.load(jsonContents)
            if not isinstance(self.jsonFile, str):
                self.jsonFile = self.jsonFile.name
        self.original = {
            'sourceDir': self.getField('sourceDir'),
            'destDir': self.getField('destDir'),
            'files': self.getField('files'),
            'filetypes': self.getField('filetypes')
        }
        self.filetypes = self.syncConfig['filetypes'] if 'filetypes' in self.syncConfig else {}
        return self.refresh()
        
    def refresh(self):
        self.config = DirListing(self.syncConfig['files'] if 'files' in self.syncConfig else dict())
        self.source = DirListing(self.syncConfig['sourceDir'])
        self.dest = DirListing(self.syncConfig['destDir'])
        self.added = self.source.minus(self.dest)
        self.removed = self.dest.minus(self.source)
        self.missing = self.config.minus(self.source)
        #TODO: better handling of missing files rather than just ignoring them
        notMissing = self.config.minus(self.missing)
        self.toTransfer = notMissing.intersection(self.added)
        self.toRemove = self.dest.minus(self.config)
        self._loaded = True
        return self

    def performSync(self, dry=False):
        processes = self.toTransfer.addFiles(self.source.dirPath, self.dest.dirPath, s, dry)
        self.toRemove.removeFiles(self.dest.dirPath, dry)
        for p in processes:
            if p.poll() is None:
                p.wait()
    
    def setField(self, field, value):
        if field not in ['files', 'sourceDir', 'destDir', 'filetypes']:
            raise ValueError("Field error:" + field)
        self.syncConfig[field] = value
        if field=="files":
            self.config = DirListing(self.syncConfig['files'])

    def getField(self, field):
        if field in self.syncConfig:
            return self.syncConfig[field]
        return {}
    
    def toConfig(self):
        output = {
            "sourceDir": self.syncConfig['sourceDir'],
            "destDir": self.syncConfig['destDir'],
            "files": self.config.toConfig()
            }
        if self.filetypes:
            output['filetypes'] = self.filetypes
        return json.dumps(output, sort_keys=False, indent=4, separators=(',', ': '))

    def hasChanged(self):
        if not self.original:
            return False
        for key in self.original:
            if key == "gui" or key == "files":
                continue
            if key not in self.syncConfig or self.original[key] != self.syncConfig[key]:
                print(key + " has changed, ", self.original[key])
                return True
        print("No change")
        return False


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
    guiapp = gui.GuiApp(DirListing, Data(args.jsonfile))
    gui.app.exec_()
else:
    data = Data(args.jsonfile)
    if args.print:
        printables = {
            'config':   data.config,
            'source':   data.source,
            'dest':     data.dest,
            'added':    data.added,
            'removed':  data.removed,
            'missing':  data.missing,
            'toTransfer': data.toTransfer,
            'toRemove': data.toRemove
        }
        if args.print=="all":
            for p in printables:
                print(printables[p])
        else:
            print(printables[args.print])
        exit(0)
    else:
        data.performSync()