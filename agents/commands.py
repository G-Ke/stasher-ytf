from datetime import datetime, timedelta
import time
import click
import os

from database.database import Database
from services.youtube_api_service import YouTubeAPIService
from services.yt_dlp_service import YTDLPService
from config import load_config

class StashVideoTool:
    name = "StashVideoTool"
    description = "This tool stashes a video or its audio from a given URL."

    def __init__(self, yt_dlp_service: YTDLPService):
        self.yt_dlp_service = yt_dlp_service
        self.config = load_config()

    def _run(self, video_url: list[str], output_path: str = None, audio_only: bool = True) -> dict:
        output_path = output_path or self.config.get('default_output_path', 'downloads')
        audio_only = audio_only or self.config.get('default_audio_only', True)
        
        for url in video_url:
            try:
                print(audio_only)
                if audio_only is False:
                    self.yt_dlp_service.download_video(url, output_path)
                else:
                    self.yt_dlp_service.download_audio(url, output_path)
                message = f"Audio stashed successfully to {output_path}"
                return {"success": True, "message": message}
            except Exception as e:
                return {"success": False, "message": f"Error stashing video: {str(e)}"}

class UpdatePlaylistTool:
    name = "UpdatePlaylistTool"
    description = "This tool updates a playlist associated with the user's account. It updates metadata and video items as needed."

    def __init__(self, db: Database, youtube_api: YouTubeAPIService):
        self.db = db
        self.youtube_api = youtube_api

    def _run(self, playlist_id: str) -> dict:
        result = {
            "playlist_updated": False,
            "videos_updated": False,
            "message": []
        }

        playlist_updated = self.youtube_api.update_playlist(self.db, playlist_id)
        if playlist_updated:
            result["playlist_updated"] = True
            result["message"].append(f"Playlist {playlist_id} metadata has been updated.")
        else:
            result["message"].append(f"No changes detected in playlist {playlist_id} metadata.")

        updated_videos = self.youtube_api.update_playlist_items(self.db, playlist_id)
        if updated_videos:
            result["videos_updated"] = True
            result["message"].append(f"Updated {len(updated_videos)} videos in playlist {playlist_id}:")
            for video_id in updated_videos:
                result["message"].append(f"  • {video_id}")
        else:
            result["message"].append(f"No changes detected in videos for playlist {playlist_id}.")

        self.db.update_playlist_last_fetched(playlist_id)
        result["message"].append(f"Playlist {playlist_id} update process completed.")

        return result

def update_playlist_command(obj, playlist_id):
    """Function to update a single playlist"""
    db = obj['db']
    youtube_api = obj['youtube_api']
    # playlist_id = obj['playlist_id']
    # playlist_id = 'PLvdKPgz0vo-t4AN4AuCj9Fo28Flk5Q8ZM'
    
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

def update_all_playlists_command(obj):
    """Function to update all playlists"""
    youtube_api = obj['youtube_api']
    playlists = youtube_api.get_playlists()
    for playlist in playlists:
        playlist_id = playlist['id']
        update_playlist_command(obj, playlist_id)
    click.secho(f"All playlists for your account updated successfully.", fg='green')

def stash_video_command(obj, video_url, output_path, audio_only):
    """Function to stash a video or its audio"""
    yt_dlp_service = obj['yt_dlp_service']
    if audio_only:
        yt_dlp_service.download_audio(video_url, output_path)
        click.secho(f"Audio stashed successfully to {output_path}", fg='green')
    else:
        yt_dlp_service.download_video(video_url, output_path)
        click.secho(f"Video stashed successfully to {output_path}", fg='green')

def check_playlist_delta_command(obj, verbose, save):
    """Function to check playlist delta"""
    db = obj['db']
    youtube_api = obj['youtube_api']

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

def stash_playlist_command(obj, playlist_id, output_path, audio_only, batch_size, batch_delay, summary_interval):
    """Function to stash all videos in a playlist"""
    db = obj['db']
    youtube_api = obj['youtube_api']
    yt_dlp_service = obj['yt_dlp_service']

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