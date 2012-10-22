#/usr/bin/dev python3i
def encode(data):
  """ Encoder implementation of the Bencode algorithm    

  @param data: The data to encode
  @type data: int, tuple, list, dict or str
      
  @return: The encoded data
  @rtype: str
  """
  i = 0
  if type(data) == int:
    return 'i%de' % data
  elif type(data) == str:
   return '%d:%s'%(len(data),data)
  elif type(data) in (list,tuple):
    encodedListItems = ''
    for item in data:
      encodedListItems += encode(item)
    return 'l%se'%encodedListItems
  elif type(data) == dict:
    encodedDictItems = ''
    keys = list(data.keys())
    keys.sort()
    for key in keys:
      encodedDictItems += encode(key)
      encodedDictItems += encode(data[key])
    return 'd%se'%encodedDictItems
  else:
    raise TypeError("Cannot bencode '%s' object" % type(data))

