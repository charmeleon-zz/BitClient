#!/usr/bin/dev python3
# BitClient -- bitlog.py
# Personalized implementation for error logging

import logging, inspect, traceback

class log(logging.Logger):
  def __init__(self, tb = ""):
    logging.Logger.__init__(self, "bitclient")
    lh0 = logging.StreamHandler() # loghandler[0]
    lh0.setLevel(logging.CRITICAL)
    self.addHandler(lh0)
    try:
      lh1 = logging.FileHandler("logs/big.log")
    except IOError:
      open("logs/big.log", "w").close()
      lh1 = logging.FileHandler("logs/big.log")
    lh1.setLevel(logging.CRITICAL)
    lh1.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s %(message)s'))
    self.addHandler(lh1)

