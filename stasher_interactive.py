import os
import click

from agents.stasher import Stasher
from agents.stasher_ollama import StasherOllama
from config import load_config

ASCII_BANNER = """
____________              ______                  _______                    _____     
__  ___/_  /______ __________  /______________    ___    |______ ______________  /_    
_____ \_  __/  __ `/_  ___/_  __ \  _ \_  ___/    __  /| |_  __ `/  _ \_  __ \  __/    
____/ // /_ / /_/ /_(__  )_  / / /  __/  /        _  ___ |  /_/ //  __/  / / / /_      
/____/ \__/ \__,_/ /____/ /_/ /_/\___//_/         /_/  |_|\__, / \___//_/ /_/\__/      
                                                         /____/                        
"""

def display_banner(agent):
    click.clear()
    click.secho(ASCII_BANNER, fg='cyan', bold=True)
    click.echo("\nAvailable Tools:")
    for tool in agent.tools:
         click.secho(f"  {tool.name}: ", fg='green', bold=True, nl=False)
         click.echo(tool.description)
    click.echo("\n")

def run_stasher():
    config = load_config()
    stasher = Stasher(os.path.abspath(__file__))
    _run_interactive_loop(stasher)

def run_stasher_ollama():
    config = load_config()
    stasher = StasherOllama(os.path.abspath(__file__))
    _run_interactive_loop(stasher)

def _run_interactive_loop(agent):
    display_banner(agent)
    print(f"Starting interactive mode with {type(agent).__name__}...")
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

if __name__ == '__main__':
    run_stasher()