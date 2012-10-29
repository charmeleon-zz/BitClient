#!/usr/bin/dev python
# BitClient -- peer.py

import sys,struct,socket


#TODO: Ideally, Peer class should have a Protocol object, which would be a 
#TCP/UDP/uTP wrapper depending on settings.

class Peer(object):
  def __init__(self, peer_info, session_data):
    '''Initialize a peer object given a dictionary with port and ip as well as a
    handshake and info_hash'''
    self.ipaddr, self.port = peer_info['ip'], peer_info['port']
    self.handshake, self.info_hash = session_data['handshake'], session_data['info_hash']
    self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    self.status_ok = True
    print("Initialized peer, attempting to connect")
    self.sock.settimeout(5)
    try:
      self.sock.connect((self.ipaddr,int(self.port)))
    except (ConnectionRefusedError, KeyboardInterrupt, TimeoutError) as e:
      print("Connection for %s:%s timed out or refused."%(self.ipaddr,self.port))
      self.disconnect()
    self.sock.settimeout(None) # once we're connected, we're bros
#    self.socketdata = self.sock.makefile("rw",0)

  def disconnect():
    '''Disconnect from peer and remove OK status'''
    self.status_ok = False
    self.close()

  def prepare_message(self, message):
    pass

  def good_status(self):
    return self.status_ok

  def send_message(self, message):
    self.sock.sendall(message)
    reply = self.sock.recv(1024*1024)
    if self.handshake not in reply:
      self.close()
    '''If the initiator of the connection receives a handshake in which the 
    peer_id does not match the expected peerid, then the initiator is expected 
    to drop the connection. '''
    print("The peer said ",repr(reply))

  def receive_data(self):
    pass

  def close(self):
    '''Close the socket connection'''
    self.sock.close()

  def shake_hand(self):
    print("Shaking hands with ",repr(self.handshake))
    self.send_message(self.handshake)
#    self.close()

