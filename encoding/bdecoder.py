#!/usr/bin/env python3
import sys
import re

class decoder(object):
  def __init__(self):
    pass

  def decode(self,enc_string):
    '''
    This is the single method needed to decode a bencoded string.

    '''
    enc_string_type = self.__sort(enc_string)
    if(enc_string_type=="dictionary"):
      decoded = self.__decodeDictionary(enc_string)
    elif(enc_string_type=="list"):
      decoded = self.__decodeList(enc_string)
    elif(enc_string_type=="integer"):
      decoded = self.__decodeInteger(enc_string)
    print(enc_string_type)

  def __sort(self,enc_string):
    '''
    Sort an encoded string to user the proper decoding algorithm
    aka: dictionary/list/integer

    '''
    if(isinstance(enc_string,str)): # verify that a string was passed
      patterns = {'integer'   :'^i.+e$',
                  'list'      :'^l.+e$',
                  'dictionary':'^d.+e$'}
      for name in patterns:
        if(re.search(patterns[name],enc_string)):
          return name
      raise Exception("attempted to decoded a non-bencoded string")
    else:
      raise Exception("bdecoder can only decode bencoded strings, and no other objects")
  def __decodeDictionary(self,enc_string):
    '''
    Decode a bencoded dictionary

    '''
    item = {}
  def __decodeList(self,enc_string):
    '''
    Decode a bencoded list

    '''
    item = []  
  def __decodeInteger(self,enc_string):
    '''
    Decode a bencoded integer

    ''' 
    pattern = '-?\d+'
    num = int(re.search(pattern,enc_string).group(0))
    print(num)
    return num

  def tokenize(self,text, match=re.compile("([idel])|(\d+):|(-?\d+)").match):
    i = 0
    while i < len(text):
        m = match(text, i)
        print(m.lastindex)
        s = m.group(m.lastindex)
        i = m.end()
        if m.lastindex == 2:
            yield "s"
            yield text[i:i+int(s)]
            i = i + int(s)
        else:
          print(s)
          yield s

if __name__=='__main__':
  text_string = "i-343e"
  bd = decoder()

  src = bd.tokenize(text_string)
#  print(src.next)
#  print(src.next())
  #data = decode_item(src.next, src.next())
  #for token in src: # look for more tokens
  #  raise SyntaxError("trailing junk")
  #except (AttributeError, ValueError, StopIteration):
  #  raise SyntaxError("syntax error")
  #return data
  bd.tokenize(text_string)
  bd.decode(text_string) #integer test
