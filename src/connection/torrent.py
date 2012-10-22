#!/usr/bin/dev python
# BitClient -- torrent.py
# standard lib
import os, sys
# BitClient lib
#import peer
from src.encoding import bdecoder

class Torrent(object):
  '''
  The Torrent class is a wrapper for a .torrent file and provides the
  functionality needed by the client to interact with them
  '''

  def __init__(self,filename):
    '''Initialize a torrent object, given the filename
    A torrent object should consist, at minimum, of the following:
    * a .torrent file containing the metadata for this file
    * a file identical in name to the .torrent file but replaces the ending
      .torrent with .part, which will keep track of our progress
    * methods: totalSize(), totalDownloaded()
    '''
    # localize folder where torrents are stored
    self.filename = filename
    # if it has finished downloading, then there won't be a part file!
    self.partfilename = self._getPartFileName()
    self.partfile = self._getPartFile("r")
    #TODO: realistically, on startup we should recognize whether a file has
    #finished downloading, and seed if it has
    self.metainfo_data = self._readTorrentFile()
    pass

  def _readTorrentFile(self):
    '''Attempt to read a torrent file and return its content.
    This function works under the assumption that a .torrent file is binary
    Returns a dictionary
    '''
    try:
      with open(self.filename, mode='rb') as localized_file:
        return encoding.bdecoder.decode(localized_file.read().decode("latin1"))
    except IOError as e:
      print("File ",self.filename," could not be found")
      sys.exit(2)

  def _getPartFileName(self):
    '''Return the name of the partfile for this torrent'''
    #TODO: Should also return a .part file if the encoding matches .torrent
    #TODO: Set a flag indicating whether file is complete or not?
    if self.filename.endswith(".torrent"):
      tmp = self.filename[:-len(".torrent")]
      if os.path.exists(tmp):
        return tmp
      else:
        return tmp+".part"
    else:
      raise TypeError("torrent file must end in .torrent, given %s"%filename)

  def _getPartFile(self,m):
    '''Return file object corresponding to the "partfile"
    If it doesn't exist, create it
    '''
    if os.path.exists(self.partfilename):
      return open(self.partfilename,mode=m).read()
    else:
      open(self.partfilename,mode="w").close()
      return self._getPartFile(m)

  def _getTorrentFile(self):
    '''Return the file object corresponding to the .torrent file'''
    pass

  def totalDownloaded(self):
    '''Return the total downloaded, which is the size of the part file'''
    pass

  def totalSize(self):
    '''Return the total size of the file'''
    pass
  
  def getTrackers(self):
    for t in self.metainfo_data['announce']:
      print("Announce list: ",t)
