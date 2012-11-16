#!/usr/bin/dev python3
# BitClient -- strmanip.py

import string, random

SUFFIXES = {
  1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
  1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
  }

def string_generator(size=20, chars=string.ascii_uppercase + string.digits):
  '''Returns a pseudo-random string of a given size, default 20'''
  return ''.join(random.choice(chars) for x in range(size))

def parse_filesize(size, base=1024):
  '''Given a size and base, parse the size, in bytes, into a human-readable
  string
  (Default base: 1024. Available: 1024, 1000)
  '''
  # essentially, as seen in "Dive into python 3"
  for suffix in SUFFIXES[base]:
    size/=base
    if size < base:
      return '{0:.1f} {1}'.format(size, suffix)

