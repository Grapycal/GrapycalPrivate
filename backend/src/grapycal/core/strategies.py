from abc import ABC, abstractmethod


class OpenAnotherWorkspaceStrategy(ABC):
    @abstractmethod
    def open(self, path: str):
        pass