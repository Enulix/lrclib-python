from hashlib import sha256
import threading
import requests
import time


class LrcLibError(Exception):
    """Base exception for all the other exceptions"""

    pass


class InvalidArguments(LrcLibError):
    """Arguments are invalid"""

    pass


class NotFound(LrcLibError):
    """Song was not found"""

    pass


class RateLimited(LrcLibError):
    """Exceeded API's rate limit"""

    pass


class IncorrectToken(LrcLibError):
    """The provided publish token is incorrect"""

    pass


class BadRequest(LrcLibError):
    """Request was rejected"""

    pass


class ChallengeTimeout(LrcLibError):
    """Solver took too long, prefix and target are expired"""

    pass


def solve_challenge(prefix: str, target: str, timeout: int = 280) -> str:
    """
    Solve the nonce challenge fom the challenge endpoint

    Args:
        prefix: Prefix given by endpoint (str)
        target: Target given by endpoint (str)
        timeout: Timeout in seconds (int)

    Returns:
        Token (str)

    Raises:
        ChallengeTimeout: Solve took too long
    """
    target = int(target, 16).to_bytes(32, "big")
    start = time.monotonic()
    prefix = prefix.encode()
    buf = bytearray(prefix)
    start_len = len(prefix)
    nonce = 0

    while time.monotonic() - start < timeout:
        buf[start_len:] = str(nonce).encode()
        if sha256(buf).digest() <= target:
            return f"{prefix.decode()}:{nonce}"
        nonce += 1

    raise ChallengeTimeout(
        f"Solver timeout after {round(time.monotonic() - start, 2)}s"
    )


class Song:
    def __init__(self, response):
        self.song_id = response.get("id")
        self.track_name = response.get("trackName")
        self.artist_name = response.get("artistName")
        self.album_name = response.get("albumName")
        self.duration = response.get("duration")
        self.instrumental = response.get("instrumental")
        self.plain_lyrics = response.get("plainLyrics")
        self.synced_lyrics = response.get("syncedLyrics")
        self.lyrics = self.synced_lyrics or self.plain_lyrics

    @property
    def status(self):
        if self.instrumental:
            return "Instrumental"
        elif self.synced_lyrics:
            return "Synced"
        elif self.plain_lyrics:
            return "Plain"
        else:
            return "Unknown"

    def __str__(self):
        return f"{self.track_name} by {self.artist_name} ({self.status})"

    def __repr__(self):
        if self.album_name:
            return f"[{self.song_id}] {self.track_name} by {self.artist_name} in album {self.album_name} ({self.status}){f' [{self.duration}]' if self.duration else ""}"
        else:
            return f"[{self.song_id}] {self.track_name} by {self.artist_name} ({self.status}){f' [{self.duration}]' if self.duration else ""}"

    def __eq__(self, other):
        if not isinstance(other, Song):
            return NotImplemented

        if self.song_id == other.song_id and (self.song_id and other.song_id):
            return True

        durch = False
        if isinstance(self.duration, int) and isinstance(other.duration, int):
            durch = abs(self.duration - other.duration) <= 5

        checks = [
            self.track_name == other.track_name,
            self.artist_name == other.artist_name,
            self.album_name == other.album_name,
            self.instrumental == other.instrumental,
        ]
        matches = sum(1 for check in checks if check) + (1 if durch else 0)
        return matches >= 3


