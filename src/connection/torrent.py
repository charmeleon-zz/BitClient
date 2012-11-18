#!/usr/bin/dev python
# BitClient -- torrent.py
import os, sys, struct, time, curses
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
    self.torrentname = self.filename[len(self.filepath):]
    self.total_size = 0
    self.left = 0
    self.metainfo_data = self.read_torrent_file(filename)
#    if 'encoding' in self.metainfo_data:
#      self.log.warn("Attention: Torrent has specified encoding")
#      sys.exit(0)
    self.info = self.metainfo_data['info']
    self.piece_size = self.info['piece length']
    try:
      self.partfiledata = self.parse_partfile_data(self.filepath,
        self.info['name'] if 'name' in self.info else os.path.basename(self.filename),
        self.info['length'] if 'length' in self.info else self.info['files'])
    except KeyError:
      self.good_status = False
      print("MalformedTorrent: The length key for torrent %s was not given, removing from queue" % self.filename)
    self.peerid = self.get_peer_id()
    #TODO: realistically, on startup we should recognize whether files have
    # finished downloading
    self.info_hash = self.get_info_hash(self.info)
    self.trackers = {};self.parse_trackers(self.metainfo_data)
    self.pieces = []; self.map_pieces(self.info['pieces'])
    self.peers = [] # Peer objects
    self.backup_peers = [] # list of {ip:,port:} dicts for backup
    self.uploaded = 0
    self.finished = False
    self.downloaded = 0
    self.pieces_left = 0
    self.runtime = time.time()
    self.shutdown = False

  def torrent(self):
    while not self.shutdown:
      self.pieces_left = len([m for m in self.pieces if not m['have']])
      self.update_peers(self.query_trackers())
      # Check whether we still have pieces left to send
      if not self.pieces_left:
        self.log.debug("Download completed, cleaning up...")
        sys.exit(0)
      for peer_index, peer in enumerate(self.peers):
        # Process requests
        # TODO: Work on strategy for pieces that need be requested multiple times
        if peer.can_request():
          for piece_index, piece in [(n, m) for (n, m) in enumerate(self.pieces) if not m['have']]:
            if peer.can_request() and peer.has_piece(piece_index) and not piece['requested']:
              peer.request_piece(piece_index, piece.get('size', self.piece_size))
              piece['requested'] = True
              piece['attempts'] += 1
        # Process completed pieces
        if peer.has_complete_pieces():
          sys.stdout.write("\r%s/%s ({0:.2f}%%) pieces downloaded. Rate: %s/s".
            format((len(self.pieces) - self.pieces_left)/len(self.pieces)*100) %
            (len(self.pieces) - self.pieces_left, len(self.pieces), 
            strmanip.parse_filesize(self.downloaded/(time.time() - self.runtime), 1000)))
          sys.stdout.flush()
          for piece in peer.complete_pieces():
            if self.check_piece(piece['index'], piece['data']):
              self.write_piece(piece['index'], piece['data'])
            else:
              self.log.warn("Piece hash FAILED. Index: %s" % piece['index'])
              self.pieces[piece['index']]['requested'] = False
              sys.exit(0)
      Peer.loop()
    print("Exiting BitClient")
    sys.exit(1)

  def check_piece(self, piece_index, data):
    '''Hash-check a given piece'''
    return sha(data).digest() == self.pieces[piece_index]['hash']

  def write_piece(self, piece_index, data):
    '''Given a piece index and its data, insert it to its corresponding file(s)
    This function does NOT perform a hash check'''
    prev_len = 0
    for fobj, offset, chunk_length in self.piece_info(piece_index):
      fobj.insert_at(offset, data[prev_len:prev_len + chunk_length])
      prev_len += chunk_length
    self.pieces[piece_index]['have'] = True
    self.downloaded += len(data)

  def has_good_status(self):
    '''Boolean flag indicating whether the torrent can stay in the queue'''
    return self.good_status

  def read_torrent_file(self, filename):
    '''Attempt to read a torrent file and return its content.
    Returns a dictionary'''
    try:
      with open(filename, mode='rb') as localized_file:
        return bdecoder.decode(localized_file.read().decode("latin1"))
    except IOError as e:
      print("File ",filename," could not be found")
      self.good_status = False

  def parse_partfile_data(self, path, name, args):
    '''Return the name of the partfile for this torrent'''
    if isinstance(args, int):
      self.total_size = args
    elif isinstance(args, list):
      for arg in args:
        self.total_size += arg['length']
    else:
      print("Received unrecognized args:\n\t%r\n\ttype: %s"%(args,type(args)))
      sys.exit(2)

    # TODO: properly implement 'completed' flag for each file
    if isinstance(args, int):
      return [{"name": name, "fullpath": self.pathify_file(path, name),"length": args, 
        "file": File(self.pathify_file(path, name))}]
    elif isinstance(args, list):
      if name:
        self.filepath = os.path.join(self.filepath, name)
        path = os.path.join(path, name)
        self.log.debug("New path: %s" % path)
      return [{"name": f['path'], "fullpath": self.pathify_file(path, f['path']),
        "length": f['length'], 
        "file": File(self.pathify_file(path, f['path']))
        } for f in args]
    else:
      print("arg of type: %s" % type(args))
      raise TypeError("torrent file must end in .torrent, given %s which ends with %s"
        %(self.filename, os.path.split(self.filename)[-1]))

  def pathify_file(self, path, filename):
    '''Locate a part file in the given path. If an existing file is not found
    return a file with a .part extension'''
    if isinstance(filename, list):
      if len(filename) == 1:
        filename = filename[0]
      elif len(filename) == 2:
        filename = os.path.join(filename[0], filename[1])
    elif isinstance(filename, str):
      pass
    else:
      self.log.critical("An error occurred when parsing the files")
      self.log.critical("Expected: list or str. Received: %s" % type(filename))
      self.log.debug(filename)
      sys.exit(1)
    return os.path.join(path, filename)
    
  def downloaded(self, name = ""):
    '''Return the total downloaded, which is the size of the part file'''
    return self.downloaded

  def parse_trackers(self, metainfo_data):
    '''Populate the list of http trackers'''
    if 'announce-list' in metainfo_data:
      for t in metainfo_data['announce-list']: # Addendum to the specification
        if isinstance(t, list):
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
    params = { 
      "info_hash": parse.quote(self.info_hash), "peer_id": parse.quote(self.peerid),
      "port": 51413,  # TODO: Decide on a different port
      "uploaded": 0,   #TODO: uploaded = ? NOTE: can only keep track for sesh
      "downloaded": self.downloaded,
      "left": self.pieces_left * self.piece_size,
      "event": self.event(),
      "compact": COMPACT
#      "numwant":MAX_PEERS - len(self.peers),
    }
    # NOTE: urlencode uses quote_plus, which doesn't work here
