# encoding: utf-8
import json, os, subprocess, shutil, multiprocessing, argparse
import threading, signal, sys

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
        if not os.path.exists(dir):
            return
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

    def addFiles(self, sourcePath, destPath, filetypes, callback, err_callback, dry_run=False):
        def compileList(fileList, path=""):
            res = []
            if "." in fileList:
                srcDir = os.path.join(sourcePath, path)
                destDir = os.path.join(destPath, path)
                if not os.path.isdir(destDir) and not dry_run:
                    os.makedirs(destDir)
                for name, ext in fileList["."].items():
                    if ext.lower() not in filetypes:
                        if dry_run:
                            print("COPY:", os.path.join(path, name + ext), "->", os.path.join(path, name + ext))
                        else:
                            res.append({
                                "label": os.path.join(path, name + ext),
                                "cmd": shutil.copy2,
                                "args": [os.path.join(srcDir, name + ext), os.path.join(destDir, name + ext)]
                            })
                        continue
                    filetype = filetypes[ext.lower()]
                    cmd = list(filetype['cmd'])
                    srcFile = os.path.join(srcDir, name + ext)
                    destFile = os.path.join(destDir, name + filetype['to'])
                    if "{0}" in cmd:
                        cmd[cmd.index("{0}")] = srcFile
                        if "{1}" in cmd:
                            cmd[cmd.index("{1}")] = destFile
                    elif "{}" in cmd:
                        cmd[cmd.index("{}")] = srcFile
                        
                    if dry_run:
                        print("CALL:", cmd)
                    else:
                        res.append({
                            "label": os.path.join(path, name+ext),
                            "cmd": cmd,
                            "args": [srcFile, destFile]
                            })
            for name in fileList:
                if name != ".":
                    res.extend( compileList(fileList[name], os.path.join(path, name)) )
            return res

        return compileList(self.fileList)

    def removeFiles(self, destPath, callback, err_callback, dry_run=False):
        def rm(target):
            os.remove(target)
            dirpath = os.path.dirname(target)
            if dirpath!= "" and not os.listdir(dirpath):
                if dry_run:
                    print("RMDIR:", dirpath)
                else:
                    os.rmdir(dirpath)
        def helper(fileList, path=""):
            res = []
            destDir = os.path.join(destPath, path)
            if "." in fileList:
                for name, ext in fileList["."].items():
                    if dry_run:
                        print("REMOVE:", os.path.join(path, name + ext))
                    else:
                        res.append({
                            "label": os.path.join(path, name + ext),
                            "cmd": rm,
                            "args": [os.path.join(destDir, name + ext)]
                        })
            for name in fileList:
                if name != ".":
                    res.extend( helper(fileList[name], os.path.join(path, name)) )
            return res
        return helper(self.fileList)


class ConsistentProcess:
    def __init__(self, cmd, args, label):
        self.cmd = cmd
        self.args = args
        self.label = label
        if self.callable():
            self.proc = multiprocessing.Process(target=cmd, args=args)
        else:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.killed = False

    def callable(self):
        return callable(self.cmd)

    def kill(self):
        self.killed = True
        if self.callable():
            self.proc.terminate()
        else:
            self.proc.send_signal(signal.SIGINT)

    def stdout(self):
        if self.callable():
            return ""
        else:
            return self.proc.stdout.read()

    def stderr(self):
        if self.callable():
            return ""
        else:
            return self.proc.stderr.read()

    def is_alive(self):
        if self.callable():
            return self.proc.is_alive()
        else:
            return self.proc.poll()==None

    def returncode(self):
        if self.callable():
            return self.proc.exitcode
        else:
            return self.proc.returncode

    def wait(self):
        if self.callable():
            self.proc.start()
            self.proc.join()
        else:
            self.proc.wait()
        


class MahPool:
    def __init__(self, commands, cb, ercb): 
        self.commands = commands
        self.tasks = []
        self.active = []
        self.success_callback = cb
        self.error_callback = ercb
        self.stop_on_error = True
        while self.another():
            pass

        self.running = len(self.active) > 0
        
        self.oldSignalHandler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self.sigint_handler)

    def kill_all(self):
        for p in self.tasks:
            if p.is_alive():
                p.kill()

    def sigint_handler(self, signal, frame):
        self.kill_all()
        if self.oldSignalHandler:
            return self.oldSignalHandler(signal, frame)

    def wait(self):
        while self.running:
            pass


    def another(self):
        if len(self.commands)==0 or len(self.active) >= args.concurrent:
            return False
        cmd = self.commands.pop()
        def runInThread():
            proc = ConsistentProcess(label=cmd['label'], cmd=cmd['cmd'], args=cmd['args'])
            self.tasks.append(proc)
            proc.wait()
            self.active.remove(thread)
            if proc.returncode()==0:
                if self.success_callback:
                    self.success_callback(proc)
            else:
                if self.error_callback:
                    self.error_callback(proc)
                if self.stop_on_error:
                    self.kill_all()
                    self.running = False
                    return
            if not self.another() and len(self.active)==0:
                self.running = False;
        thread = threading.Thread(target=runInThread)
        self.active.append(thread)
        thread.start()
        return True

class Data(object):

    def __init__(self, dataFile):
        self._loaded = False
        self.jsonFile = dataFile
        self.syncConfig = dict(jsonFile=None, files=None)
        if self.jsonFile:
            self.reload()
        else:
            self.original = None

    def resetOriginals(self):
        self.original = {
            'sourceDir': self.getField('sourceDir'),
            'destDir': self.getField('destDir'),
            'files': self.getField('files'),
            'filetypes': self.getField('filetypes')
        }
        return self
        
    def reload(self):
        with open(self.jsonFile) if isinstance(self.jsonFile, str) else self.jsonFile as jsonContents: 
            self.syncConfig = json.load(jsonContents)
        if not isinstance(self.jsonFile, str):
            self.jsonFile = self.jsonFile.name
        self.resetOriginals()
        self.filetypes = self.syncConfig['filetypes'] if 'filetypes' in self.syncConfig else {}
        return self.rescan()
        
    def rescan(self):
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
    
    def performSync(self, cb=None, ecb=None, dry=False):
        cmds = self.toTransfer.addFiles(self.source.dirPath, self.dest.dirPath, self.filetypes, cb, ecb, dry)
        cmds.extend( self.toRemove.removeFiles(self.dest.dirPath, cb, ecb, dry) )
        return MahPool(cmds, cb, ecb)

    
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
                return True
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


def handle_siginit(signal, frame):
    print("SIGINT received, exiting")
    sys.exit(1)
signal.signal(signal.SIGINT, handle_siginit)


if args.gui:
    import gui
    gui.GuiApp(
        APP_NAME,
        AUTHOR,
        AUTHOR_URL,
        VERSION,
        DirListing,
        Data(args.jsonfile))
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
        def cb(x):
            sys.stdout.write(".")
            #print(x.stdout())
        def err(x):
            if x.killed:
                # Just canceled
                #print("canceled", x.cmd)
                pass
            else:
                # An actual error occurred
                print(x.stderr())
        pool = data.performSync(cb, err, args.dry)
        pool.wait()
        print("Done")