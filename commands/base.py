from abc import ABC, abstractmethod


class BaseCommand(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, parameters: dict, context: dict):
        pass

    @classmethod
    @abstractmethod
    def add_cli_parameters(cls, cli_command):
        pass

