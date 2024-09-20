import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = 'youtube_playlists.db'

def load_config():
    return {
        'client_secrets_file': 'test_client_secret.json',
    }