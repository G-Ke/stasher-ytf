import json
import logging
from typing import List, Dict

from litellm import completion

from agents.commands import UpdatePlaylistTool, StashVideoTool
from config import load_config
from database.database import Database
from agents.command_handlers import update_playlist_handler, stash_video_handler, check_playlist_delta_handler
from services.youtube_api_service import YouTubeAPIService
from services.yt_dlp_service import YTDLPService

logger = logging.getLogger(__name__)

class Stasher:
    def __init__(self, ytf_cli_path):
        self.config = load_config()
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
        stash_video_tool = StashVideoTool(self.yt_dlp_service)
        self.tools = [update_playlist_tool, stash_video_tool]

    def register_commands(self):
        self.register_command("update_playlist", update_playlist_handler)
        self.register_command("stash_video", stash_video_handler)
        self.register_command("check_playlist_delta", check_playlist_delta_handler)

    def register_command(self, command_name, handler):
        self.command_registry[command_name] = handler

    def handle_user_input(self, user_input):
        command_plan = self.plan_command(user_input)
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
        Important!: You are the Stasher agent, an AI designed to take in user input and determine the appropriate command and its parameters. The available commands are:
        Determine the appropriate command and its parameters. The available commands are:
        1. update_playlist - Updating the playlist metadata for the user, given a playlist (may have to ask for it), and saved to the database.
        2. stash_video  - Stashing a video or audio file for the user, given a URL or ID (may have to ask for it), and then saved to the user's storage.

        If the user doesn't make their request clear, or it doesn't fall neatly into one of the commands you have access to, the response should be always to remind the user that you are the stasher agent and can only perform limited commands. 
        It's ok to ask for clarification.


        Return a JSON object with the following structure/schema:
        {{
            "command": "command_name",
            "parameters": {{
                "param1": "value1",
                "param2": "value2"
            }}
        }}

        For example, if the user wants to stash a video and they give you the URL or ID like "dQw4w9WgXcQ", the response should be:
        {{
            "command": "stash_video",
            "parameters": {{
                "video_urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                "output_path": "downloads",
                "audio_only": false
            }}
        }}

        Ensure that the command name matches exactly one of the available commands. Never return anything else. Just JSON in the schema above.
        """
        
        response = self.get_llm_response(prompt)
        logger.info(f"Raw LLM Response: {response}")
        
        return self.parse_llm_response(response)

    def get_llm_response(self, prompt):
        response = completion(model=self.model, messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    def parse_output(self, output):
        if isinstance(output, str):
            return output
        else:
            return str(output)

    def parse_llm_response(self, response: str) -> Dict:
        print(response)
        try:
            parsed = json.loads(response)
            if parsed['command'] == 'stash_video':
                if 'video_ids' in parsed['parameters']:
                    parsed['parameters']['videos'] = parsed['parameters'].pop('video_ids')
                elif 'video_id' in parsed['parameters']:
                    parsed['parameters']['videos'] = [parsed['parameters'].pop('video_id')]
                elif 'video_urls' in parsed['parameters']:
                    parsed['parameters']['videos'] = [parsed['parameters']['video_urls']]
            return parsed
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            return {}

if __name__ == '__main__':
    ytf_cli_path = '../main.py'
    ytf_agent = Stasher(ytf_cli_path)
    while True:
        user_input = input("Enter your command (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        result = ytf_agent.handle_user_input(user_input)