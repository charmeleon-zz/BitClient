#!/usr/bin/dev python3
# Bitclient -- tracker.py

import sys, re, socket, struct
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from urllib.error import URLError
from src.encoding import bdecoder


class Tracker(object):
  '''A wrapper object for client-tracker communications'''
  def __init__(self,tracker_url):
    '''Initializes our communication socket and keep it open. The port info
    is extracted from the URL provided'''
    self.tracker_url = tracker_url
    self.p = urlparse(self.tracker_url)
    self.host = self.p.hostname
    self.port = 0 if self.p.port is None else self.p.port
    self.timeout = False  # if the tracker misbehaves, have it sit in a corner
    self.timer = 300 # how often we should re-announce (or re-ping), in seconds

  def announce(self,query_string):
    '''Announce to the tracker, returns the tracker's raw HTTP reply (headers included).
    Returns the peer list of tuples'''
    if self.timeout==False:
      # The query string changes, so we should re-parse every time we announce
      newp = urlparse(self.tracker_url+query_string)
      try:
        rawreply = urlopen("%s?%s"%(self.tracker_url,newp.query)).read().decode("latin1") # bencoded reply
        return self.get_peer_list(rawreply)
      except (ConnectionRefusedError, URLError) as e:
        print("An error ocurred when connecting to host %s: %s. Trying again in %ds"%(self.host,e,300))
        self.timeout = True
        self.timer = 300
        pass
    else:
      pass

  def reannounce(self):
    '''Re-announce'''

  def get_peer_list(self,raw_reply):
    '''Returns dictionary of peers with ip,port keys'''
    response = bdecoder.decode(raw_reply) # decode
    if 'peers' not in response:
      print("Peer list from tracker is empty. ",end="")
      if 'failure reason' in response:
        print(response['failure reason'])
        return
    unparsed_peers = response['peers'].encode("latin1") # get the right encoding
    peers_list = []
    if type(unparsed_peers)==dict:
      print("Unsupported peers model: dictionary")
      sys.exit(1)
    else: # binary model
      peers = self._parse_binary_peers(unparsed_peers)
      while True:
        try:
          peers_list.append(self.get_peer_info(next(peers)))
        except StopIteration: # keep going!
          break
      return [{"ip":k[0],"port":k[1]} for k in peers_list]

  def _parse_binary_peers(self,peers):
    '''Generator for peers in binary format'''
    for i in range(0,len(peers),6):
      yield peers[i:i+6]

  def get_peer_info(self,peer):
    '''Pack peer info into a tuple of ipaddress and port'''
    peer_info = struct.unpack("!BBBBH",peer)
    return ".".join(str(s) for s in peer_info[:4]),peer_info[-1]

