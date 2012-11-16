# BitClient - BitTorrent Client written in Python 3.3

BitClient uses only code from the standard python library. I've created it as a way to get familiar with Python and Networking

## Usage
To use, simply call from terminal:
    python3 bitclient.py

The script will look for any .torrent file under the torrents/ folder and begin download

## TODO
### Functional
* Set 'rate' modifier to update only the last line in terminal buffer
* Write pieces directly to file\(s\) \(get rid of .part files\)
* Send Bitfield and have messages
* Accept incoming requests, send pieces as requested
* Implement torrenting Strategies
* Limit Download/Upload speed

### UI
* Turn off logging to buffer \(except critical\)
* Show persistent D/U speed as a single line
