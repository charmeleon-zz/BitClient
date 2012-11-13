#!/bin/src/dev python3
# BitClient -- file.py
# A wrapper file object to conduct file IO

import os

#READONLY = 1
#WRITEONLY = 2
#READWRITE = 3

class File(object):
  READONLY = 1
  WRITEONLY = 2
  READWRITE = 3
  def __init__(self, name, mode = 3):
    self.name = name
    if mode == File.READWRITE:
      self.mode = os.O_RDWR|os.O_CREAT
    elif mode == File.WRITEONLY:
      self.mode = os.O_WRONLY|os.O_CREAT
    elif mode == File.READONLY:
      self.mode = os.O_RDONLY|os.O_CREAT
    self.fobj = os.open(name, self.mode)
    print("Opened file %s" % name)

  def insert_at(self, startpos, data):
    if isinstance(data, str):
      data = bytes(data, "UTF-8")
    os.lseek(self.fobj, startpos, os.SEEK_SET)
    os.write(self.fobj, data)

  def read_from(self, startpos, num):
    os.lseek(self.fobj, startpos, os.SEEK_SET)
    return os.read(self.fobj, num)

  def read(self):
    return open(self.name).read()

  def close(self):
    os.close(self.fobj)

