import os
import toml
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = 'youtube_playlists.db'

def load_config():
    # Load environment variables
    env_config = {
        'client_secrets_file': os.getenv('CLIENT_SECRETS_FILE', 'test_client_secret.json'),
    }

    # Load TOML configuration
    toml_config = {}
    if os.path.exists('controls.toml'):
        toml_config = toml.load('controls.toml')

    # Merge configurations, giving precedence to environment variables
    config = {**toml_config.get('default', {}), **env_config}
    return config