#!/usr/bin/dev python
# BitClient -- torrent.py
import os, sys, struct, time
from math import ceil
from urllib import parse
from hashlib import sha1 as sha
# BitClient lib
from src.connection.tracker import Tracker
from src.connection.peer import Peer
from src.encoding import bdecoder, bencoder
from src.utils import strmanip
from src.io.file import File
import src.io.bitlog as bitlog

# TODO: MAX_PEERS = 35. 5 is good for debugging
MAX_PEERS = 15
COMPACT = 1

class Torrent(object):
  '''The Torrent class is a wrapper for a .torrent file and provides the
  functionality needed by the client to interact with them'''

  def __init__(self,filename):
    '''Initialize a torrent object, given the filename'''
    self.good_status = True
    self.log = bitlog.log()
    self.filename = filename
    self.filepath = os.path.dirname(self.filename)
    self.metainfo_data = self.read_torrent_file(filename)
    self.info = self.metainfo_data['info']
    self.piece_size = self.info['piece length']
    self.torrentname = ""
    self.files = []
    try:
      # TODO: md5sum is a nice to have, but passing None arg is a PITA
      self.partfiledata = self.parse_partfile_data(self.filepath,
        self.info['name'] if 'name' in self.info else os.path.basename(self.filename),
        self.info['length'] if 'length' in self.info else self.info['files'])
    except KeyError:
      self.good_status = False
      print("MalformedTorrent: The length key for torrent %s was not given, removing from queue" % self.filename)
    # necessary so that get_downloaded() functions properly
    if isinstance(self.partfiledata, list):
      for filedata in self.partfiledata:
        self.get_partfile(filedata['fullpath'], "rb")
    else:
      self.get_partfile(self.partfiledata['fullpath'], "rb")
    self.peerid = self.get_peer_id()
    #TODO: realistically, on startup we should recognize whether files have
    # finished downloading
    self.info_hash = self.get_info_hash(self.info)
    self.trackers = {};self.parse_trackers(self.metainfo_data)
    self.pieces = []; self.map_pieces(self.info['pieces'])
    self.peers = {} # Peer objects
    self.backup_peers = [] # list of {ip:,port:} dicts for backup

    self.uploaded = 0
    self.finished = False

  def torrent(self):
    stop = False
    while not stop:
      self.update_peers(self.query_trackers())
      for i in self.peers:
        if self.peers[i].can_request():
          for piece in [m for m in self.pieces if not m['have']]:
            if not piece['requested'] and not piece['have']:
              if self.peers[i].can_request() and self.peers[i].has_piece(piece['index']):
                print("Requesting piece %s announced" % piece['index'])
                self.peers[i].request_piece(piece['index'], self.piece_size)
                piece['requested'] = True
              elif self.peers[i].can_request():
                print("Requesting piece %s unnanounced" % piece['index'])
                self.peers[i].request_piece(piece['index'], self.piece_size)
                piece['requested'] = True
#                print("%s pieces left" % len([z for z in self.pieces if not z['have']]))
#                print("%s pieces left" % len([z for z in self.pieces if not z['have']]))
              else:
                print("%s pieces left" % len([z for z in self.pieces if not z['have']]))
        if self.peers[i].has_complete_pieces():
          for j in self.peers[i].complete_pieces():
            [k for k in self.pieces if k['index'] == j['index']][0]['file'].insert_at(j['index']*self.piece_size, j['data'])
            [k for k in self.pieces if k['index'] == j['index']][0]['have'] = True
