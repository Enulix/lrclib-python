# Quickstart
## The basics
to do anything you need a client
```
from lrclib import LrclibClient

client = LrclibClient()
```
So, how do we use it?
## client.get()
the get() method can be used to get songs directly in 2 ways:
1. through the id on lrclib `client.get(12345)`
2. through the song's signature `client.get(title, artist, album, duration)`
example usage:
```
song = client.get("Never Gonna Give You Up", "Rick Astley", duration = 213)
print(song)
```
you should get `Never Gonna Give You Up by Rick Astley`
but what if we want to search for a song?
# Placeholder
