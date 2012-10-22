#!/usr/bin/sys python3
# A basic cli BitTorrent Client -- bitclient.py
# Python's standard library
from sys import argv
from hashlib import sha1 as sha
from urllib import parse
import socket, os, hashlib
# BitClient modules
#from connection import torrent, filequeue
from connection import filequeue
from connection import torrent

def run():
  '''
  Download all files under /torrents folder
  '''
  q_obj = filequeue.FileQueue()
  queue = q_obj.getFileQueue()
  if len(queue)==0 or queue is None:
    print("No files in queue")
  else:
    # key : Connection<class>
    # Need at minimum one thread per file?
    torrentList = []
    for filename in queue:
      print("Tracking: ",filename)
      torrentList.append(torrent.Torrent(filename))
#      meta_info = readfile.readTorrentFile(queue[filename])
#      querytracker.query_tracker(meta_info)
# while True:
# create socket
# connect to tracker server    

if __name__=="__main__":
  '''
  usage: bitclient.py [<filename>] [<port>]

  '''
  try:
    filename = argv[1]
  except IndexError:
    print("",end="")
  run()
