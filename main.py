# encoding: utf-8
import json, os
from tinytag import TinyTag
import subprocess
import shutil


class DirListing:
    def __str__(self):
        return json.dumps(self.fileList, sort_keys=True, indent=4, separators=(',', ': '))
    
    def __init__(self, dirPath):
        self.dirPath = dirPath
        self.fileList = {}
        self.walkDir(self.dirPath, self.fileList)

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
        return self._min(self.fileList, other.fileList)
    
    def altered(self, other):
        return self._alt(self.fileList, other.fileList)
    
    def _alt(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                for basename in myList[key]:
                    if key in otherList and basename in otherList[key] and myList[key][basename] != otherList[key][basename]:
                        result.setdefault(key,{})[basename] = myList[key][basename]
            elif isinstance(myList[key], dict):
                if key in otherList:
                    result[key] = self._alt(myList[key], otherList[key])
        return result
    
    def _min(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                for basename in myList[key]:
                    if key not in otherList or basename not in otherList[key]:
                        result.setdefault(key,{})[basename] = myList[key][basename]
            elif isinstance(myList[key], dict):
                if key in otherList:
                    result[key] = self._min(myList[key], otherList[key])
                else:
                    result[key] = myList[key]
        return result


def addFiles(fileList, path=""):
    if "." in fileList:
        srcDir = os.path.join(source.dirPath, path)
        destDir = os.path.join(dest.dirPath, path)
        if not os.path.isdir(destDir):
            os.makedirs(destDir)
        for name, ext in fileList["."].items():
            print(path, name, ext)
            if ext.lower() != ".flac":
                shutil.copy2(
                    os.path.join(srcDir, name + ext),
                    os.path.join(destDir, name + ext))
                continue
            cmd = ['ffmpeg',
                   '-i', os.path.join(srcDir, name + ext),
                   '-q:a', '2',
                   '-map_metadata', '0',
                   '-id3v2_version', '3',
                   os.path.join(destDir, name + ".mp3")]
            print(" ".join(cmd))
            processes.add(subprocess.Popen(cmd))
            if len(processes) >= max_processes:
                os.wait()
                processes.difference_update([p for p in processes if p.poll() is not None])
                
            ## ffmpeg -i "${srcDir}/${name}${ext}" -qscale:a 0 "${destDir}/${name}.mp3"
    for name in fileList:
        if name == ".":
            continue
        addFiles(fileList[name], os.path.join(path, name))


def printj(j):
    print(json.dumps(j, sort_keys=True, indent=4, separators=(',', ': ')))
    
################################################

with open('/run/media/notbryant/5688b375-0c10-45d5-9e82-52acb0060cf6/Media/sync.json') as data_file:
    syncConfig = json.load(data_file)


source = DirListing(syncConfig['sourceDir'])
dest = DirListing(syncConfig['destDir'])

added = source.minus(dest)
removed = dest.minus(source)
#altered = source.altered(dest)

processes = set()
max_processes = 10
    
addFiles(added)
for p in processes:
    if p.poll() is None:
        p.wait()



