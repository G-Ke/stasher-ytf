# Stasher Agent

Stasher Agent is a command-line interface and AI Agent for managing and stashing video content metadata. Interact with an LLM in natural language to perform tasks like updating playlist metadata, stashing files, and more.

The tool includes interactive Agent mode, as well standard CLI commands. The agent mode can utilize a Together API key or a local model via Ollama.

***This is a work in progress. It is a tool I use, but there are other tools that may be better options for you.***

## Features

- Stashing metadata for a specific playlist.
- Stashing data from a given URL or playlist.
- Check for differences between local and remote playlists.
- Save delta information as a job for future reference.
- Batch stashing data with customizable settings.
- Store stashed metadata in a sqlite database.

## Prerequisites

- **Python 3.10+**
- **FFmpeg**: Required for audio processing and format conversion.
  - Windows: `winget install Gyan.FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

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

3. Configure your environment:
   - Copy `test_client_secret.json` or your downloaded OAuth credentials to the project root.
   - Create a `.env` file (optional) to specify the secrets file location:
     ```env
     CLIENT_SECRETS_FILE=client_secrets.json
     ```
   - (Optional) Customize behavior in `controls.toml`.

## Usage

To run the CLI, use the following command:


### Commands

- **Authentication**
  ```bash
  python main.py auth
  ```
  *Initiates the OAuth flow to grant the application access to your YouTube account.*

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

- **Enter Agent Mode (Cloud)**
  *Uses TogetherAI (requires API key).*
```bash
python main.py run-stasher

> update playlist IfEY5_NB6is
> update all of my playlists please
> stash video IfEY5_NB6is
```

- **Enter Agent Mode (Local)**
  *Uses a local Ollama instance (requires Ollama installed and running).*
```bash
python main.py run-stasher-ollama

> update playlist IfEY5_NB6is
> update all of my playlists please
> stash video IfEY5_NB6is
```

## Configuration

## Configuration

The application uses a hierarchy for configuration:
1. **Environment Variables**: Defined in `.env` (e.g., `CLIENT_SECRETS_FILE`).
2. **Configuration File**: `controls.toml` for default settings.

Ensure `client_secrets_file` points to a valid Google OAuth Client ID JSON file.

## Contributing

Feel free to submit issues, but for now, this is a personal project. I recommend forking and modifying to your liking.