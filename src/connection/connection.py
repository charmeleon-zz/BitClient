#!/usr/bin/dev python3
# BitClient -- connection.py
import sys,socket

class Connection(object):
  '''
  The connection client for BitClient. A single connection should manage all
  sockets

  '''

  def __init__(self,HOST='',PORT=0):
    '''
    When the Connection initializes, we will be immediately connected as
    localhost and begin listening to a port

    '''
    self.s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    self.trackers = getTrackers()
    print("Socket: ",self.s.getsockname())
  
  def keep_alive():
    '''The keep-alive message is a message with zero bytes. There is no message
    ID and no payload.
    '''
    return "0000"
  def choke():
    '''The choke message is fixed-length and has no payload.'''
    return "00010"

  def unchoke():
    '''The unchoke message is fixed-length and has no payload.'''
    return "00011"

  def interested():
    '''The interested message is fixed-length and has no payload.'''
    return "00012"

  def not_interested():
    '''The not interested message is fixed-length and has no payload.'''
    return "00013"

  def connectTracker(self,SERVER):
    print(SERVER)

  def add_peer(self,ADDRESS,PORT):
    '''
  
    '''
    # self.s.bind((ADDRESS,PORT))
    # print("Connected to: %r"%ADDRESS)
    #

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
  
    # TODO: Support for multi-trackers (dictionary form)
    if "http://" in meta_info['announce']:
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
    
    '''Messages
    The have message is fixed length. The payload is the zero-based index of a piece that has just been successfully downloaded and verified via the hash.
    
    Implementer's Note: That is the strict definition, in reality some games may be played. In particular because peers are extremely unlikely to download pieces that they already have, a peer may choose not to advertise having a piece to a peer that already has that piece. At a minimum "HAVE suppression" will result in a 50% reduction in the number of HAVE messages, this translates to around a 25-35% reduction in protocol overhead. At the same time, it may be worthwhile to send a HAVE message to a peer that has that piece already since it will be useful in determining which piece is rare.
    
    A malicious peer might also choose to advertise having pieces that it knows the peer will never download. Due to this attempting to model peers using this information is a bad idea.
    bitfield: <len=0001+X><id=5><bitfield>
    
    The bitfield message may only be sent immediately after the handshaking sequence is completed, and before any other messages are sent. It is optional, and need not be sent if a client has no pieces.
    
    The bitfield message is variable length, where X is the length of the bitfield. The payload is a bitfield representing the pieces that have been successfully downloaded. The high bit in the first byte corresponds to piece index 0. Bits that are cleared indicated a missing piece, and set bits indicate a valid and available piece. Spare bits at the end are set to zero.
    
    Some clients (Deluge for example) send bitfield with missing pieces even if it has all data. Then it sends rest of pieces as have messages. They are saying this helps against ISP filtering of BitTorrent protocol. It is called lazy bitfield.
    
    A bitfield of the wrong length is considered an error. Clients should drop the connection if they receive bitfields that are not of the correct size, or if the bitfield has any of the spare bits set.
    request: <len=0013><id=6><index><begin><length>
    
    The request message is fixed length, and is used to request a block. The payload contains the following information:
    
        index: integer specifying the zero-based piece index
        begin: integer specifying the zero-based byte offset within the piece
        length: integer specifying the requested length. 
    
    This section is under dispute! Please use the discussion page to resolve this!
    
    View #1 According to the official specification, "All current implementations use 2^15 (32KB), and close connections which request an amount greater than 2^17 (128KB)." As early as version 3 or 2004, this behavior was changed to use 2^14 (16KB) blocks. As of version 4.0 or mid-2005, the mainline disconnected on requests larger than 2^14 (16KB); and some clients have followed suit. Note that block requests are smaller than pieces (>=2^18 bytes), so multiple requests will be needed to download a whole piece.
    
    Strictly, the specification allows 2^15 (32KB) requests. The reality is near all clients will now use 2^14 (16KB) requests. Due to clients that enforce that size, it is recommended that implementations make requests of that size. Due to smaller requests resulting in higher overhead due to tracking a greater number of requests, implementers are advised against going below 2^14 (16KB).
    
    The choice of request block size limit enforcement is not nearly so clear cut. With mainline version 4 enforcing 16KB requests, most clients will use that size. At the same time 2^14 (16KB) is the semi-official (only semi because the official protocol document has not been updated) limit now, so enforcing that isn't wrong. At the same time, allowing larger requests enlarges the set of possible peers, and except on very low bandwidth connections (<256kbps) multiple blocks will be downloaded in one choke-timeperiod, thus merely enforcing the old limit causes minimal performance degradation. Due to this factor, it is recommended that only the older 2^17 (128KB) maximum size limit be enforced.
    
    View #2 This section has contained falsehoods for a large portion of the time this page has existed. This is the third time I (uau) am correcting this same section for incorrect information being added, so I won't rewrite it completely since it'll probably be broken again... Current version has at least the following errors: Mainline started using 2^14 (16384) byte requests when it was still the only client in existence; only the "official specification" still talked about the obsolete 32768 byte value which was in reality neither the default size nor maximum allowed. In version 4 the request behavior did not change, but the maximum allowed size did change to equal the default size. In latest mainline versions the max has changed to 32768 (note that this is the first appearance of 32768 for either default or max size since the first ancient versions). "Most older clients use 32KB requests" is false. Discussion of larger requests fails to take latency effects into account.
    piece: <len=0009+X><id=7><index><begin><block>
    
    The piece message is variable length, where X is the length of the block. The payload contains the following information:
    
        index: integer specifying the zero-based piece index
        begin: integer specifying the zero-based byte offset within the piece
        block: block of data, which is a subset of the piece specified by index. 
    
    cancel: <len=0013><id=8><index><begin><length>
    
    The cancel message is fixed length, and is used to cancel block requests. The payload is identical to that of the "request" message. It is typically used during "End Game" (see the Algorithms section below).
    port: <len=0003><id=9><listen-port>
    
    The port message is sent by newer versions of the Mainline that implements a DHT tracker. The listen port is the port this peer's DHT node is listening on. This peer should be inserted in the local routing table (if DHT tracker is supported). 
      '''