#            print("Piece %s completed")
            #filewrapper.write(seek) 
      if not [m for m in self.pieces if not m['have']]:
        self.log.info("Download completed")
        break
      Peer.loop()
    print("Exiting BitClient")
    sys.exit(1)

  def has_good_status(self):
    return self.good_status

  def read_torrent_file(self, filename):
    '''Attempt to read a torrent file and return its content.
i    Returns a dictionary'''
    try:
      with open(filename, mode='rb') as localized_file:
        return bdecoder.decode(localized_file.read().decode("latin1"))
    except IOError as e:
      print("File ",filename," could not be found")
      sys.exit(2)
      # how to remove from queue?
      # bump the error upwards and catch in client, remove from queue

  def parse_partfile_data(self, path, name, args):
    '''Return the name of the partfile for this torrent'''
    self.total_size = 0

    if isinstance(args, int):
      self.total_size = args
    elif isinstance(args, list):
      self.torrentname = []
      for arg in args:
        self.torrentname.append(arg)
        self.total_size += arg['length']
    else:
      print("Received unrecognized args:\n\t%r\n\ttype: %s"%(args,type(args)))
      sys.exit(2)

    if isinstance(args, int):
      return {"name":name, "fullpath": self.pathify_file(path, name),"length": args, 
        "completed": self.completed_status(self.pathify_file(path, name), args), "lower": 0, "file": File(self.pathify_file(path, name))}
    elif isinstance(args, list):
      return [{"name":f['path'], "fullpath": self.pathify_file(path, f['path']),
        "length": f['length'], 
        "completed": self.completed_status(self.pathify_file(path, f['path']), f['length']),
        "lowest": int(self.piece_size/f['length']), "file": File(self.pathify_file(path, name))} for f in args]
    else:
      print("arg of type: %s"%type(args))
      raise TypeError("torrent file must end in .torrent, given %s which ends with %s"
        %(self.filename, os.path.split(self.filename)[-1]))

  def pathify_file(self, path, filename):
    '''Locate a part file in the given path. If an existing file is not found
    return a file with a .part extension'''
    if isinstance(filename, list) and len(filename)==1:
      filename = filename[0]
    elif isinstance(filename, str):
      pass
    else:
      print("An error occurred when parsing the files")
      print(type(filename))
      raise TypeError
      sys.exit(1)

    if os.path.exists(os.path.join(path, filename)):
      return os.path.join(path, filename)
    else:
      return os.path.join(path, filename + ".part")
    

  def get_partfile(self, filename, m):
    '''Return file object corresponding to the "partfile"
    If it doesn't exist, create it'''
    
    if os.path.exists(filename):
      return open(filename, mode=m).read()
    else:
      open(filename, mode="w").close()
      return self.get_partfile(filename, m)

  def get_downloaded(self, name = ""):
    '''Return the total downloaded, which is the size of the part file'''
    if len(name)==0:
      name = self.partfiledata

    if isinstance(name, str):
      return os.path.getsize(name) if os.path.exists(name) else 0
    elif isinstance(name, dict):
      return self.get_downloaded(name['fullpath'])
    else:
      return sum([os.path.getsize(f['fullpath']) if os.path.exists(f['fullpath']) else 0 for f in name])

  def parse_trackers(self, metainfo_data):
    '''Populate the list of http trackers'''
    if 'announce-list' in metainfo_data:
      for t in metainfo_data['announce-list']: # Addendum to the specification
        if isinstance(t,list):
          for ele in t:
            self._add_tracker(ele)
        else:
          self._add_tracker(t)
    else:
      self._add_tracker(metainfo_data['announce'])

  def _add_tracker(self, tracker_name):
    '''Update our tracker list (for the time being, restricted to http trackers)'''
    if tracker_name not in self.trackers and tracker_name.startswith('http://'):
      self.trackers[tracker_name] = Tracker(tracker_name)

  def get_announce_string(self):
    '''Returns announce string in accordance to BitTorrent's HTTP specification'''
    # create url string
    params = {
      "info_hash":parse.quote(self.info_hash), # digest vs hexdigest
      "peer_id":parse.quote(self.peerid), # peer_id varies
      "port":51413,
      "uploaded":0,   #TODO: uploaded = ? @note: can only keep track for sesh
      "downloaded":self.get_downloaded(),
      "left":self._get_left(),
      "event":"started",
      "compact":COMPACT
#      "numwant":MAX_PEERS - len(self.peers),
    }
    # @NOTE: urlencode uses quote_plus, which doesn't work here
