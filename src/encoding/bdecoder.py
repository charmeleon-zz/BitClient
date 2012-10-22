#!/usr/bin/dev python3
# BitClient -- bdecoder2.py
#Author: Erick
#Recursion credit: http://effbot.org/zone/bencode.htm#usage
#10/5/2012: Finished porting to python3k
import re
def atom(text, match=re.compile("([deli])|(\d+):|-?(\d+)").match):
  '''
  A generator for bencoded strings. It provides a single character
  at a time

  '''
  index = 0
  while index<len(text):
    try:
      m = match(text,index)
      s = m.group(m.lastindex)
      index = m.end()
      if m.lastindex==2:  # means we have something before and after : in our string. This will only happen 
        yield "s"         # when we have an integer indicating the length of the next hash, so we indicate that there's a string
        yield text[index:index+int(s)] # and we yield from our current index to the end of the next hash
        index = index+int(s)  # move the index to the end of the upcoming hash
      else:
        yield s
    except TypeError:
      raise TypeError

def decode_singleton(singleton, token):
  '''
  Parse incoming 'singleton' in accordance to its token (integer, list, dictionary and the virtual token 's')
  's' isn't part of the BitTorrent specification, but it is used to distinguish 
  numbers in the encoding which indicate the length of the next hash from actual integers

  '''
  if token=="i":    # integer
    data = int(next(singleton))
    if next(singleton)!="e":
      raise ValueError
  elif token in ("s","\\"):  # string type, virtual 's' token
    data = next(singleton)
  elif token in("l","d"): # lists/dictionaries
    data = []
    tok = next(singleton)
    while tok!="e":
      data.append(decode_singleton(singleton,tok))
      tok = next(singleton)
    if token=="d":
      data=dict(zip(data[0::2],data[1::2]))  # create dictionary from two lists
  else:
    raise ValueError(" for ",token)
  return data

def bdecode(text):
  '''
  Decode bencoded string in accordance to the BitTorrent specification

  '''
  try:
    src = atom(text)
    data = decode_singleton(src,next(src)) # initial call
    for token in src:
      raise SyntaxError("junk")
  except (AttributeError,ValueError,StopIteration) as e:
    raise e
  return data

def decode(text):
  return bdecode(text)

if __name__=="__main__":
  print(bdecode("i3e"))
  print(bdecode('l4:spam4:eggse'))
  print(bdecode("d9:publisher3:bob17:publisher-webpage15:www.example.com18:publisher.location4:homee"))
  print(bdecode("i003e"))
