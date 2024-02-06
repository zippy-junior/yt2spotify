import spotipy
from spotipy.oauth2 import SpotifyOAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re
from urllib.parse import quote_plus

# Spotify Credentials
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id='',
                                               client_secret='',
                                               redirect_uri='',
                                               scope="playlist-modify-public"))

class YTClient:
    def __init__(self) -> None:
        self.secret = ""
        self.youtube = None
        self.playlists = dict()

    def authenticate_youtube(self):
        # The CLIENT_SECRETS_FILE variable specifies the name of a file that contains the OAuth 2.0 information for this
        # application, including its client_id and client_secret.
        CLIENT_SECRETS_FILE = self.secret
        # This OAuth 2.0 access scope allows for full read/write access to the authenticated
        # user's account and requires requests to use an SSL connection.
        SCOPES = ['https://www.googleapis.com/auth/youtubepartner']
        API_SERVICE_NAME = 'youtube'
        API_VERSION = 'v3'
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        self.youtube = youtube

    def get_playlists(self):
        request = self.youtube.playlists().list(part="snippet", mine=True)
        response = request.execute()

        for item in response["items"]:
            self.playlists[item["snippet"]["title"]] = item["id"]

    def process_song_title(self, song):
        processed = song
        processed = re.sub(r"\(.*\)|\[.*\]", "", processed)
        splitted = processed.split(" - ", 1)
        if len(splitted) > 1:
            return splitted[0], splitted[1]
        else:
            return "", splitted
    
    # Extracts songs from playlist
    def get_playlist_items(self, playlist_id: str):
        all_playlist_items = []
        page_token = None

        while True:
            request = self.youtube.playlistItems().list(
                part="snippet",
                maxResults=50,
                playlistId=playlist_id,
                pageToken=page_token
            )
            response = request.execute()
            for item in response["items"]:
                newSong = dict()
                newSong["artist"], newSong["title"] = self.process_song_title(item["snippet"]["title"])
                newSong["position"] = item["snippet"]["position"]
                all_playlist_items.append(newSong)
            page_token = response.get('nextPageToken')

            if not page_token:
                break

        return all_playlist_items
            
class SpotifyClient:
    def __init__(self, ytclient) -> None:
        self.ytclient = ytclient

    # Converts YouTube songs to Spotify songs
    def get_spotify_uri(self, song_name, artist):
        results = sp.search(q=quote_plus(f"track:{song_name} artist:{artist}"), limit=1)
        if results['tracks']['items']:
            return results['tracks']['items'][0]['uri']

    def sort_songs(self, lst):
        sorted_songs = []
        lst.sort(key=lambda x: x['position'])
        print(lst)
        for song in lst:
            sorted_songs.append(song['uri'])
        return sorted_songs

    def split_list(self, lst):
        for i in range(0, len(lst), 99):
            yield lst[i:i + 99]

    # Transfer the playlist
    def transfer_playlist(self):
        self.ytclient.get_playlists()
        for playlist_name, playlist_id in self.ytclient.playlists.items():
            spotify_uris = []

            for song in self.ytclient.get_playlist_items(playlist_id):
                spotify_song = dict()
                spotify_song["uri"] = self.get_spotify_uri(song['title'], song['artist'])
                if spotify_song.get("uri"):
                    spotify_song['position'] = song['position']
                    spotify_uris.append(spotify_song)
                else:
                    print("NOT FOUND", song['title'], song['artist'])

            # Creating playlist in Spotify
            playlist = sp.user_playlist_create(sp.me()['id'], playlist_name)
            # Adding songs to the playlist
            sorted_songs = self.sort_songs(spotify_uris)
            for sub in self.split_list(sorted_songs):
                sp.playlist_add_items(playlist['id'], sub)

# Use the function
YC = YTClient()
YC.authenticate_youtube()
SC = SpotifyClient(YC)
SC.transfer_playlist()