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
    self.truncate = self.total_size - len(self.pieces) * self.piece_size
    self.peers = [] # Peer objects
    self.backup_peers = [] # list of {ip:,port:} dicts for backup
    self.temp_file = File(self.filename.replace(".torrent", ".part"))
    self.uploaded = 0
    self.finished = False
    self.downloaded = 0
    self.runtime = time.time()

  def torrent(self):
#    stdscr = curses.initscr()
#    curses.noecho()
#    stdscr.keypad(1)
    stop = False
    pieces_left = 0
#    begin_x = 20; begin_y = 7; height = 1; width = 80
#    cur = curses.newwin(height, width, begin_y, begin_x)
    while not stop:
      debug_flase = False
      self.update_peers(self.query_trackers())
      pieces_left = len([m for m in self.pieces if not m['have']])
      # Check whether we still have pieces left to send
      if not pieces_left:
        self.log.debug("Download completed, cleaning up...")
        self.extract_from_temp()
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
          self.log.debug("%s/%s pieces downloaded. Rate: %s/s" %
            (len(self.pieces) - pieces_left, len(self.pieces), strmanip.parse_filesize(self.downloaded/(time.time() - self.runtime), 1000)))
          for piece in peer.complete_pieces():
            if self.check_piece(piece['index'], piece['data']):
              self.write_to_temp(piece['index'], piece['data'])
            else:
              self.log.warn("Piece hash FAILED. Index: %s" % piece['index'])
              self.pieces[piece['index']]['requested'] = False
              sys.exit(0)
      Peer.loop()
    print("Exiting BitClient")
    sys.exit(1)

  def check_piece(self, piece_index, data):
    '''Hash-check a given piece'''
#    if sha(data).digest() != self.pieces[piece_index]['hash']:
#      if piece_index < 5:
#        self.log.debug("Piece: %s" % piece_index)
#        self.log.debug(sha(data).digest())
#        self.log.debug(self.pieces[piece_index]['hash'])
#        self.log.debug("Piece length: %s\tExpected length: %s\tNum: %s" 
#            % (len(data), self.pieces[piece_index].get('size', self.piece_size), piece_index))
#      self.log.debug("Piece begin: %s" % data[:100])
#      self.log.debug("Piece end: %s" % data[-100:])
#      sys.exit(0)
#    else:
#      self.log.debug("Piece %s checks out OK" % piece_index)
    return sha(data).digest() == self.pieces[piece_index]['hash']

  def write_to_temp(self, piece_index, data):
    if not self.pieces[piece_index]['have']:
      self.temp_file.insert_at(piece_index * self.piece_size, data)
      self.pieces[piece_index]['have'] = True
      self.downloaded += len(data)

  def extract_from_temp(self):
    '''Extract the binary data from a single .part file and parse it to multiple
    files'''
    self.log.debug("Extracting from temp")
    total = 0
    for fileinfo in self.partfiledata:
      self.log.debug("Writing %s" % fileinfo['name'])
      # to avoid running out of RAM, let's not write more than 512MiB at a time
      if fileinfo['length'] <= 2**29:
        fileinfo['file'].insert_at(0, self.temp_file.read_from(total, fileinfo['length']))
        total += fileinfo['length']
      else:
        tmp = fileinfo['length']
        while tmp > 2**29:
          fileinfo['file'].insert_at(0, self.temp_file.read_from(total, 2**29))
          total += 2**29
        if tmp:
          fileinfo['file'].insert_at(0, self.temp_file.read_from(total, tmp))
          total += tmp
          tmp = 0
    self.log.debug("Done parsing files. Exiting BitClient")
