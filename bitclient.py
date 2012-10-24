#!/usr/bin/sys python3
# A basic cli BitTorrent Client -- bitclient.py
# Python's standard library
from sys import argv
from hashlib import sha1 as sha
from urllib import parse
import socket, os, hashlib
# BitClient modules
#from connection import torrent, filequeue
from src.io import filequeue
from src.connection import torrent

def run():
  '''
  Download all files under /torrents folder
  '''
  q_obj = filequeue.FileQueue()
  queue = q_obj.getFileQueue()
  if queue is None or len(queue)==0:
    print("No files in queue")
  else:
    torrentList = [] # A list of torrent objects
    # TODO: A timer for when to refresh the queue
    print("Appending .torrent files to queue")
    print("Files in queue: ")
    for filename in queue:
      print("\t%s"%filename)
      torrentList.append(torrent.Torrent(filename)) # now connect to the trackers
    print()
    for tor in torrentList:
#      help(tor)
      tor.query_trackers()
'''    shutdown = False
    while not shutdown:
      try:
      except KeyboardInterrupt:
        print("Stopping BitClient")
        shutdown=True
'''      
#    while True:     
#      print("Doing stuff...")
#sys.stdout.write /r (beginning 

if __name__=="__main__":
  '''
  usage: bitclient.py [<filename>] [<port>]

  '''
  try:
    filename = argv[1]
  except IndexError:
    print("",end="")
  run()
