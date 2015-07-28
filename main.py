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
    
    def diff(self, other):
        return self._cmpPart(self.fileList, other.fileList)
    
    def _cmpPart(self, myList, otherList):
        result = {}
        for key, myVal in myList.items():
            otherVal = otherList[key] if key in otherList else {}
            if key in myList and key not in otherList:
                result[key] = "+"
            elif key in otherList and key not in myList:
                result[key] = "-"
            elif type(myList[key]) != type(otherList[key]):
                result[key] = "~"
            elif key == ".":
                files = result #.setdefault('.',{})
                for basename in myVal:
                    if basename not in otherVal:
                        files[basename] = "+"
                    elif myVal[basename] != otherVal[basename]:
                        files[basename] = "~"
                for basename in otherVal:
                    if basename not in files:
                        files[basename] = "-"
            elif isinstance(myVal, dict):
                print("Parting", key)
                result[key] = self._cmpPart(myVal, otherVal)
        for key, otherVal in otherList.items():
            if key not in myList:
                if key == ".":
                    for basename in otherVal:
                        result[basename] = "-"
                else:
                    result[key] = "-"
                #result[key] = self._cmpDeleted(otherVal)
        return result
    
    def _cmpDeleted(self, otherList):
        result = {}
        for key in otherList:
            if isinstance(otherList[key], dict):
                result[key] = self._cmpDeleted(otherList[key])
            else:
                result[key] = "-"
        return result




testA = DirListing(os.path.join(MEDIA_DIR, "Music/Switchfoot"))
testB = DirListing("/mnt/Tera/Media/Music/Switchfoot")
#print(testA)
printj(testA.diff(testB))