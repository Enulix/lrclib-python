from lrclib import LrclibClient, Song, solve_challenge

# This tests all of lrclib's fucntionality
client = LrclibClient()

help(solve_challenge)

get_case = client.get(12345)
if isinstance(get_case, Song) and get_case.synced_lyrics:
    print("test 1 passed")
else:
    print("test 1 failed")

search_case = client.search("Cuphead Rap", "JT Music")
if isinstance(search_case, list):
    print("test 2 passed")
else:
    print("test 2 failed")

publish_case = client.publish(
    {
        "track_name": get_case.track_name,
        "artist_name": get_case.artist_name,
        "album_name": get_case.album_name,
        "duration": get_case.duration,
        "synced_lyrics": get_case.synced_lyrics,
        "plain_lyrics": get_case.plain_lyrics
    }
)
if publish_case:
    print("test 3 passed")
else:
    print("test 3 failed")
