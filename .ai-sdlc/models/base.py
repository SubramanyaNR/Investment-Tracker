from abc import ABC, abstractmethod

class ModelAdapter(ABC):
    """
    Common interface for all model adapters in the AI-SDLC framework.
    """
    
    @abstractmethod
    def run(self, prompt: str) -> str:
        """
        Executes the given prompt and returns the model response.
        To be implemented by concrete adapters.
        """
        raise NotImplementedError
