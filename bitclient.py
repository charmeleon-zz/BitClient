#!/usr/bin/sys python3
# A basic cli BitTorrent Client -- bitclient.py
# Python's standard library
from sys import argv
from hashlib import sha1 as sha
from urllib import parse
import socket, os, hashlib
# BitClient modules
#from connection import torrent, filequeue
from src.connection import filequeue, torrent

def run():
  '''
  Download all files under /torrents folder
  '''
  q_obj = filequeue.FileQueue()
  queue = q_obj.getFileQueue()
  if queue is None or len(queue)==0:
    print("No files in queue")
  else:
    torrentList = []
    for filename in queue:
      print("Tracking: ",filename)
      torrentList.append(torrent.Torrent(filename))
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
