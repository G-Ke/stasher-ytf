from datetime import datetime, timezone
import logging
import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

class YouTubeAPIService:
    def __init__(self, client_secrets_file):
        self.client_secrets_file = client_secrets_file
        self.credentials = None
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.credentials = pickle.load(token)

        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                except Exception as e:  # Catch any exception during refresh
                    logger.warning(f"Token refresh failed: {e}. Re-authenticating...")
                    self.credentials = None  # Reset credentials to force re-authentication
            if not self.credentials:  # If credentials are None or invalid
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                self.credentials = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(self.credentials, token)

        return build('youtube', 'v3', credentials=self.credentials, cache_discovery=False)

    def get_playlist_details(self, playlist_id):
        request = self.youtube.playlists().list(
            part="snippet,contentDetails",
            id=playlist_id
        )
        response = request.execute()

        if 'items' in response and len(response['items']) > 0:
            playlist = response['items'][0]
            return {
                'id': playlist['id'],
                'title': playlist['snippet']['title'],
                'description': playlist['snippet']['description'],
                'channel_id': playlist['snippet']['channelId'],
                'channel_title': playlist['snippet']['channelTitle'],
                'item_count': playlist['contentDetails']['itemCount']
            }
        return None

    def get_playlist_items(self, playlist_id):
        items = []
        next_page_token = None

        while True:
            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                video_id = item['contentDetails']['videoId']
                video_details = self.get_video_details(video_id)
                items.append(video_details)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return items

    def get_video_details(self, video_id):
        request = self.youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response = request.execute()

        if 'items' in response and len(response['items']) > 0:
            video = response['items'][0]
            return {
                'id': video['id'],
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'published_at': datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
                'channel_id': video['snippet']['channelId'],
                'channel_title': video['snippet']['channelTitle'],
                'view_count': int(video['statistics'].get('viewCount', 0)),
                'like_count': int(video['statistics'].get('likeCount', 0)),
                'comment_count': int(video['statistics'].get('commentCount', 0)),
                'duration': video['contentDetails']['duration']
            }
        return None

    def get_playlists(self):
        request = self.youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=100
        )
        response = request.execute()
        return response['items']

    def update_playlist(self, db, playlist_id):
        playlist_details = self.get_playlist_details(playlist_id)
        if playlist_details:
            old_hash = db.get_playlist_hash(playlist_id)
            new_hash = db.update_playlist(
                playlist_id,
                playlist_details['title'],
                playlist_details['description'],
                playlist_details['channel_id'],
                playlist_details['channel_title'],
                playlist_details['item_count']
            )
            return new_hash != old_hash
        return False

    def update_playlist_items(self, db, playlist_id):
        playlist_items = self.get_playlist_items(playlist_id)
        updated_videos = []
        for item in playlist_items:
            if item is None:  # Skip if item is None
                continue
            old_hash = db.get_video_hash(item['id'])
            new_hash = db.update_video(
                item['id'],
                playlist_id,
                item['title'],
                item['description'],
                item['published_at'],
                item['channel_id'],
                item['channel_title'],
                item['view_count'],
                item['like_count'],
                item['comment_count'],
                item['duration']
            )
            if new_hash != old_hash:
                updated_videos.append(item['id'])
        return updated_videos

    def get_playlist_delta(self, db):
        # Get all playlists the user has access to
        channels_request = self.youtube.channels().list(
            part="contentDetails",
            mine=True
        )
        channels_response = channels_request.execute()

        all_playlists = []
        for channel in channels_response['items']:
            playlists_request = self.youtube.playlists().list(
                part="snippet",
                channelId=channel['id'],
                maxResults=200
            )
            while playlists_request:
                playlists_response = playlists_request.execute()
                all_playlists.extend(playlists_response['items'])
                playlists_request = self.youtube.playlists().list_next(playlists_request, playlists_response)

        # Get all playlists in the database
        db_playlists = db.get_all_playlists()

        # Compare and create delta
        unseen_playlists = []
        processed_playlists = []
        unprocessed_playlists = []

        db_playlist_ids = set(p['id'] for p in db_playlists)
        api_playlist_ids = set(p['id'] for p in all_playlists)

        for playlist in all_playlists:
            if playlist['id'] not in db_playlist_ids:
                unseen_playlists.append(playlist)
            else:
                processed_playlists.append(playlist)

        unprocessed_playlists = [p for p in all_playlists if p['id'] not in db_playlist_ids]

        return {
            'all': all_playlists,
            'processed': processed_playlists,
            'unprocessed': unprocessed_playlists
        }

    def get_all_playlist_video_details(self, db, playlist_id):
        # Update the playlist in the database
        playlist_updated = self.update_playlist(db, playlist_id)
        if playlist_updated:
            logger.info(f"Playlist {playlist_id} metadata has been updated.")
        else:
            logger.info(f"No changes detected in playlist {playlist_id} metadata.")

        # Update playlist items and get video details
        updated_videos = self.update_playlist_items(db, playlist_id)
        if updated_videos:
            logger.info(f"Updated {len(updated_videos)} videos in playlist {playlist_id}.")
        else:
            logger.info(f"No changes detected in videos for playlist {playlist_id}.")

        # Get all video details
        videos = []
        playlist_items = self.get_playlist_items(playlist_id)
        for item in playlist_items:
            if item is not None:
                videos.append(item)

        # Update the last_fetched timestamp for the playlist
        db.update_playlist_last_fetched(playlist_id)

        return videos
