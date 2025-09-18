import os, json
from pathlib import Path
from typing import Dict, Any

CONFIG_DIR = Path.home() / ".grimbrain"
CONFIG_PATH = CONFIG_DIR / "config.json"
CACHE_DIR = CONFIG_DIR / "cache"
NARRATION_CACHE = CACHE_DIR / "narration.jsonl"

def load_config() -> Dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def get_api_key() -> str | None:
    # precedence: env, then local config
    return os.getenv("OPENAI_API_KEY") or load_config().get("openai_api_key")

def get_ai_enabled() -> bool:
    # env overrides config; both accept "1"/"true"/"yes"
    val = os.getenv("GRIMBRAIN_AI")
    if val is None:
        val = str(load_config().get("GRIMBRAIN_AI", "0"))
    return val.strip().lower() in ("1","true","yes","on")

def choose_ai_enabled(override: str | None) -> bool:
    """
    override: "on"|"off"|None. Precedence: override > env > config.
    """
    if override is not None:
        return override.strip().lower() in ("on","1","true","yes")
    return get_ai_enabled()

def append_cache_line(path: Path, obj: Dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def iter_cache(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: 
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue
