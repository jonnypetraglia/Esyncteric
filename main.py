# encoding: utf-8
import json, os
from tinytag import TinyTag
import pprint

pp = pprint.PrettyPrinter(indent=4)

MEDIA_DIR = "/run/media/notbryant/5688b375-0c10-45d5-9e82-52acb0060cf6/Media"
os.chdir(MEDIA_DIR)

TEST_DIR = 'Music/Owl City/Ocean Eyes'
TEST_FILE = '01 - Cave In.flac'

tag = TinyTag.get(os.path.join(MEDIA_DIR, TEST_DIR, TEST_FILE))
print('This track is by %s.' % tag.artist)
print('It is %f seconds long.' % tag.duration)




#with open('sync.json') as data_file:    
#    syncList = json.load(data_file)

def printj(j):
    print(json.dumps(j, sort_keys=True, indent=4, separators=(',', ': ')))


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
    
    def _min(self, myList, otherList):
        result = {}
        for key in myList:
            if key == ".":
                result[key] = {}
                for basename in myList[key]:
                    if key not in otherList or basename not in otherList[key] or myList[key][basename] != otherList[key][basename]:
                        result[key][basename] = myList[key][basename]
            elif key not in otherList:
                if isinstance(myList[key], dict):
                    result[key] = self._min(myList[key], otherList[key] if key in otherList else {})
                else:
                    result[key] = myList[key]
        return result
        result = {}
        for key in otherList:
            if isinstance(otherList[key], dict):
                result[key] = self._cmpDeleted(otherList[key])
            else:
                result[key] = "-"
        return result




testA = DirListing(os.path.join(MEDIA_DIR, "Music/Switchfoot"))
testB = DirListing("/mnt/Tera/Media/Music/Switchfoot")
#testB = DirListing(os.path.join(MEDIA_DIR, "Music/Owl City/Ocean Eyes"))
#print(testA)
#printj(testA.diff(testB))
printj(testA.minus(testB))
printj(testB.minus(testA))