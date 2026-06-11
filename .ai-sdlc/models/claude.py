import subprocess
import shutil
from .base import ModelAdapter

class ClaudeAdapter(ModelAdapter):
    """
    Adapter for Anthropic's Claude models using the 'claude' CLI.
    """
    
    def run(self, prompt: str) -> str:
        if not shutil.which("claude"):
            return "Error: 'claude' CLI not found in PATH. Please install it to use this adapter."

        try:
            # Use 'claude -p' for non-interactive output. 
            # We pass the prompt as an argument.
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                return "Error: Claude CLI returned an empty response."
                
            return result.stdout.strip()

        except subprocess.CalledProcessError as exc:
            return f"Error executing Claude CLI (exit code {exc.returncode}):\n{exc.stderr or exc.stdout}"
        except Exception as exc:
            return f"Error: An unexpected error occurred while running Claude CLI: {str(exc)}"
