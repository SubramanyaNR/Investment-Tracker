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

    def run(self, prompt: str, log_path: Path | None = None) -> str:
        if not shutil.which("gemini"):
            return "Error: 'gemini' CLI not found in PATH. Please install it to use this adapter."

        try:
            proc = subprocess.Popen(
                ["gemini", "--approval-mode", "auto_edit", "--skip-trust", "-p", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(_REPO_ROOT),
            )

            lines = []
            log_file = open(log_path, "w", encoding="utf-8", buffering=1) if log_path else None
            try:
                for line in proc.stdout:
                    lines.append(line)
                    if log_file:
                        log_file.write(line)
                        log_file.flush()
            finally:
                if log_file:
                    log_file.close()

            proc.wait()
            output = "".join(lines).strip()

            if proc.returncode != 0:
                return f"Error executing Gemini CLI (exit code {proc.returncode}):\n{output}"
            if not output:
                return "Error: Gemini CLI returned an empty response."
            return output

        except Exception as exc:
            return f"Error: An unexpected error occurred while running Gemini CLI: {str(exc)}"
