import os
import json
import urllib.request
import urllib.error
from pathlib import Path
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

    def run(self, prompt: str, log_path: Path | None = None) -> str:
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
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urllib.request.Request(url, headers=headers, data=json.dumps(data).encode("utf-8"))

        try:
            chunks = []
            log_file = open(log_path, "w", encoding="utf-8", buffering=1) if log_path else None
            try:
                with urllib.request.urlopen(req, timeout=180) as response:
                    for raw_line in response:
                        line = raw_line.decode("utf-8").strip()
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        delta = event.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content") or ""
                        if token:
                            chunks.append(token)
                            if log_file:
                                log_file.write(token)
                                log_file.flush()
            finally:
                if log_file:
                    log_file.write("\n")
                    log_file.close()

            content = "".join(chunks).strip()
            if not content:
                return "Error: OpenRouter API returned an empty response."
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
