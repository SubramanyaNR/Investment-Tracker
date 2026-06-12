import subprocess
import shutil
from pathlib import Path
from .base import ModelAdapter

# Repo root is two levels up from this file (.ai-sdlc/models/gemini.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google's Gemini models using the 'gemini' CLI.

    Runs headless with --approval-mode auto_edit so Gemini can actually write
    code (write_file/replace). Without it, headless `gemini -p` blocks every
    edit tool and only returns a text plan — the implementation never lands.
    auto_edit auto-approves file edits but NOT run_shell_command, so migrations
    and tests stay under human/Claude control. --skip-trust avoids the
    untrusted-directory refusal; cwd pins edits to the repo, not .ai-sdlc.
    """

    def run(self, prompt: str) -> str:
        if not shutil.which("gemini"):
            return "Error: 'gemini' CLI not found in PATH. Please install it to use this adapter."

        try:
            result = subprocess.run(
                ["gemini", "--approval-mode", "auto_edit", "--skip-trust", "-p", prompt],
                capture_output=True,
                text=True,
                check=True,
                cwd=str(_REPO_ROOT),
            )
            
            if not result.stdout.strip():
                return "Error: Gemini CLI returned an empty response."
                
            return result.stdout.strip()

        except subprocess.CalledProcessError as exc:
            return f"Error executing Gemini CLI (exit code {exc.returncode}):\n{exc.stderr or exc.stdout}"
        except Exception as exc:
            return f"Error: An unexpected error occurred while running Gemini CLI: {str(exc)}"
