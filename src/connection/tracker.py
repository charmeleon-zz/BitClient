#!/usr/bin/dev python3
# Bitclient -- tracker.py

from encoding import bdecoder, bencoder
from hashlib import sha1 as sha
from urllib import parse

MAX_PEERS = 35
COMPACT = 1
class Tracker(object):
  def query_tracker(self,meta_info):
    '''
    From the metafile, query the tracker(s)
  
    '''
    # create url string
    announce = meta_info['announce']+"?"
    params = {
      "info_hash":parse.quote(sha(bencoder.encode(meta_info['info']).encode("latin-1")).digest()), # digest vs hexdigest
      "peer_id":parse.quote('-BCSS-Tw3nTyl3tTer13'),
      "port":51413,
      "uploaded":0,   #TODO: uploaded = ?
      "downloaded":0, #TODO: downloaded = len(file+.part)
      "left":726269952,       #TODO: left = len(file)-downloaded
      "numwant":MAX_PEERS,
      "compact":COMPACT
    }
    url='?'
    # order doesn't matter, which is good since these will come otu
    # in no particular order (thanks Allison (aka akaptur)!)
    for key, value in params.items():
      url+='%s=%s&'%(key,value) #TODO: @SEE parse.urlencode
    url = url[:-1] # chop off the last member (ouch)
  
    if "ubuntu" in meta_info['announce']:
      print("Querying tracker...")
      info_hash = "%5c2V%deA%d3z%f1%7f%c8%ef%20%bc%3f%e8q%f8%c7%e8%0f"
      print("Expected hash: ",info_hash)
      if info_hash==params["info_hash"]:
        print("They are the same")
      else:
      print("URL: ",url)
  def parse_tracker_response(self,tracker_response):
    '''
    Capture and parse the tracker response
    '''
    
