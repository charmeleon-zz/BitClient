#!/usr/bin/dev python3
# BitClient -- peer.py

import sys,struct,socket
import asyncore, traceback
# src library
import src.io.bitlog as bitlog

MESSAGES = {
  "keep-alive": "0000",
  "keep alive": "0000",
  "keep_alive": "0000",
  "choke"     : "00010",
  "unchoke"   : "00011",
  "interested": "00012",
  "not interested": "00013",
  "not_interested": "00013",
  "not-interested": "00013",
  "request"   : "00136"
}
MSG_ID = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
MSG_NAME = ["keep-alive", "choke", "unchoke", "interested", "not interested", "request", "piece", "cancel", "port"]
MAX_REQUESTS = 15  # max 5 pieces per peer
REQUEST_SIZE = 2**14

#TODO: Ideally, Peer class should have a Protocol object, which would be a 
#TCP/UDP/uTP wrapper depending on settings.

class Peer(asyncore.dispatcher):
  def __init__(self, peer_info, session_data):
    '''Initialize a peer object given a dictionary with port and ip as well as a
    handshake and info_hash'''
    asyncore.dispatcher.__init__(self)
    self.ipaddr, self.port = peer_info['ip'], int(peer_info['port'])
    self.handshake, self.info_hash = session_data['handshake'], session_data['info_hash']
    self.log = bitlog.log()
    self.create_socket()
    self.status_ok = True
    self.sent_prepare = False
    self.removable = False
    self.lastcall = b""
    self.writebuffer = b""
    self.handshaked = False
    self.is_choked = True
    self.choked = True
    self.is_interested = False
    self.interested = False
    try:
      self.connect((self.ipaddr, self.port))
    except (ConnectionRefusedError, OSError) as e:
      self.disconnect()
    self.pending_requests = 0
    self.bitfield = {}
    self.block = []
    self.piece_buffer = []  # pending
    self.piece_completed = [] # done

  def handle_read(self):
    try:
      r = self.get_from_buffer()
      if r:
        self.parse_message(r)
    except (ConnectionRefusedError, OSError) as e:
      self.log.warn("Connection refused: %s:%s" % (self.ipaddr, self.port))
      self.disconnect()

  def handle_write(self):
    if self.writebuffer:
      if isinstance(self.writebuffer, str):
        self.writebuffer = bytes(self.writebuffer, "UTF-8")
      sent = self.send(self.writebuffer)
      self.writebuffer = self.writebuffer[sent:]
    else:
      pass
      #self.writebuffer = self.get_message("keep alive")

  def handle_connect(self):
    if not self.handshaked:
      try:
        self.shake_hand()
      except ConnectionRefusedError:
        self.disconnect()

  def handle_close(self):
    self.disconnect()

  def disconnect(self):
    '''Disconnect from peer and remove OK status'''
    self.removable = True
    self.interested = False
    self.status_ok = False
    self.close()

  def has_advertised(self):
    '''Whether the peer has advertised having pieces'''
    return len(self.bitfield) > 0

  def get_message(self, message):
    '''Find the prescribed message by id or string'''
    if isinstance(message, str):
      if message in MESSAGES.keys():
        return self.prepare_message(MESSAGES[message])
    elif isinstance(message, int):
      if message in MSG_ID:
        return MSG_NAME[MSG_ID]
    else:
      return False

  def prepare_message(self, message):
    '''Prepare a message for transmission according to BT spec'''
    if len(message) == 4:
      return struct.pack("!I", int(message[:4]))
    elif len(message) == 5:
      return struct.pack("!IB", int(message[:4]), int(message[4:5]))
    else:
      t = struct.pack("!IB", int(message[:4]) + int(message[4:5])) + bytes(''.join(chr(int(a)) for a in message[5:]), "UTF-8")
      return t
  def can_request(self):
    '''Whether we've maxed out the number of requests per peer'''
    return self.connected and self.handshaked and self.sent_prepare and self.interested and not self.choked and self.pending_requests < MAX_REQUESTS

  def good_status(self):
    '''Whether connection is ok, peer is interested and not choked'''
    return self.status_ok and self.interested and not self.is_choked

  def get_from_buffer(self, reply_buffer=4096):
    '''Retrieve more data from the buffer, without sending a message'''
    return self.recv(reply_buffer)

  def request_piece(self, piece_index, piece_size):
    '''Request this piece from the peer'''
    if not [f for f in self.piece_buffer if f['index'] == int(piece_index)]:
      self.pending_requests+=1
      self.piece_buffer.append({"index": int(piece_index), "size": int(piece_size), "data": []})
      last_block_num = piece_size / REQUEST_SIZE
      last_block_size = piece_size % REQUEST_SIZE
      for i in range(0, piece_size, REQUEST_SIZE):
        if last_block_size:
          if i == last_block_num:
            self.add_to_buffer(self.get_message("request") + struct.pack("!III", int(piece_index), int(i/REQUEST_SIZE), last_block_size))
            break
        self.add_to_buffer(self.get_message("request") + struct.pack("!III", int(piece_index), int(i/REQUEST_SIZE), REQUEST_SIZE))
      self.log.info("Requesting piece: %s\tNumber of blocks: %s\tTotal: %s\tPeer: %s:%s" % (piece_index, last_block_num, piece_size, self.ipaddr, self.port))

  def has_piece(self, piece_index):
    '''Whether this peer has announced having this piece'''
    try:
      return self.bitfield[piece_index]
    except KeyError:
      return False

  def can_remove(self):
    return self.removable

  def unfinished_pieces(self):
    return self.piece_buffer

  def parse_message(self, message):
    '''Given a peer's output'''
    if self.lastcall:
      if len(self.lastcall) == len(message):
        self.log.warning("Possible duplication -- lastcall, message")
        if message == self.lastcall:
          self.log.critical("Duplication confirmed, fix ASAP")
          self.log.critical("%s\n%s" % (self.lastcall, message))
      message = b''.join(a for a in [self.lastcall, message])
      self.lastcall = b''
    if len(message) == 0:
      self.log.warn("Received empty message")
      return
    if message[1:20].lower() == b"bittorrent protocol":
      self.process_handshake(message)
      return
    elif len(message) < 4:
      self.lastcall = message
      return
    prefix = message[:4]
    msg_len = 0
    try:
      msg_len = struct.unpack('!I', prefix)[0]
    except struct.error:
      self.log.error("Attempted to unpack: %s\n\tFull message: %s" % (prefix, message))
      self.log.error(traceback.print_last())
      sys.exit(1)
    if len(message[4:]) != msg_len:
      if len(message[4:]) < msg_len:  # incomplete message, let's wait
        self.lastcall = message
      elif len(message[4:]) > msg_len:  # serial message, de-serialize
        self.parse_message(message[:msg_len+4])
        self.parse_message(message[msg_len+4:])
      return
    if msg_len == 0:  # keep alive
      self.status_ok == True
    else:
      msg_id = ord(message[4:5])  # TODO: Is this bulletproof?
      if msg_id == 0:
        self.log.debug("We have been choked %s:%s" % (self.ipaddr, self.port))
        self.choked = True
        sys.exit(0)
      elif msg_id == 1:
        self.log.debug("We have been unchoked %s:%s" % (self.ipaddr, self.port))
        self.choked = False
      elif msg_id == 2:
        self.log.debug("Peer is interested")
        self.is_interested = True
      elif msg_id == 3:
        self.log.debug("Peer is not interested")
        self.is_interested = False
      elif msg_id == 4:
        self.update_bitfield_with_have(message[5:])
      elif msg_id == 5:
        self.update_bitfield(message[5:])
        if not self.sent_prepare:
          self.prepare_peer()
      elif msg_id == 7:
        self.process_block(message[5:])
      elif msg_id == 8:
        self.log.debug("Peer is requesting cancellation %s " % message[5:])
        sys.exit(1)
      elif msg_id == 9:
        print("Peer is advicing on port: %s " % message[5:])
      else:
        self.log.critical("invalid tcp msg rcvd - malicious or ignorant, equally dangerous")
        self.log.critical("msg id : %s\tLen: %s\tPeer: %s:%s " % (msg_id, msg_len, self.ipaddr, self.port))
        self.log.critical(message)
        self.disconnect()

  def process_block(self, b):
    '''Add block to piece buffer'''
    index, begin, block = struct.unpack("!I", b[:4])[0], struct.unpack("!I", b[4:8])[0], b[8:]
    for p in [a for a in self.piece_buffer if a['index'] == index]:  # piece
      p['data'].insert(index, block)
      if len(b''.join([j for j in p['data']])) == p['size']:
        self.piece_completed.append({"index": index, "data": b''.join([k for k in p['data']])})
        self.piece_buffer.remove([a for a in self.piece_buffer if a['index'] == index][0])
        self.pending_requests -= 1

  def has_complete_pieces(self):
    '''Announce that we have a complete piece'''
    return len(self.piece_completed)

  def complete_pieces(self):
    '''Return any complete pieces and empty the buffer'''
    tmp = self.piece_completed
    self.piece_completed = []
    return tmp

  def update_bitfield_with_have(self, have):
    '''Maps a have message to the bitfield'''
    self.bitfield[struct.unpack("!I", have)[0]] = True
    

  def update_bitfield(self, bf):
    '''Handle the contents of a bitfield message'''
    for b in [i for i in enumerate(bf)]:
      if b[1] == 255:
        self.bitfield[b[0]] = True

  def shake_hand(self):
    '''Send our handshake to the peer'''
    self.add_to_buffer(self.handshake)

  def process_handshake(self, reply):
    '''Confirm that a full handshake was received'''
    reply_len = reply[0]+49
    if reply_len == len(reply):
      self.status_ok = True
      self.handshaked = True
    elif len(reply) > reply_len:
      self.status_ok = True
      self.handshaked = True
      self.lastcall = reply[reply_len:]
    else:
      self.log.warn("Incomplete handshake received %s:%s" % (self.ipaddr, self.port))
      self.disconnect()
    self.log.info("Handshake with %s:%s successful." % (self.ipaddr, self.port))

  def prepare_peer(self):
    '''Send interested + unchoke message'''
    self.add_to_buffer(self.get_message('interested'))
    self.interested = True
    self.sent_prepare = True

  def add_to_buffer(self, message):
    '''Add a message to the writebuffer, which will be sent out in the next loop'''
    if isinstance(message, str):
      message = bytes(message, "UTF-8")
    self.writebuffer = b''.join(a for a in [self.writebuffer, message])

  @staticmethod
  def loop():
    asyncore.loop(30.0, False, None, 1000)
asyncore.loop()

