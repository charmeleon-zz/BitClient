#!/usr/bin/dev python3
# BitClient -- filequeue.py
import os, glob

filequeue_name = "filequeue.txt"
filequeue_folder = "torrents"
full_filequeue_path = os.path.split(os.path.abspath(__file__))[0]+os.sep+os.pardir+os.sep+filequeue_folder+os.sep
full_filequeue_name = full_filequeue_path+filequeue_name

class FileQueue(object):
  def __init__(self):
    pass

  def updateFileQueue(self):
    '''Check and update the integrity of the existing queue.
    The queue file will be re-written every time this function is called
    in accordance to any files which are found (or are missing) from the 'contents' folder
    '''
    #torrent_files = {} # empty queue
    torrent_files = []
    try:
      for v in glob.glob(full_filequeue_path+"*.torrent"):
        torrent_files.append(v)
#        torrent_files[os.path.basename(v)]=v
#        print(v)
    except FileNotFoundError:
      print("No files found",end="") # ignore
    if len(torrent_files)>0:
      return torrent_files
    else:
      return None
  
  def getFileQueue(self):
    '''Return a list object naming all files currently in the queue'''
    queue = self.updateFileQueue()
    return queue

  if __name__=="__main__":
    print("Testing queue thingee")
    self.updateFileQueue()
