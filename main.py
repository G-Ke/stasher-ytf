import click
from database.database import Database
from services.youtube_api_service import YouTubeAPIService
from services.yt_dlp_service import YTDLPService
from config import load_config
import os
from datetime import datetime, timedelta
import time

@click.group()
@click.pass_context
def cli(ctx):
    """YTF CLI"""
    if ctx.obj is None:
        ctx.obj = {}
    
    config = load_config()
    client_secrets_file = config['client_secrets_file']

    ctx.obj['db'] = Database("youtube_playlists.db")
    ctx.obj['youtube_api'] = YouTubeAPIService(client_secrets_file)
    ctx.obj['yt_dlp_service'] = YTDLPService()

@cli.command()
@click.option('--playlist-id', prompt='Enter playlist ID', help='ID of the playlist to update')
@click.pass_context
def update_playlist(ctx, playlist_id):
    """Update a single playlist"""
    db = ctx.obj['db']
    youtube_api = ctx.obj['youtube_api']
    
    playlist_updated = youtube_api.update_playlist(db, playlist_id)
    if playlist_updated:
        click.secho(f"Playlist {playlist_id} metadata has been updated.", fg='green')
    else:
        click.secho(f"No changes detected in playlist {playlist_id} metadata.", fg='yellow')

    updated_videos = youtube_api.update_playlist_items(db, playlist_id)
    if updated_videos:
        click.secho(f"Updated {len(updated_videos)} videos in playlist {playlist_id}:", fg='green')
        for video_id in updated_videos:
            click.echo(f"  • {click.style(video_id, fg='cyan')}")
    else:
        click.secho(f"No changes detected in videos for playlist {playlist_id}.", fg='yellow')

    db.update_playlist_last_fetched(playlist_id)
    click.secho(f"Playlist {playlist_id} update process completed.", fg='green', bold=True)

@cli.command()
@click.pass_context
def update_all_playlists(ctx):
    """Update all playlists for a channel"""
    youtube_api = ctx.obj['youtube_api']
    playlists = youtube_api.get_playlists()
    for playlist in playlists:
        playlist_id = playlist['id']
        ctx.invoke(update_playlist, playlist_id=playlist_id)
    click.secho(f"All playlists for your account updated successfully.", fg='green')

@cli.command()
@click.option('--video-url', prompt='Enter video URL', help='URL of the video to stash')
@click.option('--output-path', prompt='Enter output path', default='downloads', help='Path to save the stashed file')
@click.option('--audio-only', is_flag=True, help='Stash audio only')
@click.pass_context
def stash_video(ctx, video_url, output_path, audio_only):
    """Stash a video or its audio"""
    yt_dlp_service = ctx.obj['yt_dlp_service']
    if audio_only:
        yt_dlp_service.download_audio(video_url, output_path)
        click.secho(f"Audio stashed successfully to {output_path}", fg='green')
    else:
        yt_dlp_service.download_video(video_url, output_path)
        click.secho(f"Video stashed successfully to {output_path}", fg='green')

