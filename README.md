# Stasher YTF CLI

StasherYTF CLI is a command-line interface for managing and stashing YT data. It allows users to stash playlist metadata and more to help them keep track of content they enjoy and learn from.

***This is a work in progress. It is a tool I use, but there are other tools that may be better options for you.***

## Features

- Stashing metadata for a specific playlist.
- Stashing data from a given URL or playlist.
- Check for differences between local and remote playlists.
- Save delta information as a job for future reference.
- Batch stashing data with customizable settings.
- Store stashed metadata in a sqlite database.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your client secrets file as needed.

## Usage

To run the CLI, use the following command:


### Commands

- **Update a Playlist**
  ```bash
  python main.py update-playlist --playlist-id <PLAYLIST_ID>
  ```

- **Update All Playlists**
  ```bash
  python main.py update-all-playlists
  ```

- **Stash a Video**
  ```bash
  python main.py stash-video --video-url <VIDEO_URL> --output-path <OUTPUT_PATH> [--audio-only]
  ```

- **Check Playlist Delta**
  ```bash
  python main.py check-playlist-delta [--verbose] [--save]
  ```

- **Stash a Playlist**
  ```bash
  python main.py stash-playlist --playlist-id <PLAYLIST_ID> --output-path <OUTPUT_PATH> [--audio-only] [--batch-size <BATCH_SIZE>] [--batch-delay <BATCH_DELAY>] [--summary-interval <SUMMARY_INTERVAL>]
  ```

## Configuration

The application requires a configuration file to load client secrets. Ensure that the `client_secrets_file` is correctly set in your configuration.

## Contributing

Feel free to submit issues, but for now, this is a personal project. I recommend forking and modifying to your liking.