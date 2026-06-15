from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class ModelAdapter(ABC):
    """
    Common interface for all model adapters in the AI-SDLC framework.
    """

    @abstractmethod
    def run(self, prompt: str, log_path: Optional[Path] = None) -> str:
        """
        Executes the given prompt and returns the model response.
        If log_path is provided, stream output to that file in real-time.
        """
        raise NotImplementedError
