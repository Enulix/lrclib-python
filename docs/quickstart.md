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
you should get Never Gonna Give You Up by Rick Astley
but what if we want to _search_ for a song?
## client.search()
the search() method is used to get a list of the best matching song
theres 2 ways to use it
1. search via query `client.search(query)`
2. swarch via title/artist(optional)/album(optional) `client.search(title, artist, album)`
example usage:
```
song_list = client.search("My Way", "Frank Sinatra")

# example: filter out unsynced lyrics
synced_songs = []
for song in song_list:
	# Check if the lyrics are synced
	if song.status == "Synced":
		synced_songs.append(song)
	# do nothing if not
```
