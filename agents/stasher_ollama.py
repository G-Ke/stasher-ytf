import json
import logging
from typing import List, Dict

from litellm import completion

from agents.commands import UpdatePlaylistTool, UpdateAllPlaylistsTool, StashVideoTool
from config import load_config
from database.database import Database
from agents.command_handlers import update_playlist_handler, stash_video_handler, check_playlist_delta_handler, update_all_playlists_handler
from services.youtube_api_service import YouTubeAPIService
from services.yt_dlp_service import YTDLPService

logger = logging.getLogger(__name__)

class StasherOllama:
    def __init__(self, ytf_cli_path=None):
        self.config = load_config()
        self.config['model'] = "ollama/Qwen3:4b"
        self.command_registry = {}
        self._youtube_api = None
        self.initialize_tools()
        self.register_commands()

    @property
    def youtube_api(self):
        if self._youtube_api is None:
            self._youtube_api = YouTubeAPIService(self.config['client_secrets_file'])
        return self._youtube_api

    def initialize_tools(self):
        self.model = self.config['model']
        self.db = Database(self.config['database_path'])
        self.yt_dlp_service = YTDLPService()
        update_playlist_tool = UpdatePlaylistTool(self.db, self.youtube_api)
        update_all_playlists_tool = UpdateAllPlaylistsTool(self.db, self.youtube_api)
        stash_video_tool = StashVideoTool(self.yt_dlp_service)
        self.tools = [update_playlist_tool, stash_video_tool, update_all_playlists_tool]

    def register_commands(self):
        self.register_command("update_playlist", update_playlist_handler)
        self.register_command("stash_video", stash_video_handler)
        self.register_command("check_playlist_delta", check_playlist_delta_handler)
        self.register_command("update_all_playlists", update_all_playlists_handler)

    def register_command(self, command_name, handler):
        self.command_registry[command_name] = handler

    def handle_user_input(self, user_input):
        command_plan = self.plan_command(user_input)
        if not command_plan:
             return "Failed to plan command."
             
        command = command_plan.get("command")
        parameters = command_plan.get("parameters", {})
        handler = self.command_registry.get(command)
        if handler:
            result = handler(parameters, self.tools)
            return self.parse_output(result)
        else:
            return f"Unknown command: {command}"

    def plan_command(self, user_input):
        prompt = f"""
        Given the user input: "{user_input}"
        Important!: You are the Stasher agent, an AI designed to determine the appropriate command and parameters.
        
        Available commands:
        1. update_playlist - Update playlist metadata.
        2. update_all_playlists - Update all playlists.
        3. stash_video  - Stash a video/audio given a URL or ID.

        Return ONLY a JSON object with this schema:
        {{
            "command": "command_name",
            "parameters": {{
                "param1": "value1"
            }}
        }}

        Examples:
        Input: "stash dQw4w9WgXcQ"
        Output:
        {{
            "command": "stash_video",
            "parameters": {{
                "video_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                "output_path": "downloads",
                "audio_only": false
            }}
        }}

        Input: "update all playlists"
        Output:
        {{
            "command": "update_all_playlists",
            "parameters": {{}}
        }}
        """
        
        response = self.get_llm_response(prompt)
        logger.info(f"Raw LLM Response: {response}")
        return self.parse_llm_response(response)

    def get_llm_response(self, prompt):
        # litellm handles ollama calls. Ensure base_url is set if not default.
        # usually http://localhost:11434
        response = completion(
            model=self.model, 
            messages=[{"role": "user", "content": prompt}],
            api_base="http://localhost:11434"
        )
        return response.choices[0].message.content

    def parse_output(self, output):
        if isinstance(output, str):
            return output
        else:
            return str(output)

    def parse_llm_response(self, response: str) -> Dict:
        print(f"Debug Raw Response: {response}")
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            parsed = json.loads(clean_response)
            
            # Normalize parameters
            if parsed.get('command') == 'stash_video':
                if 'video_ids' in parsed.get('parameters', {}):
                    parsed['parameters']['videos'] = parsed['parameters'].pop('video_ids')
                elif 'video_id' in parsed.get('parameters', {}):
                    parsed['parameters']['videos'] = [parsed['parameters'].pop('video_id')]
                elif 'video_urls' in parsed.get('parameters', {}):
                     if isinstance(parsed['parameters']['video_urls'], str):
                        parsed['parameters']['videos'] = [parsed['parameters']['video_urls']]
                     else:
                        parsed['parameters']['videos'] = parsed['parameters']['video_urls']
            
            return parsed
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {}

if __name__ == '__main__':
    agent = StasherOllama()
    print(f"StasherOllama initialized with model: {agent.model}")
    while True:
        try:
            user_input = input("Enter your command (or 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            result = agent.handle_user_input(user_input)
            print(result)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
