from .base import BaseCommand
import click

class UpdatePlaylistCommand(BaseCommand):
    name = "update_playlist"
    description = "Update a playlist"

    @classmethod
    def add_cli_parameters(cls, cli_command):
        cli_command.click.option("--playlist-id", type=str, help="The ID of the playlist to update")
        return cli_command
    
    def execute(self, obj, parameters: dict, context: dict):
        playlist_id = parameters.get("playlist_id")
        db = obj['db']
        youtube_api = obj['youtube_api']

        playlist_update = youtube_api.get_playlist_details(db, playlist_id)
        if playlist_update:
            return f"Playlist {playlist_id} metadata updated"
        else:
            return f"No changes to playlist {playlist_id} detected"
