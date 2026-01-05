import os

from agents.stasher import Stasher
from agents.stasher_ollama import StasherOllama
from config import load_config

def run_stasher():
    config = load_config()
    stasher = Stasher(os.path.abspath(__file__))
    _run_interactive_loop(stasher)

def run_stasher_ollama():
    config = load_config()
    stasher = StasherOllama(os.path.abspath(__file__))
    _run_interactive_loop(stasher)

def _run_interactive_loop(agent):
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