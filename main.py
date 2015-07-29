# encoding: utf-8
import json, os
from tinytag import TinyTag
import subprocess
import shutil
import multiprocessing
import argparse


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
        # TODO: Filetype filtering
        for f in os.listdir(dir):
            if os.path.isfile(os.path.join(dir, f)):
                files.setdefault('.',{})
                splitext = os.path.splitext(f)
                files["."][splitext[0]] = splitext[1]
            else:
                files[f] = {}
                self.walkDir(os.path.join(dir, f), files[f])
    
    def minus(self, other):
        return DirListing(self._min(self.fileList, other.fileList))
    
    def altered(self, other):
        return DirListing(self._alt(self.fileList, other.fileList))
    
    def intersection(self, other):
        return DirListing(self._inter(self.fileList, other.fileList))
    
    def toConfig(self):
        return self._conf(self.fileList)
    
    def _inter(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                for basename in myList[key]:
                    if key in otherList and basename in otherList[key] and myList[key][basename] == otherList[key][basename]:
                        result.setdefault(key,{})[basename] = myList[key][basename]
            elif key in otherList:
                if isinstance(myList[key], dict):
                    result[key] = self._inter(myList[key], otherList[key])
                    if result[key] == {}:
                        del result[key]
                elif myList[key] == otherList[key]:
                    result[key] = myList[key]
        return result
    
    def _alt(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                for basename in myList[key]:
                    if key in otherList and basename in otherList[key] and myList[key][basename] != otherList[key][basename]:
                        result.setdefault(key,{})[basename] = myList[key][basename]
            elif key in otherList:
                if isinstance(myList[key], dict):
                    result[key] = self._alt(myList[key], otherList[key])
                    if result[key] == {}:
                        del result[key]
                elif myList[key] != otherList[key]:
                    result[key] = myList[key]
        return result
    
    def _min(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                for basename in myList[key]:
                    if key not in otherList or basename not in otherList[key]:
                        result.setdefault(key,{})[basename] = myList[key][basename]
            elif key in otherList:
                if isinstance(myList[key], dict):
                    result[key] = self._min(myList[key], otherList[key])
                    if result[key] == {}:
                        del result[key]
            else:
                result[key] = myList[key]
        return result
    
    def _conf(self, myList):
        result = {}
        for key in myList:
            if key == ".":
                for basename, ext in myList[key].items():
                    result.setdefault(key,[]).append(basename + ext)
            else:
                result[key] = self._conf(myList[key])
                if result[key] == {}:
                        del result[key]
        return result


def addFiles(fileList, path=""):
    if "." in fileList:
        srcDir = os.path.join(source.dirPath, path)
        destDir = os.path.join(dest.dirPath, path)
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
            addFiles(fileList[name], os.path.join(path, name))

def removeFiles(fileList, path=""):
    destDir = os.path.join(dest.dirPath, path)
    if "." in fileList:
        for name, ext in fileList["."].items():
            if dry_run:
                print("REMOVE:", os.path.join(path, name + ext))
            else:
                os.remove(os.path.join(destDir, name + ext))
    for name in fileList:
        if name != ".":
            removeFiles(fileList[name], os.path.join(path, name))
    if path!= "" and not os.listdir(destDir):
        if dry_run:
            print("RMDIR:", destDir)
        else:
            os.rmdir(destDir)


def printj(j):
    print(json.dumps(j, sort_keys=True, indent=4, separators=(',', ': ')))
    

def check_negative(value):
    ivalue = int(value)
    if ivalue <= 0:
         raise argparse.ArgumentTypeError("%s is an invalid int value" % value)
    return ivalue
    
################################################

parser = argparse.ArgumentParser(description='One-way file-based syncronization with per-file selection & custom commands')
parser.add_argument('jsonfile', type=argparse.FileType('r'),
                   help='path to a JSON file containing a sync configuration')
parser.add_argument('--print',
                   choices=['all', 'config', 'source', 'dest', 'added', 'removed', 'missing', 'toTransfer', 'toRemove'],
                   help='prints JSON data but does not perform sync')
parser.add_argument('-d', '--dry', action='store_true',
                   help='simulate the sync but do not perform')
parser.add_argument('-c', '--concurrent', type=check_negative, default=multiprocessing.cpu_count(),
                   help='maximum number of concurrent transcoding processes; defaults to number of cores')
args = parser.parse_args()


with args.jsonfile as data_file:
    syncConfig = json.load(data_file)

config = DirListing(syncConfig['sync'])
source = DirListing(syncConfig['sourceDir'])
dest = DirListing(syncConfig['destDir'])

added = source.minus(dest)
removed = dest.minus(source)

missing = config.minus(source)
toTransfer = config.intersection(added)
toRemove = dest.minus(config)



#print(toTransfer)
#print("********************************")
#print(toRemove)

print(args.print)

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

processes = set()
max_processes = args.concurrent
dry_run = args.dry

exit(0)

addFiles(toTransfer.fileList)
removeFiles(toRemove.fileList)

for p in processes:
    if p.poll() is None:
        p.wait()

