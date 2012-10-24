#!/usr/bin/dev python
# BitClient -- torrent.py
import os, sys
from urllib import parse
from hashlib import sha1 as sha
# BitClient lib
from src.connection.tracker import Tracker
from src.encoding import bdecoder, bencoder
from src.utils import strmanip

MAX_PEERS = 35
COMPACT = 1

class Torrent(object):
  '''The Torrent class is a wrapper for a .torrent file and provides the
  functionality needed by the client to interact with them'''

  def __init__(self,filename):
    '''Initialize a torrent object, given the filename'''
    self.filename = filename
    self.partfilename = self._get_part_file_name()
    self.partfile = self._get_part_file("r")
    #TODO: realistically, on startup we should recognize whether a file has
    #finished downloading, and seed if it has
    self.metainfo_data = self._read_torrent_file()
    self.info = self.metainfo_data['info']
    self.trackers = {};self._parse_trackers()
    self.num_peers = 0

  def _read_torrent_file(self):
    '''Attempt to read a torrent file and return its content.
    This function works under the assumption that a .torrent file is binary
    Returns a dictionary'''
    try:
      with open(self.filename, mode='rb') as localized_file:
        return bdecoder.decode(localized_file.read().decode("latin1"))
    except IOError as e:
      print("File ",self.filename," could not be found")
      sys.exit(2)

  def _get_part_file_name(self):
    '''Return the name of the partfile for this torrent'''
    # TODO: how should this work with multi-file torrents?
    if self.filename.endswith(".torrent"):
      tmp = self.filename[:-len(".torrent")]
      if os.path.exists(tmp):
        return tmp
      else:
        return tmp+".part"
    else:
      raise TypeError("torrent file must end in .torrent, given %s"%filename)

  def _get_part_file(self,m):
    '''Return file object corresponding to the "partfile"
    If it doesn't exist, create it'''
    if os.path.exists(self.partfilename):
      return open(self.partfilename,mode=m).read()
    else:
      open(self.partfilename,mode="w").close()
      return self._getPartFile(m)

  def get_downloaded(self):
    '''Return the total downloaded, which is the size of the part file'''
    return os.path.getsize(self.partfilename)

  def total_size(self):
    '''Return the total size of the file'''
    try:
      return self.info['length']
    except KeyError: # multi-file
      value = 0
      for f in self.info['files']:
        value+=f['length']
      return value

  def getTrackers(self):
    '''Return the list of HTTP trackers'''
    print("Updating trackers for ",filename)
    self._parse_trackers() 
    return self.trackers

  def _parse_trackers(self):
    '''Read the metainfo for the latest tracker info'''
    if 'announce-list' in self.metainfo_data:
      for t in self.metainfo_data['announce-list']: # Addendum to the specification
        if isinstance(t,list):
          for ele in t:
            self._add_tracker(ele)
        else:
          self._add_tracker(t)
    else:
      if self.metainfo_data['announce'] not in self.trackers:
        self._add_tracker(self.metainfo_data['announce'])

  def _add_tracker(self,tracker_name):
    '''Update our tracker list (for the time being, restricted to http trackers)'''
    if tracker_name not in self.trackers and tracker_name.startswith('http://'):
      self.trackers[tracker_name] = Tracker(tracker_name)

  def get_announce_string(self):
    # create url string
    params = {
      "info_hash":parse.quote(sha(bencoder.encode(self.metainfo_data['info']).encode("latin-1")).digest()), # digest vs hexdigest
      "peer_id":parse.quote(('-BCSS-'+strmanip.string_generator(20))[:20]),
      "port":51413,
      "uploaded":0,   #TODO: uploaded = ? @note: can only keep track for sesh
      "downloaded":self.get_downloaded(),
      "left":self._get_left(),
      "event":"started",
      "numwant":MAX_PEERS-self.num_peers,
      "compact":COMPACT
    }
    url='?'
    # order doesn't matter, which is good since these will come out
    # in no particular order (thanks Allison (aka akaptur)!)
    for key, value in params.items():
      url+='%s=%s&'%(key,value) #TODO: @SEE parse.urlencode
    url = url[:-1] # chop off the last member (ouch)
    return url

  def query_trackers(self):
    '''Send an announcement to the tracker, but only if we're under MAX_PEERS'''
    if self.num_peers<MAX_PEERS:
      for t in self.trackers:
        self.trackers[t].announce(self.get_announce_string())

  def _get_left(self):
    return self.total_size()-self.get_downloaded()

  def add_peer(self):
    pass

  def remove_peer(self):
    pass

