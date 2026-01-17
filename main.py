import click

from database.database import Database
from services.youtube_api_service import YouTubeAPIService
from services.yt_dlp_service import YTDLPService
from config import load_config
from agents.commands import (
    update_playlist_command,
    update_all_playlists_command,
    stash_video_command,
    check_playlist_delta_command,
    stash_playlist_command
)

from dotenv import load_dotenv

load_dotenv()


def ensure_authenticated(service, force=False):
    """
    Ensures that the YouTube API service is authenticated.
    If not, it prompts the user for consent before initiating the OAuth flow.
    """
    if not force and service.try_load_credentials():
        return

    click.secho("\nAuthentication Required", fg='yellow', bold=True)
    click.echo("The application needs to access your YouTube account to manage playlists.")
    click.echo("This process will:")
    click.echo("  1. Open a browser window to Google Sign-In.")
    click.echo("  2. Ask you to authorize the application.")
    click.echo("  3. Save a 'token.pickle' file locally for future use.")
    
    if click.confirm("\nDo you want to proceed?", default=True, abort=True):
        click.secho("Initiating authentication flow...", fg='green')
        service.authenticate_interactive()
        click.secho("Authentication successful!", fg='green')

@click.group()
@click.pass_context
def cli(ctx):
    """Stasher Agent CLI"""
    if ctx.obj is None:
        ctx.obj = {}
    
    config = load_config()
    client_secrets_file = config['client_secrets_file']

    ctx.obj['db'] = Database("youtube_playlists.db")
    ctx.obj['youtube_api'] = YouTubeAPIService(client_secrets_file)
    ctx.obj['yt_dlp_service'] = YTDLPService()

@cli.command()
@click.pass_context
def auth(ctx):
    """Authenticate with YouTube API"""
    ensure_authenticated(ctx.obj['youtube_api'], force=True)

@cli.command()
@click.option('--playlist-id', prompt='Enter playlist ID', help='ID of the playlist to update')
@click.pass_context
def update_playlist(ctx, playlist_id):
    """Update a single playlist"""
    ensure_authenticated(ctx.obj['youtube_api'])
    update_playlist_command(ctx.obj, playlist_id)

@cli.command()
@click.pass_context
def update_all_playlists(ctx):
    """Update all playlists for a channel"""
    ensure_authenticated(ctx.obj['youtube_api'])
    update_all_playlists_command(ctx.obj)

@cli.command()
@click.option('--video-url', prompt='Enter video URL', help='URL of the video to stash')
@click.option('--output-path', prompt='Enter output path', default='downloads', help='Path to save the stashed file')
@click.option('--audio-only', is_flag=True, help='Stash audio only')
@click.pass_context
def stash_video(ctx, video_url, output_path, audio_only):
    """Stash a video or its audio"""
    ensure_authenticated(ctx.obj['youtube_api'])
    stash_video_command(ctx.obj, video_url, output_path, audio_only)

@cli.command()
@click.option('--verbose', is_flag=True, help='Print detailed information about the delta')
@click.option('--save', is_flag=True, help='Save the delta as a job')
@click.pass_context
def check_playlist_delta(ctx, verbose, save):
    """Check for differences between local and remote playlists"""
    ensure_authenticated(ctx.obj['youtube_api'])
    check_playlist_delta_command(ctx.obj, verbose, save)

@cli.command()
@click.option('--playlist-id', prompt='Enter playlist ID', help='ID of the playlist to stash')
@click.option('--output-path', prompt='Enter output path', default='downloads', help='Path to save the stashed files')
@click.option('--audio-only', is_flag=True, help='Stash audio only')
@click.option('--batch-size', default=3, show_default=True, help='Number of videos to stash in each batch')
@click.option('--batch-delay', default=1200, show_default=True, help='Delay in seconds between batches')
@click.option('--summary-interval', default=300, show_default=True, help='Interval in seconds between summary prints')
@click.pass_context
def stash_playlist(ctx, playlist_id, output_path, audio_only, batch_size, batch_delay, summary_interval):
    """Stash all videos in a playlist"""
    ensure_authenticated(ctx.obj['youtube_api'])
    stash_playlist_command(ctx.obj, playlist_id, output_path, audio_only, batch_size, batch_delay, summary_interval)

@cli.command()
@click.pass_context
def run_stasher(ctx):
    """Run the interactive mode for command processing"""
    from stasher_interactive import run_stasher
    run_stasher()

@cli.command()
@click.pass_context
def run_stasher_ollama(ctx):
    """Run the interactive mode with Ollama agent"""
    from stasher_interactive import run_stasher_ollama
    run_stasher_ollama()

if __name__ == '__main__':
    cli()