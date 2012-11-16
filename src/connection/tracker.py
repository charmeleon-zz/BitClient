#!/usr/bin/dev python3
# Bitclient -- tracker.py

import sys, re, socket, struct, time, math
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from urllib.error import URLError
from src.encoding import bdecoder

TRACKER_TIMEOUT = 300 # Timeout if tracker request fails
MAX_FAILURE = 6 # Maximum number of failures for a tracker before we no longer try (sesh)

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
    self.timeouts = 0 # num of times we have requested tracker and it has been out
    self.refresh = 0
    self.timer = time.time()

  def announce(self,query_string):
    '''Announce to the tracker, returns the tracker's raw HTTP reply (headers included).
    Returns the peer list of tuples'''
    # The query string changes, so we should re-parse every time we announce
    newp = urlparse(self.tracker_url+query_string)
    try:
      print("URL: %s?%s"%(self.tracker_url,newp.query))
      rawreply = urlopen("%s?%s"%(self.tracker_url,newp.query)).read().decode("latin1") # bencoded reply
      self.timer = time.time()
      return self.get_peer_list(rawreply)
    except (ConnectionRefusedError, URLError) as e:
      print("An error ocurred when connecting to host %s: %s. Trying again in %ds"%(self.host,e,TRACKER_TIMEOUT))
      self.timeout = True
      self.timer = time.time()
      pass

  def can_reannounce(self):
    return bool(self.refresh == 0 or (time.time()-self.timer)>=self.refresh)

  def is_available(self):
    return bool(self.timeout==False or 
                  (self.timeout==True and math.floor(time.time()-self.timer)>=TRACKER_TIMEOUT and self.timeouts<MAX_FAILURE))

  def get_peer_list(self,raw_reply):
    '''Returns dictionary of peers with ip,port keys'''
    response = bdecoder.decode(raw_reply) # decode
    if not self.refresh:
      self.refresh = response['interval']
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
      for p in peers:
        peers_list.append(self.get_peer_info(p))
      return [{"ip":k[0],"port":k[1]} for k in peers_list]

  def _parse_binary_peers(self,peers):
    '''Generator for peers in binary format'''
    for i in range(0,len(peers),6):
      yield peers[i:i+6]

  def get_peer_info(self,peer):
    '''Pack peer info into a tuple of ipaddress and port'''
    peer_info = struct.unpack("!BBBBH",peer)
    return ".".join(str(s) for s in peer_info[:4]),peer_info[-1]