#    curses.nobreak(); curses.echo(); curses.endwin()
    sys.exit(0)

  def write_piece(self, piece_index, data, offset = 0):
    '''Allocates the piece to the appropriate file(s), as they come in'''
    # NOTE: Work in progress, does NOT work in its current state
    # TODO: Hash check before writing
    piece_pos = piece_index * self.piece_size
    total = offset
    for fileinfo in self.partfiledata:
      # Piece corresponds to this file
      if piece_pos <= total + fileinfo['length']:
        # Inserting this piece as-is will not exceed length of file
        if fileinfo['length'] >= piece_pos - total + len(data):
          fileinfo['file'].insert_at(pos - total, data)
          self.log.debug("Writing piece %s to file %s" % (piece_index, fileinfo['file'].get_name()))
          break
        # Inserting this piece exceeds file boundaries...
        else:
          # ...because this is the last piece and we are supposed to truncate it
          if self.truncate and piece_index == len(self.pieces) - 1:
            fileinfo['file'].insert_at(pos - total, data[:self.truncate])
          # ...because the pice is bigger than the file to begin with
          elif len(data) > fileinfo['length']:
            fileinfo['file'].insert_at(pos - total, data[:fileinfo['length']])
            self.write_piece(piece_index, data[fileinfo['length']:])
          # The data that we have, by itself, is bigger than the file
          elif len(data) > fileinfo['length']:
            if self.truncate and piece_index == len(self.pieces) - 1:  # indeed, last piece
              self.log.debug("Writing last piece to file %s" % fileinfo['file'].get_name())
              fileinfo['file'].insert_at(pos - total, data[:self.truncate])
              sys.exit(0)
            else:
              fileinfo['file'].insert_at(pos - total, data[:fileinfo['length']])
              sys.exit(0)
          # Either the piece overlaps, or this is the last piece and we should truncate
          else:
            fileinfo['file'].insert_at(pos - total, data[:pos - total + fileinfo['length']])
            self.log.critical("File: %s" % fileinfo['file'].get_name())
            self.log.critical("Current piece exceeds file length. Piece: %s" % piece_index)
            self.log.critical("Filename: %s" % fileinfo['name'])
            self.log.critical("File length: %s. Offset: %s. Piece size: %s" % (fileinfo['length'], pos - total, len(data)))
            self.log.critical("Attempted insert of %s bytes" % (pos - total + fileinfo['length']))
            sys.exit(0)
      # Piece belongs elsewhere, keep going
      else:
        total += fileinfo['length']

  def has_good_status(self):
    return self.good_status

  def read_torrent_file(self, filename):
    '''Attempt to read a torrent file and return its content.
    Returns a dictionary'''
    try:
      with open(filename, mode='rb') as localized_file:
        return bdecoder.decode(localized_file.read().decode("latin1"))
    except IOError as e:
      print("File ",filename," could not be found")
      sys.exit(2)
      # TODO: bump the error upwards and catch in client, remove from queue

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

    if isinstance(args, int):
      return [{"name":name, "fullpath": self.pathify_file(path, name),"length": args, 
        "completed": self.completed_status(self.pathify_file(path, name), args), "lower": 0, "file": File(self.pathify_file(path, name))}]
    elif isinstance(args, list):
      if name:
        self.filepath = os.path.join(self.filepath, name)
        path = os.path.join(path, name)
        if not os.path.exists(path):
          os.makedirs(path)
        self.log.debug("New path: %s" % path)
      return [{"name": f['path'], "fullpath": self.pathify_file(path, f['path']),
        "length": f['length'], 
        "completed": self.completed_status(self.pathify_file(path, f['path']), f['length']),
        "file": File(self.pathify_file(path, f['path']))} for f in args]
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
      self.log.critical("An error occurred when parsing the files")
      self.log.critical("Expected: list or str. Received: %s" % type(filename))
      sys.exit(1)
    return os.path.join(path, filename)
    
  def downloaded(self, name = ""):
    '''Return the total downloaded, which is the size of the part file'''
    return self.downloaded
