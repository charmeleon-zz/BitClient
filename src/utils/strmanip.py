#!/usr/bin/dev python3
# BitClient -- strmanip.py

import string, random

def Hexify(any_string):
  '''Convert a string element to a string of hexadecimal values'''
  empty_list = []
  for c in any_string:
    empty_list.append("\\"+hex(c))
  return ''.join(empty_list)

def string_generator(size=20, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for x in range(size))

