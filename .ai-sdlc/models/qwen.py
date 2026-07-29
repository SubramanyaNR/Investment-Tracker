import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from .base import ModelAdapter

_ENV_FILE = Path(__file__).parent.parent / ".env"


def _load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    if _ENV_FILE.is_file():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY":
                return v.strip().strip('"').strip("'")
    return ""


class QwenAdapter(ModelAdapter):
    """
    Adapter for Alibaba's Qwen models via OpenRouter.
    """

    def run(self, prompt: str, log_path: Optional[Path] = None) -> str:
        api_key = _load_api_key()
        if not api_key:
            return "Error: OPENROUTER_API_KEY not found in environment or backend/.env."

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SubramanyaNR/Investment-Tracker",
            "X-Title": "WealthSignal AI-SDLC"
        }

        data = {
            "model": "qwen/qwen3-32b",
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode("utf-8"))

        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))

            content = body["choices"][0]["message"]["content"].strip()

            if not content:
                return "Error: OpenRouter API returned an empty response."

            if log_path:
                log_path.write_text(content + "\n", encoding="utf-8")

            return content

        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = "Could not read error body."
            return f"Error executing OpenRouter API (HTTP {exc.code}): {exc.reason}\nDetails: {error_body}"
        except urllib.error.URLError as exc:
            return f"Error: Network failure while contacting OpenRouter API: {exc.reason}"
        except TimeoutError:
            return "Error: Request to OpenRouter API timed out."
        except Exception as exc:
            return f"Error: An unexpected error occurred while running Qwen adapter: {str(exc)}"
