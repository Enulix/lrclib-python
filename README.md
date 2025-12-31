# lrclib-python
An extremely basic wrapper for the lrclib api, a lightweight alternative to lrclibapi

## Quickstart
First thing you have to do before anything is initiate the client
```from lrclib import LrclibClient
client = LrclibClient()
```
Basic usage:
```
# Get by id
s = client.get(3657360)

# Get by song signature (title, artist, album, duration)
s = client.get("Never Gonna Give You Up", "Rick Astley", duration = 213)
print(s.song_id) # song's id on lrclib
print(s.status) # can be one of three: "Synced", "Plain", "Instrumental"
print(s.synced_lyrics) # get the synced lyrics
print(s.plain_lyrics) # get the plain lyrics

# get a list of matching songs (title/query, artist, album)
results = client.search("Blur", "Stellar")
print(results[0]) # print the first result
# this can be used in the same way as s was in explaining the .get() method
```
extra docs at [/docs/quickstart.md]
