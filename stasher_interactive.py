import os

from agents.stasher import Stasher
from config import load_config

def run_stasher():
    config = load_config()
    stasher = Stasher(os.path.abspath(__file__))
    while True:
        user_input = input("Enter your command (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        result = stasher.handle_user_input(user_input)
        print(result)

if __name__ == '__main__':
    run_stasher()