#    return 0

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
    # create url string
    params = { 
      "info_hash": parse.quote(self.info_hash), "peer_id": parse.quote(self.peerid),
      "port":51413,
      "uploaded":0,   #TODO: uploaded = ? NOTE: can only keep track for sesh
      "downloaded": self.downloaded, #TODO: Is this working? Debug
      "left": self._get_left(),
      "event": "started",
      "compact": COMPACT
#      "numwant":MAX_PEERS - len(self.peers),
    }
    # NOTE: urlencode uses quote_plus, which doesn't work here
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
    return self.total_size-self.downloaded

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
    '''Given the pieces string, map them 20-byte sized chunks'''
    piece_length = 20 # the hash is 20 bytes long
    if isinstance(current_map, str):
      current_map = current_map.encode("latin-1")
    self.pieces = [{"hash":current_map[i:i+piece_length],
      "have": False,  "requested": False, 
      "priority": 0,  "written": False,
      "attempts": 0}
       for i in range(0, len(current_map), piece_length)]
#   piece_map: hash | have | requested | priority | attempts  | index | file
    calc_total = len(self.pieces) * self.piece_size
    overage = calc_total - self.total_size
    if overage:
      self.pieces[-1]['size'] = self.piece_size - overage
      calc_total = calc_total - overage
    if calc_total != self.total_size:
      self.log.critical("The pieces for the torrent were incorrectly mapped")
      sys.exit(0)
    self.log.debug("Attempting to download: %s\t%s" %  (calc_total, strmanip.parse_filesize(calc_total, 1000)))
    self.update_map()

  def update_map(self):
    '''Check existing filedata, if any, and confirm its integrity'''
    self.log.debug("Number of pieces: %s" % len(self.pieces))
    # Beginning from piece 0
    totaldata = 0
    fileindex = 0
    pieceindex = 0
    self.log.debug("Total size: %s. Piece size: %s" % (self.total_size, self.piece_size))
    if os.path.exists(self.filename.replace(".torrent", ".part")):
      f = File(self.filename.replace(".torrent", ".part"))
      for i in range(0, self.total_size, self.piece_size):
        pieceindex = int(i/self.piece_size)
        self.pieces[pieceindex]['have'] = \
          self.check_piece(pieceindex, f.read_from(i, self.piece_size))
      f.close()
    else:
      leftover = b""
      # Going through each file
      for fileindex, fileinfo in enumerate(self.partfiledata):
        # Jumping through the data in increments of piece_size
        for i in range(0, fileinfo['length'], self.piece_size):
          pieceindex = int(i/self.piece_size)
          # If we don't exceed the file's boundary
#          self.log.debug("Checking piece %s, file %s" % (pieceindex, fileinfo['name']))
          if i + self.piece_size < fileinfo['length']:
            if not leftover:
              # check the hash directly
              self.pieces[pieceindex]['have'] = \
                self.check_piece(pieceindex, fileinfo['file'].read_from(i, self.piece_size))
            else:
              # prepend leftover and evaluate
              self.pieces[pieceindex]['have'] = \
                self.check_piece(pieceindex, b''.join([leftover, fileinfo['file'].read_from(i, self.piece_size - len(leftover))]))
              leftover = b""
          # Otherwise, if we're at the last file, we may have an irregular piece
          elif fileindex == len(self.partfiledata) - 1:
            if not leftover:
              self.pieces[pieceindex]['have'] = \
                self.check_piece(pieceindex, fileinfo['file'].read_from(i, self.piece_size))
            else:
              self.pieces[pieceindex]['have'] = \
                self.check_piece(pieceindex, b''.join([leftover, fileinfo['file'].read_from(i, self.pieces[pieceindex]['size'])]))
              leftover = b""
          # Finally, it could just be a piece that overlaps
          else:
            leftover = fileinfo['file'].read_from(i, fileinfo['length'] - i)
    self.log.debug("Starting with %s pieces" % len([n for n in self.pieces if n['have']]))
#    self.log.debug(self.pieces)
    # Alternatively, from the first file

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