#    return "?"+parse.urlencode(params)
    url = "?"
    for key, value in params.items():
      url+='%s=%s&'%(key,value)
    return url[:-1]

  # TODO: Make property -- info_hash is constant
  def get_info_hash(self,info_key):
    '''Returns a binary string of a sha1 hash'''
    return sha(bencoder.encode(info_key).encode("latin-1")).digest()
  
  # TODO: Property
  def get_peer_id(self):
    '''Return a pseudo-random peer id'''
    return parse.quote(('-BCSS-'+strmanip.string_generator(20))[:20])

  def query_trackers(self):
    '''Send an announcement to the tracker and get an updated peer list'''
    addtl_peers = []
    for t in self.trackers:
      if self.trackers[t].can_reannounce() and self.trackers[t].is_available():
        l = self.trackers[t].announce(self.get_announce_string())
        if l is None or len(l) == 0:
          pass
        else:
          addtl_peers.extend(l)
      else:
        continue
    return addtl_peers

  def _get_left(self):
    '''How much is left to download, in bytes'''
    return self.total_size-self.get_downloaded()

  def update_peers(self, peer_info_list):
    '''Given a list of dictionaries, update the list of peers for this torrent'''
    if peer_info_list is not None:
      self.backup_peers.extend(peer_info_list)
    for peer_info in self.backup_peers:
      if self.add_peer(peer_info):
        del self.backup_peers[self.backup_peers.index(peer_info)]
    Peer.loop()
    # Check for anything to remove
    to_delete = []
    for ip in self.peers:
      if self.peers[ip].can_remove():
        to_delete.append(ip)
    for i in to_delete:
      self.log.debug("Dropping peer %s" % i)
      self.remove_peer(i)

  def add_peer(self, peer_info):
    '''Add to our list of peers if it is not already there'''
    if peer_info['ip'] not in self.peers and len(self.peers) < MAX_PEERS:
      p = Peer(peer_info, {"info_hash": self.info_hash, "handshake": self.get_handshake()})
      self.peers[peer_info['ip']] = p
      return True
    else:
      pass

  def remove_peer(self,peer_ip):
    '''Remove from our list of peers, if it exists'''
    if peer_ip in self.peers:
      unfinished = self.peers[peer_ip].unfinished_pieces()
      if unfinished:
        for pc in unfinished:
          for piece in [i for i in self.pieces if i['index'] == pc['index']]:
            piece['requested'] = False
      del self.peers[peer_ip]
    else:
      pass

  def get_num_peers(self):
    '''Return the number of currently active peers'''
    return len(self.peers)

  def map_pieces(self, current_map):
    '''Given the pieces string, map them 20-byte sized chunks'''
    piece_length = 20 # the hash is 20 bytes long
    piece_num = 0
    self.pieces = [{"hash":current_map[i:i+piece_length],
      "have": False,  "requested": False, 
      "priority": 0,  "written": False,
      "attempts": 0,  "index": int(i/piece_length),
      "file": self.partfiledata['file'] if isinstance(self.partfiledata, dict)
        else [f for f in self.partfiledata if f['lowest'] <= int(i/piece_length)][0]['file']}
       for i in range(0,len(current_map),piece_length)]
#   piece_map: hash | have | requested | priority | attempts  | index | file
    # TODO: compare hash of file extract vs file

  def get_file_in_range(self, size):
    # given a size, figure out which filename it corresponds to
    totallen = 0
    lastname = ""
    while totallen < size:
      for f in self.partfiledata:
        totallen += f['length']

  def get_handshake(self):
    '''A method for a handshake. Since peer_id constantly changes, it's best
    not to store it'''
    pstr = bytes("BitTorrent protocol", "UTF-8")
    pstrlen = struct.pack("!b", len(pstr))
    reserved = struct.pack("!II", 0, 0)
    rest = self.info_hash + bytes(self.peerid, "UTF-8")
    handshake = bytes(pstrlen + pstr + reserved + rest)
    return handshake

  @staticmethod
  def loop():
    Peer.loop()

  def completed_status(self, filepath, length):
    '''Given a full filepath and file length, check if file has finished
    downloading'''
    return length == self.get_downloaded(filepath)

