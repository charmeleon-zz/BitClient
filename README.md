# BitClient - BitTorrent Client written in Python 3.3

BitClient is a lightweight BitTorrent client that only uses code from the
standard p3k library.

I created it to get familiar with Python, Networking, and writing code by
following a specification.

## Requirements
Minimum: Python 3.3.0
Tested only under GNU/Linux

## Usage
To use, simply call from terminal:

    python3 bitclient.py

The script will look for any .torrent file under the torrents/ folder and begin
download

## TODO
### Functional
* ~~Set 'rate' modifier to update only the last line in terminal buffer~~
* ~~Write pieces directly to file\(s\) \(get rid of .part files\)~~
* Fix CPU usage from asyncore.loop call
* Add a task manager
* Send Bitfield and have messages
* Accept incoming requests, send pieces as requested
* Better multi-torrent support
* Magnet links support
* Implement torrenting Strategies
* Limit Download/Upload speed

### UI
* ~~Turn off logging to buffer \(except critical\)~~
* ~~Show persistent D/U speed as a single line~~
