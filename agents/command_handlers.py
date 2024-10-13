import click
import logging

from typing import List, Dict

logger = logging.getLogger(__name__)

def update_playlist_handler(parameters: Dict, tools: List[callable]) -> str:
    update_playlist_tool = next((tool for tool in tools if tool.name == "UpdatePlaylistTool"), None)
    if update_playlist_tool and 'playlist_id' in parameters:
        result = update_playlist_tool._run(parameters['playlist_id'])
        output = "\n".join(result["message"])
        if result["playlist_updated"] or result["videos_updated"]:
            output = click.style(output, fg='green')
        else:
            output = click.style(output, fg='yellow')
        return output
    else:
        return "Error: UpdatePlaylistTool not found or playlist_id not provided."

def update_all_playlists_handler(parameters: Dict, tools: List[callable]) -> str:
    update_all_playlists_tool = next((tool for tool in tools if tool.name == "UpdateAllPlaylistsTool"), None)
    if update_all_playlists_tool:
        result = update_all_playlists_tool._run()
        output = "\n".join(result["message"])
        if result["playlists_updated"] or result["videos_updated"]:
            output = click.style(output, fg='green')
        else:
            output = click.style(output, fg='yellow')
        return output
    else:
        return "Error: UpdateAllPlaylistsTool not found."

def stash_video_handler(parameters: Dict, tools: List[callable]) -> str:
    logger.info(f"Stash video handler called with parameters: {parameters}")
    logger.info(f"Available tools: {[tool.name for tool in tools]}")
    
    stash_video_tool = next((tool for tool in tools if tool.name == "StashVideoTool"), None)
    
    # Check for video_url, url, video_ids, or videos in parameters
    video_inputs = parameters.get('video_ids') or parameters.get('videos') or [parameters.get('url') or parameters.get('video_urls')]
    
    # Flatten the list of lists into a single list
    if isinstance(video_inputs, list):
        video_inputs = [item for sublist in video_inputs for item in (sublist if isinstance(sublist, list) else [sublist])]
    
    if not isinstance(video_inputs, list):
        video_inputs = [video_inputs]
    
    video_urls = []
    for video_input in video_inputs:
        if video_input:
            if len(video_input) == 11 and video_input.isalnum():
                # Likely a YouTube video ID, construct full URL
                video_urls.append(f"https://www.youtube.com/watch?v={video_input}")
            else:
                # Assume it's already a full URL
                video_urls.append(video_input)
    
    if stash_video_tool is None:
        logger.error("StashVideoTool not found in available tools")
        return "Error: StashVideoTool not found in available tools."
    
    if not video_urls:
        logger.error("No valid video URLs or IDs provided in parameters")
        return "Error: No valid video URLs or IDs provided."
    
    results = []
    for video_url in video_urls:
        try:
            result = stash_video_tool._run(video_url=[video_url], output_path=parameters.get('output_path', 'downloads'), audio_only=parameters.get('audio_only', False))
            if result['success']:
                results.append(f"Successfully stashed video: {video_url}")
            else:
                results.append(f"Failed to stash video {video_url}: {result['message']}")
        except Exception as e:
            results.append(f"Failed to stash video {video_url}: {str(e)}")
    
    return "\n".join(results)

def check_playlist_delta_handler(parameters: Dict, tools: List[callable]) -> str:
    # Implement check playlist delta logic here
    return "Checking playlist delta..."
