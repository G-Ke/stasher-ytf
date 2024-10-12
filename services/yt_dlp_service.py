import hashlib
import os

import yt_dlp

class YTDLPService:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

    def download_audio(self, video_url, output_path):
        ydl_opts = {**self.ydl_opts, 'outtmpl': f'{output_path}/%(title)s.%(ext)s'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

    def download_video(self, video_url, output_path):
        ydl_opts = {'outtmpl': f'{output_path}/%(title)s.%(ext)s'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

    def calculate_file_hash(self, file_path):
        hash_md5 = hashlib.md5()
        with open(os.path.normpath(file_path), "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def download_videos(self, video_ids, output_path, audio_only=False, db=None):
        if audio_only:
            self.ydl_opts['format'] = 'bestaudio/best'
            self.ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            self.ydl_opts['format'] = 'bestvideo+bestaudio/best'
            self.ydl_opts['postprocessors'] = []

        self.ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')

        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            for video_id in video_ids:
                try:
                    print(f"Downloading video {video_id}...")
                    info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
                    filename = ydl.prepare_filename(info)
                    file_path = os.path.normpath(os.path.join(filename))
                    
                    # Check for both original and converted file
                    if os.path.exists(file_path):
                        final_file_path = file_path
                    elif audio_only and os.path.exists(os.path.splitext(file_path)[0] + '.mp3'):
                        final_file_path = os.path.splitext(file_path)[0] + '.mp3'
                    else:
                        print(f"File not found after download: {file_path}")
                        return 'file_not_found'
                    
                    file_hash = self.calculate_file_hash(final_file_path)
                    if db:
                        db.add_download(video_id, final_file_path, file_hash)
                    return 'downloaded'
                except yt_dlp.utils.DownloadError as e:
                    print(f"yt-dlp download error for video {video_id}: {str(e)}")
                    return 'download_error'
                except Exception as e:
                    print(f"Unexpected error downloading video {video_id}: {str(e)}")
                    return 'unexpected_error'