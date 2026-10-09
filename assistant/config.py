"""Environment settings. Offline search does not require an API key."""
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    sop_dir: Path
    api_key: str | None
    model: str
    top_k: int = 3


def load_config() -> Config:
    # Optional dependency: the standard-library search mode works without it.
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    folder = Path(os.environ.get("SOP_DIR", "data/sops"))
    if not folder.is_absolute():
        folder = PROJECT_ROOT / folder
    return Config(folder, os.environ.get("OPENAI_API_KEY"),
                  os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
