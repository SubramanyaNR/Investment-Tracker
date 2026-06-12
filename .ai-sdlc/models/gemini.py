import subprocess
import shutil
from .base import ModelAdapter

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google's Gemini models using the 'gemini' CLI.
    """
    
    def run(self, prompt: str) -> str:
        if not shutil.which("gemini"):
            return "Error: 'gemini' CLI not found in PATH. Please install it to use this adapter."

        try:
            # Use 'gemini -p' for non-interactive output.
            result = subprocess.run(
                ["gemini", "-p", prompt],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                return "Error: Gemini CLI returned an empty response."
                
            return result.stdout.strip()

        except subprocess.CalledProcessError as exc:
            return f"Error executing Gemini CLI (exit code {exc.returncode}):\n{exc.stderr or exc.stdout}"
        except Exception as exc:
            return f"Error: An unexpected error occurred while running Gemini CLI: {str(exc)}"
