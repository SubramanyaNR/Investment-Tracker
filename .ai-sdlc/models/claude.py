import subprocess
import shutil
from pathlib import Path
from typing import Optional
from .base import ModelAdapter


class ClaudeAdapter(ModelAdapter):
    """
    Adapter for Anthropic's Claude models using the 'claude' CLI.
    Uses subprocess.run (blocking) so Claude's OAuth-based permission flow works.
    Output is written to log_path after completion — not live-streamed, but
    readable/tailable as soon as the stage finishes.
    Live streaming is handled by Gemini and Qwen adapters for their stages.
    """

    # Prepended to every prompt so Claude outputs text only and doesn't try to use tools.
    _REVIEWER_PREFIX = (
        "IMPORTANT: You are acting as a text-only reviewer. "
        "Output ONLY your written analysis as plain text. "
        "Do NOT use any tools, write any files, or run any commands. "
        "Do NOT start a new workflow or feature. Just read the prompt below and respond with text.\n\n"
        "---\n\n"
    )

    def run(self, prompt: str, log_path: Optional[Path] = None) -> str:
        if not shutil.which("claude"):
            return "Error: 'claude' CLI not found in PATH. Please install it to use this adapter."

        try:
            result = subprocess.run(
                ["claude", "-p", self._REVIEWER_PREFIX + prompt],
                capture_output=True,
                text=True,
            )

            output = result.stdout.strip() or result.stderr.strip()

            if log_path and output:
                log_path.write_text(output + "\n", encoding="utf-8")

            if not output:
                return "Error: Claude CLI returned an empty response."
            return output

        except Exception as exc:
            return f"Error: An unexpected error occurred while running Claude CLI: {str(exc)}"
