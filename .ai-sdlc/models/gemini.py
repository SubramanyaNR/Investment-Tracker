import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from .base import ModelAdapter

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = Path(__file__).parent.parent / ".env"


def _load_env() -> dict:
    """Merge .ai-sdlc/.env (GEMINI_API_KEY, GEMINI_MODEL, ...) into the subprocess environment.
    The gemini CLI reads these from its process env, not from this repo's .env files directly."""
    env = os.environ.copy()
    if _ENV_FILE.is_file():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

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

    def run(self, prompt: str, log_path: Optional[Path] = None) -> str:
        if not shutil.which("gemini"):
            return "Error: 'gemini' CLI not found in PATH. Please install it to use this adapter."

        try:
            result = subprocess.run(
                ["gemini", "--approval-mode", "auto_edit", "--skip-trust", "-p", prompt],
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                env=_load_env(),
            )

            output = (result.stdout + result.stderr).strip()

            if log_path and output:
                log_path.write_text(output + "\n", encoding="utf-8")

            if result.returncode != 0:
                return f"Error executing Gemini CLI (exit code {result.returncode}):\n{output}"
            if not output:
                return "Error: Gemini CLI returned an empty response."
            return output

        except Exception as exc:
            return f"Error: An unexpected error occurred while running Gemini CLI: {str(exc)}"
