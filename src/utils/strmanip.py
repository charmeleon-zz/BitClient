#!/usr/bin/dev python3
# BitClient -- strmanip.py

import string, random

def string_generator(size=20, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for x in range(size))

