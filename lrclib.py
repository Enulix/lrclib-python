from hashlib import sha256
import requests

# Custom exception
class LrcLibError(Exception):
    pass

# info class, would use dataclass but too lazy to learn
class Song:
    def __init__(self, response):
        self.song_id = response.get('id')
        self.track_name = response.get('trackName')
        self.artist_name = response.get('artistName')
        self.album_name = response.get('albumName')
        self.duration = response.get('duration')
        self.instrumental = response.get('instrumental')
        self.plain_lyrics = response.get('plainLyrics') 
        self.synced_lyrics = response.get('syncedLyrics')

    def __str__(self):
        return f"[SONG] {self.track_name} by {self.artist_name}"

    def __repr__(self):
        return f"[SONG] {self.track_name} by {self.artist_name}"

# Main API
class LrcLibAPI:
    def __init__(self, user_agent = "lrclib-python/1.1b", base_URL = "https://lrclib.net/api"):

        # Setup stuff
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.base_URL = base_URL
        
    def get(self, track_name:str =None, artist_name:str =None, album_name:str =None, duration: int=None, song_id: int=None, cached: bool = False):

        # If a song doesnt have an album its its own album
        if not album_name: album_name = track_name
        # Yes albums are NEEDED, check the docs

        # The caching logic
        endpoint = "get-cached" if cached else "get"
        url = f"{self.base_URL}/{endpoint}"

        # Song id shpuld work instantly
        if song_id:
            request = self.session.get(f"{url}/{song_id}")

        # bit of error stuff handling stuff before doing the GET request
        elif not track_name or not artist_name or not duration:
            raise LrcLibError("Too little arguments")
        else:
            request = self.session.get(url, params={
                'track_name': track_name, 
                'artist_name': artist_name, 
                'album_name': album_name, 
                'duration': duration
            })

        # Fallback cuz the cache endpoint is unreliable
        if request.status_code == 404 and cached:
            print("[WARN] Cached endpoint failed, falling back to normal...")
            endpoint = "get"
            url = f"{self.base_URL}/{endpoint}"
            if song_id:
                request = self.session.get(f"{url}/{song_id}")
            else:
                request = self.session.get(url, params={
                    'track_name': track_name, 
                    'artist_name': artist_name, 
                    'album_name': album_name, 
                    'duration': duration
                })
            
        # Some error handling stuff
        if request.status_code == 404 and song_id:
            raise LrcLibError(f"Song id {song_id} was not found {request.content}")
        elif request.status_code == 404:
            raise LrcLibError(f"Song {track_name} by {artist_name} was not found")
        elif request.status_code == 400:
            raise LrcLibError(f"Bad request: {request.url}")
        elif request.status_code == 429:
            raise LrcLibError("Rate limited")
        request.raise_for_status()

        # Hand the song over to the Song class
        return Song(request.json())

    def search(self, query: str= None, track_name:str =None, artist_name: str =None, album_name: str =None):
        endpoint = "search"
        url = f"{self.base_URL}/{endpoint}"

        # Use query if available
        if query: 
            request = self.session.get(url, params={'q': query})

            # More error handling
            if request.status_code == 404:
                raise LrcLibError(f"{query} was not found")
            elif request.status_code == 400:
                raise LrcLibError(f"Bad request: {request.url}")
            elif request.status_code == 429:
                raise LrcLibError("Rate limited")
            request.raise_for_status()
            return self._json_to_songlist(request.json())

        # Track name is mandatory    
        if not track_name:
            raise LrcLibError("Too little arguments")

        # But its the only mandatory parameter
        params = {'track_name': track_name}
        if artist_name:
            params.update({'artist_name': artist_name})
        if album_name:
            params.update({'album_name': album_name})
        
        request = self.session.get(url, params=params)

        # Usual error handling block
        if request.status_code == 404:
            raise LrcLibError(f"{track_name} was not found")
        elif request.status_code == 400:
            raise LrcLibError(f"Bad request: {request.url}")
        elif request.status_code == 429:
            raise LrcLibError("Rate limited")
        request.raise_for_status()
        return self._json_to_songlist(request.json())

    # Very basic function to make the search results readable
    def _json_to_songlist(self, results):
        songs = []
        for item in results:
            item = Song(item)
            songs.append(item)
        return songs

    # Code to solve nonce challenge and returns token
    def _solve_challenge(self, prefix: str, target: str):
        nonce = 0
        target_bytes = bytes.fromhex(target)

        # This is just a copy of LRCGET's implementation, it works
        while True:
            possible_solution = f"{prefix}{nonce}"
            hash_bytes = sha256(possible_solution.encode('utf-8')).digest()
            if hash_bytes[:-1] <= target_bytes[:-1]:
                return f'{prefix}:{nonce}'
        
            nonce += 1

    # Upload a song
    def publish(self, track_name: str, artist_name: str, album_name: str, duration: int, plain_lyrics: str, synced_lyrics: str):

        # Setup stuff
        endpoint = "publish"
        challenge_endpoint = "request-challenge"

        # Get the challenge
        challenge_request = self.session.post(f"{self.base_URL}/{challenge_endpoint}")
        challenge = challenge_request.json()
        prefix = challenge['prefix']
        target = challenge['target']

        # Do the challenge
        token = self._solve_challenge(prefix, target)
        print(f"Token: {token}") # Debhg stuff
        self.session.headers.update({'X-Publish-Token': token})

        # Prepare to do the upload        
        params = {
            'trackName': track_name,
            'artistName': artist_name,
            'albumName': album_name,
            'duration': duration,
            'plainLyrics': plain_lyrics,
            'syncedLyrics': synced_lyrics
        }

        # A bjt of debug stuff
        # Also .json() has a heart attack which is why im doing it like this
        request = self.session.post(f"{self.base_URL}/{endpoint}", json=params)
        content = request.content
        content = content.decode('utf-8')
        print(content)
        
        # Sucess case
        if request.status_code == 201:
            print("[INFO]Sucessfully uploaded song")
            return "Sucess"
        
        if request.status_code == 400:
            raise LrcLibError(f"Publish token {token} is incorrect")

        request.raise_for_status()

        # If youre still here, something went wrong
        print("[INFO] Execution shouldnt have gone this far")
        print("-"*32)
        print(self.session.header)
        print(f"POST {request.url}")
        print(f"Json body params:\n{params}")
        print(f"-"*32)
        print(f"Response from endpoint:\nCode:{request.status_code}\nJson:{content}")
