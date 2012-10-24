#!/usr/bin/dev python
# BitClient -- peer.py

import struct,socket

class Peer(object):
  def __init__(self, peer_info):
    '''Initialize a peer object given a dictionary'''
    self.port = peer_info['port']
    self.ipaddr = peer_info['ip']
    self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    self.sock.connect((self.ipaddr,int(self.port)))
    self.socketdata = self.sock.makefile("rw",0)

  def prepare_message(self, message):
    return struct.pack("!4s",

  def send_message(self, message):
    pass

  def receive_data(self):
    pass

  def close(self):
    '''Close the socket connection'''
    self.sock.close()

  