#    return "?"+parse.urlencode(params)
    url = "?"
    for key, value in params.items():
      url+='%s=%s&'%(key,value)
    return url[:-1]

  def event(self):
    '''Determine "event" value to be sent to tracker(s)'''
    if self.shutdown:
      return "stopped"
    else:
      return "started"

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

  def update_peers(self, peer_info_list):
    '''Given a list of dictionaries, update the list of peers for this torrent'''
    if peer_info_list is not None:
      self.backup_peers.extend(peer_info_list)
    for peer_info in self.backup_peers:
      if self.add_peer(peer_info):
        del self.backup_peers[self.backup_peers.index(peer_info)]
    Peer.loop()
    # Check for anything to remove
    for index, peer in enumerate(self.peers):
      if peer.can_remove():
        self.remove_peer(index)

  def add_peer(self, peer_info):
    '''Add to our list of peers if it is not already there'''
    if len(self.peers) < MAX_PEERS:
      self.peers.append(Peer(peer_info, {"info_hash": self.info_hash, "handshake": self.get_handshake()}))
      return True

  def remove_peer(self, peer_index):
    '''Remove from our list of peers, if it exists'''
    unfinished = self.peers[peer_index].unfinished_pieces()
    if unfinished:
      for pc in unfinished:
        self.pieces[unfinished[pc]['index']]['requested'] = False
    del self.peers[peer_index]

  def get_num_peers(self):
    '''Return the number of currently active peers'''
    return len(self.peers)

  def map_pieces(self, current_map):
    '''Given the pieces string, map them 20-byte sized chunks
    The piece map contains a list of dictionaries (one per piece) each containing
    the keys: hash | have | requested | priority | attempts'''
    piece_length = 20 # the hash is 20 bytes long
    if isinstance(current_map, str):
      current_map = current_map.encode("latin-1")
    self.pieces = [{"hash":current_map[i:i+piece_length],
      "have": False,  "requested": False, 
      "priority": 0,  "attempts": 0}
       for i in range(0, len(current_map), piece_length)]
    calc_total = len(self.pieces) * self.piece_size
    overage = calc_total - self.total_size
    if overage:
      self.pieces[-1]['size'] = self.piece_size - overage
      calc_total = calc_total - overage
    if calc_total != self.total_size:
      self.log.critical("The pieces for the torrent were incorrectly mapped")
      sys.exit(0)
    self.log.debug("Attempting to download: %s\t%s" \
      % (calc_total, strmanip.parse_filesize(calc_total, 1000)))
    self.update_map()

  def update_map(self):
    '''Check existing filedata, if any, and confirm its integrity'''
    self.log.debug("Total size: %s. Piece size: %s" % (self.total_size, self.piece_size))
    for index, piece in enumerate(self.pieces):
      piece['have'] = self.check_piece(index, b''.join(
        [chunkfile.read_from(offset, chunklen) for chunkfile, offset, chunklen in self.piece_info(index)]))
    self.log.debug("Starting with %s pieces" % len([n for n in self.pieces if n['have']]))

  def piece_info(self, pieceindex):
    '''Returns a list of tuples containing the File object(s) this piece belongs to,
    the beginning (within that file) where this piece belongs, and the length
    to be inserted within each file. e.g.:
    [(fileObj0, offset0, length0), (fileObj1, offset1, length1), ...]
    '''
    piece_length = self.pieces[pieceindex].get('size', self.piece_size)
    beginning = pieceindex * self.piece_size
    current_pos = 0 # from zeroeth file
    pc_map = []
    while current_pos < beginning + piece_length:
      for fileinfo in self.partfiledata:
        if current_pos < beginning and fileinfo['length'] + current_pos < beginning:
          current_pos += fileinfo['length']
          continue  # not there yet
        elif current_pos > beginning + piece_length:
          current_pos += fileinfo['length']
          break # overshot, this piece is done
        else:
          # offset within the file, if any
          pos = beginning - current_pos if beginning > current_pos else 0
          if pos + piece_length <= fileinfo['length']:
            pc_map.append((fileinfo['file'], pos, piece_length))
            current_pos += fileinfo['length']
          else: # appending the entirety will exceed file length
            pc_map.append((fileinfo['file'], pos, fileinfo['length'] - pos))
            piece_length -= fileinfo['length'] - pos
            current_pos += pos
    return pc_map

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
    return length == self.downloaded(filepath)

