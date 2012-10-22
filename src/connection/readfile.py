#!/usr/bin/dev python3
# bitclient -- readfile.py

import sys,os,locale
from encoding import bdecoder

def readTorrentFile(filename):
  '''
  Attempt to read a torrent file and return its content.
  This function works under the assumption that a .torrent file is binary,
  though it returns a unicode string

  '''
  localized_string = os.curdir+os.sep+filename
  try:
    with open(filename, mode='rb') as localized_file:
      return bdecoder.decode(localized_file.read().decode("latin1"))
  except IOError as e:
    print("File ",filename," could not be found")

if __name__=="__main__":
  the_file = "../torrents/[isoHunt] 2588985.torrent" 
  print(readTorrentFile(the_file))

