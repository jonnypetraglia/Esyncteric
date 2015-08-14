# Esyncteric

Esyncteric is a file-based one-way selective sync tool that allows customizable intermediary transformation.
To put it simply, I built it to allow me to select piece-by-piece what music files I want on my MP3 players and then encode them from FLAC to MP3.


It's not limited to music though; it can be used with anything that needs pre-processing or just if you want fine-tuned selective sync.

  * file-based: It preserves folder structure in the destination but item inclusion is purely files. Not folders or wildcards.
  * one-way: It takes the files you selected, transforms them (if you set it to), and places them in the destination. That simple.
  * selective: You literally select every specific file you want synced.
  * sync: It copies the files you specify and cleans the destination of any you don't.
  * customizable intermediary transformation: Big words that mean "sync this file by running X program". Example: usiong ffmpeg to encode FLAC to MP3.



To be clear: Esyncteric's goal is not to be really good at syncronization, it's meant to be a base that allows you to you define the complexity of the syncing you need. It doesn't even compare destination files to their source counterparts for time or content difference. All it does is check if it is there.


It's "Esyncteric" because the usage is so bloody esoteric I don't even know if anyone besides me would want to use it.

## Dependencies ##

Esyncteric was written with Python 3.4.

If you only are using the CLI, that's all you need; to my knowledge all modules used are shipped with every Python install.

If you are going to be using the GUI, you need to install [PyQt4](https://wiki.python.org/moin/PyQt4) as well as [Qt](http://qt.nokia.com).

Icon is courtesy of OpenClipartVectors on [pixabay](https://pixabay.com/en/esoteric-metaphysical-occult-pagan-154605/) and is licensed under the CC0 Public Domain. It was the coolest thing that came up when I google imaged "esoteric".


## Usage ##

Esyncteric is usable via either CLI or GUI.

Here are the flags you can use:

  * `-h`, `--help` = show help message
  * `--print=${what}` = do not perform the sync, just print out the JSON data specified
  * `-d`, `--dry` = simulate the sync but do not perform it
  * `-g`, `--gui` = show the GUI instead of performing the sync
  * `-c N`, `--concurrent N` = the number of processes to create while syncing; defaults to the # of cores


Configuration on a per-sync basis is stored in JSON files like so:

(TODO: Maybe support YAML as well?)


```
{
  "sourceDir": "/media/Music",
  "destDir": "/mnt/mp3player",
  "filetypes": {
    ".flac": {
        "cmd": ["ffmpeg", "-i", null, "-q:a", "2", "-map_metadata", "0", "-id3v2_version", "3", null],
        "to": ".mp3"
    },
  },
  "sync": {
    "folder": {
        "subfolder": {
            ".": ["artwork.jpg", "song.flac"]
        },
    }
  }
}
```

The JSON structure is very simple: nested JSON objects refer to the path (`folder/subfolder`) and `.` (the symbol for 'current directory') refers to an array of the files you want included in that directory. Therefore, this would sync the files `/media/Music/folder/subfolder/artwork.jpg` and `/media/Music/folder/subfolder/song.flac` to `/mnt/mp3player/folder/subfolder/artwork.jpg` and `/mnt/mp3player/folder/subfolder/song.mp3`. Notice how the FLAC has been encoded to MP3 via the ffmpeg command given in 'filetypes' whereas '.jpg' has no entry so it is simply copied.

The placeholders for 'source file' and 'destination file' are `{0}` and `{1}` respectively.



You can write the JSON by hand, generate it via a script, or use the GUI. The GUI lets you select what files you want sync via a tree. You can then run it from the GUI or CLI.