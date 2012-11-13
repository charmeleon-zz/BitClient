#!/usr/bin/sys python3
# A basic cli BitTorrent Client -- bitclient.py
# Copyright Erick Rivas until the heat death of the universe
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
    torrentQueue = {} # A list of torrent objects
    # TODO: A timer for when to refresh the queue?
    print("Appending .torrent files to queue")
    for filename in queue:
      torrentQueue[filename]=torrent.Torrent(filename)
    print("Torrenting")
    for name,tor in torrentQueue.items():
      try:
        if tor.has_good_status():
          tor.torrent()
      except KeyboardInterrupt:
        print("Stopping BitClient")
#      tor.query_trackers()
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