class LrclibClient:
    def __init__(
        self,
        user_agent: str = "lrclib-python/0.4",
        base_url: str = "https://lrclib.net/api",
    ):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.base_url = base_url
        self.timeout = 300
        self._token = None
        self._tk_time = 0
        self._tk_lock = threading.Lock()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.session.close()

    def get_token(self, force=False):
        with self._tk_lock:
            if (
                (not self._token)
                or ((time.monotonic() - self._tk_time) > self.timeout)
                or force
            ):
                challenge_endpoint = "request-challenge"
                challenge_request = self.session.post(
                    f"{self.base_url}/{challenge_endpoint}"
                )
                challenge = challenge_request.json()
                prefix = challenge["prefix"]
                target = challenge["target"]
                self._token = solve_challenge(prefix, target, self.timeout)
                self._tk_time = time.monotonic()
                return self._token
            else:
                return self._token

    def get(
        self,
        id_name: int | str,
        artist_name: str = None,
        album_name: str = None,
        duration: int = None,
        cached: bool = False,
    ) -> Song:
        """
        Get a song directly via the ID or the metadata

        Args:
            id_name: Song ID (int) or track name (str)
            artist_name: Name of Artist
            album_name: Name of Album
            duration: Duration in seconds (int)
            cached: Use cached endpoint (bool)

        Returns:
            Song: Song object with lyrics and metadata

        Raises:
            InvalidArguments: Unexpected arguments
            NotFound: Fetching directly failed
            BadRequest: A bad request was sent
            RateLimited: Exceeded the API's rate limit
        """

        song_id = None
        track_name = None
        if not (artist_name or album_name or duration):
            try:
                song_id = int(id_name)
            except Exception as e:
                raise InvalidArguments(f"ID must be an int\n{e}")
        else:
            track_name = id_name

        endpoint = "get-cached" if cached else "get"
        url = f"{self.base_url}/{endpoint}"

        if song_id:
            request = self.session.get(f"{url}/{song_id}")

        else:
            request = self.session.get(
                url,
                params={
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "album_name": album_name,
                    "duration": duration,
                },
            )

        if request.status_code == 404 and cached:
            return self.get(
                track_name, artist_name, album_name, duration, cached=False
            )

        if request.status_code == 404 and song_id:
            raise NotFound(f"Song id {song_id} was not found {request.text}")
        elif request.status_code == 404:
            raise NotFound(f"Song {track_name} by {artist_name} was not found")
        elif request.status_code == 400:
            raise BadRequest(f"Bad request: {request.url}")
        elif request.status_code == 429:
            raise RateLimited("Exceeded the Lrclib API rate limit")
        request.raise_for_status()
        return Song(request.json())

    def search(
        self, track_query: str,
        artist_name: str = None,
        album_name: str = None
    ) -> list:
        """
        Search a song either via query or name/artist/album

        Args:
            track_query: Query (str) or the track title (str)
            artist_name: Name of the artist (str)
            album_name: Name of the album (str)

        Returns:
            list of Song objects

        Raises:
            BadRequest: A bad request was sent
            RateLimited: The server rate limited this session
        """

        endpoint = "search"
        url = f"{self.base_url}/{endpoint}"

        if not (artist_name or album_name):
            query = track_query
        else:
            track_name = track_query
            query = None

        if query:
            request = self.session.get(url, params={"q": query})
            if request.status_code == 400:
                raise BadRequest(f"Bad request: {request.url}")
            elif request.status_code == 429:
                raise RateLimited("Exceeded the Lrclib API rate limit")
            request.raise_for_status()
            return [Song(item) for item in request.json()]
        if not track_name:
            raise InvalidArguments("Too little arguments")

        params = {"track_name": track_name}
        if artist_name:
            params.update({"artist_name": artist_name})
        if album_name:
            params.update({"album_name": album_name})
        request = self.session.get(url, params=params)

        if request.status_code == 400:
            raise BadRequest(f"Bad request: {request.url}")
        elif request.status_code == 429:
            raise RateLimited("Exceeded the Lrclib API rate limit")
        request.raise_for_status()
        return [Song(item) for item in request.json()]

    def publish(self, data: dict) -> bool:
        """
        Publishes a song to LrcLib

        Args:
            A dict containing:
                track_name: Name of the song (str)
                artist_name: Name of the artist (str)
                album_name: Name of the album (str)
                duration: Duration of the song in seconds (int)
                plain_lyrics: Lyrics of the song in Plaintext (str)
                synced_lyrics: Times lyrics of the song in the lrc format (str)

        Returns:
            True

        raises:
            IncorrectToken: Token was rejected
            RateLimited: The server rate limited this session
        """
        track_name = data["track_name"]
        artist_name = data["artist_name"]
        album_name = data["album_name"]
        duration = data["duration"]
        synced_lyrics = data.get("synced_lyrics")
        plain_lyrics = data.get("plain_lyrics")

        try:
            duration = int(duration)
        except Exception:
            raise InvalidArguments("Duration must be in seconds and an int")

        endpoint = "publish"
        token = self.get_token()
        headers = {"X-Publish-Token": token}
        params = {
            "trackName": track_name,
            "artistName": artist_name,
            "albumName": album_name,
            "duration": duration,
        }
        if synced_lyrics:
            params["syncedLyrics"] = synced_lyrics
        if plain_lyrics:
            params["plainLyrics"] = plain_lyrics
        request = self.session.post(
            f"{self.base_url}/{endpoint}", json=params, headers=headers
        )

        if request.status_code == 201:
            return True
        if request.status_code == 400:
            if request.json()['name'] == "IncorrectPublishTokenError":
                self._token = None
                raise IncorrectToken(f"Publish token {token} was rejected")
            raise BadRequest("Request was rejected")
        if request.status_code == 429:
            raise RateLimited("Rate Limited")
        request.raise_for_status()
