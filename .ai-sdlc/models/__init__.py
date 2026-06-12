from .claude import ClaudeAdapter
from .gemini import GeminiAdapter
from .qwen import QwenAdapter

_REGISTRY = {
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
    "qwen": QwenAdapter
}

def get_model(model_name: str):
    """
    Returns an instance of the requested model adapter.
    """
    adapter_class = _REGISTRY.get(model_name.lower())
    if not adapter_class:
        raise ValueError(f"Unknown model: {model_name}. Supported models: {list(_REGISTRY.keys())}")
    return adapter_class()
