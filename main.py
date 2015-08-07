# encoding: utf-8
import json, os, subprocess, shutil, multiprocessing, argparse
from concurrent.futures import ProcessPoolExecutor as Pool


APP_NAME = "Esyncteric"
VERSION = "0.0.1"
AUTHOR = "Qweex LLC"
AUTHOR_URL = "qweex.com"

#http://stackoverflow.com/questions/25120363/python-multiprocessing-execute-external-command-and-wait-before-proceeding


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

    def _call_proc(self, cmd):
        """ This runs in a separate thread. """
        print("Calling", cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return (out, err)


    def addFiles(self, sourcePath, destPath, filetypes, callback, dry_run=False):
        def asdf(signal, frame):
            #print("!!!!!!!!!!!!", signal, frame)
            import sys
            for p in pending:
                print("Canceling", p.running(), p.src)
                remove = p.running()
                try: print("Canceled?", p.cancel())
                except Exception: pass
                if remove:
                    filePath = os.path.join(destPath, p.dest)
                    if os.path.exists(filePath):
                        os.remove(filePath)
            sys.exit(0)
        import signal
        signal.signal(signal.SIGINT, asdf) #SIG_DFL
        #signal.signal(signal.SIGINT, signal.SIG_DFL)
        pool = Pool(max_workers=max_processes)
        pending = []
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
                    cmd[cmd.index(None)] = os.path.join(srcDir, name + ext)
                    if None in cmd:
                        cmd[cmd.index(None)] = os.path.join(destDir, name + filetype['to'])
                    if dry_run:
                        print("CONVERT:", os.path.join(path, name + ext), "->", os.path.join(path, name + filetype['to']))
                    else:
                        filename = os.path.join(path, name + ext)
                        print("Adding", filename)
                        future = pool.submit(self._call_proc, cmd)
                        future.src = filename
                        future.dest = os.path.join(path, name + filetype['to'])
                        future.cmd = cmd
                        future.add_done_callback(callback)
                        pending.append(future)
            for name in fileList:
                if name != ".":
                    helper(fileList[name], os.path.join(path, name))
        helper(self.fileList)
        #pool.shutdown(True)
        return pool, pending

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
        
    def reload(self):
        with open(self.jsonFile) if isinstance(self.jsonFile, str) else self.jsonFile as jsonContents: 
            self.syncConfig = json.load(jsonContents)
        self.filetypes = self.syncConfig['filetypes'] if 'filetypes' in self.syncConfig else {}
        if not isinstance(self.jsonFile, str):
            self.jsonFile = self.jsonFile.name
        return self.refresh()
        
    def refresh(self):
        self.config = DirListing(self.syncConfig['files'])
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
    
    def callback(self, future):
        try:
            print("Callback", future.dest, future.result())
        except Exception:
            print("EXCEPTION!")

    def performSync(self, dry=False):
        pool, pending = self.toTransfer.addFiles(self.source.dirPath, self.dest.dirPath, self.filetypes, self.callback, dry)
        self.toRemove.removeFiles(self.dest.dirPath, dry)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        for result in pending:
            out, err = result.result()
            #print("out: {} err: {}".format(out, err))
    
    def setField(self, field, value):
        if field not in ['files', 'sourceDir', 'destDir']:
            raise ValueError("Field error:" + field)
        self.syncConfig[field] = value
        if field=="files":
            self.config = DirListing(self.syncConfig['files'])
    
    def toConfig(self):
        output = {
            "sourceDir": self.syncConfig['sourceDir'],
            "destDir": self.syncConfig['destDir'],
            "files": self.config.toConfig()
            }
        if self.filetypes:
            output['filetypes'] = self.filetypes
        return json.dumps(output, sort_keys=False, indent=4, separators=(',', ': '))



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