@cli.command()
@click.option('--verbose', is_flag=True, help='Print detailed information about the delta')
@click.option('--save', is_flag=True, help='Save the delta as a job')
@click.pass_context
def check_playlist_delta(ctx, verbose, save):
    """Check for differences between local and remote playlists"""
    db = ctx.obj['db']
    youtube_api = ctx.obj['youtube_api']

    delta = youtube_api.get_playlist_delta(db)

    # Summary
    click.echo(f"All playlists: {len(delta['all'])}")
    click.echo(f"Processed playlists: {len(delta['processed'])}")
    click.echo(f"Unprocessed playlists: {len(delta['unprocessed'])}")

    if verbose:
        click.echo("\All playlists:")
        for playlist in delta['all']:
            click.echo(f"  - {playlist['snippet']['title']} (ID: {playlist['id']})")

        click.echo("\nUnprocessed playlists:")
        for playlist in delta['unprocessed']:
            click.echo(f"  - {playlist['snippet']['title']} (ID: {playlist['id']})")

    if save:
        delta_data = {
            'all': [{'id': p['id'], 'title': p['snippet']['title']} for p in delta['all']],
            'processed': [{'id': p['id'], 'title': p['snippet']['title']} for p in delta['processed']],
            'unprocessed': [{'id': p['id'], 'title': p['snippet']['title']} for p in delta['unprocessed']]
        }
        job_id = db.save_delta_job(delta_data)
        click.echo(f"Delta saved as job ID: {job_id}")

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
    db = ctx.obj['db']
    youtube_api = ctx.obj['youtube_api']
    yt_dlp_service = ctx.obj['yt_dlp_service']

    # Get playlist details
    playlist_details = youtube_api.get_playlist_details(playlist_id)
    if not playlist_details:
        click.secho(f"Playlist with ID {playlist_id} not found.", fg='red', err=True)
        return

    # Prompt user for playlist folder
    use_playlist_folder = click.confirm(click.style(f"Do you want to save files in a folder named '{playlist_details['title']}'?", fg='cyan'), default=True)
    
    if use_playlist_folder:
        # Create a folder with the playlist name
        playlist_folder = os.path.join(output_path, playlist_details['title'])
        os.makedirs(playlist_folder, exist_ok=True)
        output_path = playlist_folder

    audio_only = click.confirm(click.style("Do you want to stash audio only?", fg='cyan'), default=False)

    # Get all video details and update in database
    videos = youtube_api.get_all_playlist_video_details(db, playlist_id)

    # Filter out already stashed videos
    videos_to_download = []
    for video in videos:
        downloaded, file_hash = db.get_video_download_status(video['id'])
        if not downloaded:
            videos_to_download.append(video)
        else:
            click.secho(f"Video {video['id']} already stashed. Skipping.", fg='yellow')

    if not videos_to_download:
        click.secho("All videos in this playlist have already been stashed.", fg='green')
        return

    # Prepare summary
    click.echo("\n" + "=" * 50)
    click.secho("Stash Summary", fg='cyan', bold=True)
    click.echo("=" * 50)
    click.echo(f"Playlist: {click.style(playlist_details['title'], fg='green')}")
    click.echo(f"Number of videos to stash: {click.style(str(len(videos_to_download)), fg='green')}")
    click.echo(f"Output path: {click.style(output_path, fg='green')}")
    click.echo(f"Audio only: {click.style('Yes' if audio_only else 'No', fg='green')}")
    click.echo(f"Batch size: {click.style(str(batch_size), fg='green')}")
    click.echo(f"Delay between batches: {click.style(f'{batch_delay} seconds ({batch_delay / 60:.1f} minutes)', fg='green')}")
    click.echo(f"Summary interval: {click.style(f'{summary_interval} seconds ({summary_interval / 60:.1f} minutes)', fg='green')}")
    click.echo("=" * 50 + "\n")

    # Ask for user consent
    if not click.confirm(click.style("Do you want to proceed with the stashing?", fg='cyan', bold=True)):
        click.secho("Stashing cancelled.", fg='yellow')
        return

    # Prepare batches
    batches = [videos_to_download[i:i + batch_size] for i in range(0, len(videos_to_download), batch_size)]
    click.secho(f"batches {batches}", fg='red', bold=True)

    start_time = datetime.now()
    last_summary_time = start_time
    total_videos = len(videos_to_download)
    downloaded_videos = 0
    skipped_videos = 0

    def print_summary():
        nonlocal downloaded_videos, skipped_videos, start_time, last_summary_time
        elapsed_time = datetime.now() - start_time
        videos_per_hour = (downloaded_videos + skipped_videos) / (elapsed_time.total_seconds() / 3600) if elapsed_time.total_seconds() > 0 else 0
        estimated_completion_time = start_time + (elapsed_time / (downloaded_videos + skipped_videos) * total_videos if (downloaded_videos + skipped_videos) > 0 else timedelta(0))
        last_summary_time = datetime.now()
        
        click.echo("\n" + "=" * 50)
        click.secho("Stashing Progress", fg='cyan', bold=True)
        click.echo("=" * 50)
        click.echo(f"Progress: {click.style(f'{downloaded_videos + skipped_videos}/{total_videos}', fg='green')} videos")
        click.echo(f"Stashed: {click.style(str(downloaded_videos), fg='green')}")
        click.echo(f"Skipped (already present): {click.style(str(skipped_videos), fg='yellow')}")
        click.echo(f"Elapsed time: {click.style(str(elapsed_time), fg='cyan')}")
        click.echo(f"Average speed: {click.style(f'{videos_per_hour:.2f}', fg='cyan')} videos/hour")
        click.echo(f"Estimated completion time: {click.style(str(estimated_completion_time), fg='cyan')}")
        click.echo("=" * 50 + "\n")

    # Download videos in batches
    with click.progressbar(batches, label='Stashing batches', show_eta=False) as bar:
        for i, batch in enumerate(bar):
            click.echo(f"\nProcessing batch {click.style(str(i+1), fg='cyan')} of {click.style(str(len(batches)), fg='cyan')}...")
            
            for video in batch:
                existing_downloads = db.get_downloads_for_video(video['id'])
                if existing_downloads:
                    click.secho(f"Video {video['id']} already exists in the database", fg='yellow')
                    skipped_videos += 1
                    continue
                result = yt_dlp_service.download_videos([video['id']], output_path, audio_only, db)
                if result == 'downloaded':
                    downloaded_videos += 1
                    click.secho(f"Successfully stashed video {video['id']}", fg='green')

                elif result == 'file_not_found':
                    click.secho(f"File not found after stashing for video {video['id']}. This might be due to an issue with file conversion or permissions.", fg='yellow')
                elif result == 'download_error':
                    click.secho(f"yt-dlp stashing error for video {video['id']}. The video might be unavailable or restricted.", fg='red')
                elif result == 'unexpected_error':
                    click.secho(f"Unexpected error stashing video {video['id']}. Please check the logs for more details.", fg='red')

            if i < len(batches) - 1:  # If it's not the last batch
                click.echo(f"Waiting for {click.style(str(batch_delay), fg='cyan')} seconds ({batch_delay / 60:.1f} minutes) before the next batch...")
                
                # Print summary during longer waits
                wait_start = datetime.now()
                while (datetime.now() - wait_start).total_seconds() < batch_delay:
                    time.sleep(min(summary_interval, batch_delay))
                    if (datetime.now() - last_summary_time).total_seconds() >= summary_interval:
                        print_summary()

    click.secho("\nPlaylist stashing completed.", fg='green', bold=True)
    print_summary()

if __name__ == '__main__':
    cli()