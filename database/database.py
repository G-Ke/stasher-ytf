import sqlite3
from datetime import datetime
import hashlib
import json

class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                channel_id TEXT,
                channel_title TEXT,
                item_count INTEGER,
                last_updated TIMESTAMP,
                last_fetched TIMESTAMP,
                content_hash TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                playlist_id TEXT,
                title TEXT,
                description TEXT,
                published_at TIMESTAMP,
                channel_id TEXT,
                channel_title TEXT,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                duration TEXT,
                last_updated TIMESTAMP,
                content_hash TEXT,
                downloaded BOOLEAN DEFAULT 0,
                file_hash TEXT,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS delta_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                content_hash TEXT,
                delta_data JSON
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                file_path TEXT,
                file_hash TEXT,
                download_date TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (id)
            )
        ''')
        self.conn.commit()

    def generate_hash(self, data):
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def update_playlist(self, playlist_id, title, description, channel_id, channel_title, item_count):
        data = {
            'title': title,
            'description': description,
            'channel_id': channel_id,
            'channel_title': channel_title,
            'item_count': item_count
        }
        content_hash = self.generate_hash(data)
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO playlists (id, title, description, channel_id, channel_title, item_count, last_updated, last_fetched, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (playlist_id, title, description, channel_id, channel_title, item_count, datetime.now(), datetime.now(), content_hash))
        self.conn.commit()
        return content_hash

    def update_video(self, video_id, playlist_id, title, description, published_at, channel_id, channel_title, view_count, like_count, comment_count, duration):
        data = {
            'title': title,
            'description': description,
            'published_at': published_at.isoformat(),
            'channel_id': channel_id,
            'channel_title': channel_title,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'duration': duration
        }
        content_hash = self.generate_hash(data)
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO videos (id, playlist_id, title, description, published_at, channel_id, channel_title, view_count, like_count, comment_count, duration, last_updated, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (video_id, playlist_id, title, description, published_at, channel_id, channel_title, view_count, like_count, comment_count, duration, datetime.now(), content_hash))
        self.conn.commit()
        return content_hash

    def update_video_download_status(self, video_id, downloaded, file_hash):
        self.cursor.execute('''
            UPDATE videos
            SET downloaded = ?, file_hash = ?
            WHERE id = ?
        ''', (downloaded, file_hash, video_id))
        self.conn.commit()

    def get_playlist_last_updated(self, playlist_id):
        self.cursor.execute('SELECT last_updated FROM playlists WHERE id = ?', (playlist_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_playlist_last_fetched(self, playlist_id):
        self.cursor.execute('SELECT last_fetched FROM playlists WHERE id = ?', (playlist_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def update_playlist_last_fetched(self, playlist_id):
        self.cursor.execute('UPDATE playlists SET last_fetched = ? WHERE id = ?', (datetime.now(), playlist_id))
        self.conn.commit()

    def get_playlist_hash(self, playlist_id):
        self.cursor.execute('SELECT content_hash FROM playlists WHERE id = ?', (playlist_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_video_hash(self, video_id):
        self.cursor.execute('SELECT content_hash FROM videos WHERE id = ?', (video_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_video_download_status(self, video_id):
        self.cursor.execute('SELECT downloaded, file_hash FROM videos WHERE id = ?', (video_id,))
        result = self.cursor.fetchone()
        return result if result else (False, None)

    def get_video_by_file_hash(self, file_hash):
        self.cursor.execute('SELECT id FROM videos WHERE file_hash = ?', (file_hash,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_playlists(self):
        self.cursor.execute('SELECT id, title, description FROM playlists')
        return [{'id': row[0], 'title': row[1], 'description': row[2]} for row in self.cursor.fetchall()]

    def save_delta_job(self, delta_data):
        timestamp = datetime.now().isoformat()
        content_hash = self.generate_hash(delta_data)
        delta_json = json.dumps(delta_data)

        self.cursor.execute('''
            INSERT INTO delta_jobs (timestamp, content_hash, delta_data)
            VALUES (?, ?, ?)
        ''', (timestamp, content_hash, delta_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_delta_job(self, job_id):
        self.cursor.execute('SELECT * FROM delta_jobs WHERE id = ?', (job_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'timestamp': result[1],
                'content_hash': result[2],
                'delta_data': json.loads(result[3])
            }
        return None

    def get_latest_delta_job(self):
        self.cursor.execute('SELECT * FROM delta_jobs ORDER BY id DESC LIMIT 1')
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'timestamp': result[1],
                'content_hash': result[2],
                'delta_data': json.loads(result[3])
            }
        return None

    def add_download(self, video_id, file_path, file_hash):
        self.cursor.execute('''
            INSERT INTO downloads (video_id, file_path, file_hash, download_date)
            VALUES (?, ?, ?, ?)
        ''', (video_id, file_path, file_hash, datetime.now()))
        self.conn.commit()

    def get_download_by_file_hash(self, file_hash):
        self.cursor.execute('''
            SELECT d.*, v.title, v.channel_title
            FROM downloads d
            LEFT JOIN videos v ON d.video_id = v.id
            WHERE d.file_hash = ?
        ''', (file_hash,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'video_id': result[1],
                'file_path': result[2],
                'file_hash': result[3],
                'download_date': result[4],
                'video_title': result[5],
                'channel_title': result[6]
            }
        return None

    def get_downloads_for_video(self, video_id):
        self.cursor.execute('SELECT * FROM downloads WHERE video_id = ?', (video_id,))
        return self.cursor.fetchall()
