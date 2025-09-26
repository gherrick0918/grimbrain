import hashlib, json, os, sys, random, time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

import yaml

from .config import get_api_key, NARRATION_CACHE, append_cache_line, iter_cache


_NARRATIVE_ROOT = Path(__file__).resolve().parents[2] / "data" / "narrative"


# --- AI cache helpers -------------------------------------------------------


def _ai_cache_dir() -> Path:
    d = os.environ.get("GRIMBRAIN_AI_CACHE_DIR") or str(
        Path.home() / ".grimbrain" / "ai_cache"
    )
    path = Path(d)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ai_cache_key_v2(
    model: str,
    style: str,
    section: str,
    tpl_id: str,
    location: str,
    time_bucket: str,
) -> str:
    payload = {
        "m": model or "",
        "style": style or "",
        "sec": section or "",
        "tpl": tpl_id or "",
        "loc": location or "",
        "tb": time_bucket or "",
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _ai_cache_path_from_key(key: str) -> Path:
    return _ai_cache_dir() / f"{key}.txt"


def _ai_index_path() -> Path:
    return _ai_cache_dir() / "index.json"


def _ai_index_load() -> dict:
    path = _ai_index_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _ai_index_save(idx: dict):
    _ai_index_path().write_text(
        json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _ai_index_touch(idx: dict, key: str, path: Path):
    entry = idx.get(key) or {
        "path": str(path),
        "hits": 0,
        "created_at": time.time(),
    }
    entry["hits"] = int(entry.get("hits", 0)) + 1
    entry["last_used_at"] = time.time()
    entry["path"] = str(path)
    idx[key] = entry


def _ai_index_lru_trim(idx: dict):
    try:
        limit = int(os.environ.get("GRIMBRAIN_AI_CACHE_MAX", "500"))
    except Exception:
        limit = 500
    if len(idx) <= limit:
        return idx
    items = sorted(
        idx.items(),
        key=lambda item: item[1].get(
            "last_used_at", item[1].get("created_at", 0)
        ),
    )
    remove = items[0 : max(0, len(idx) - limit)]
    for key, meta in remove:
        try:
            Path(meta.get("path", "")).unlink(missing_ok=True)
        except Exception:
            pass
        idx.pop(key, None)
    return idx


def ai_cached_generate_v2(
    model: str,
    style: str,
    section: str,
    tpl_id: str,
    location: str,
    time_bucket: str,
    *,
    debug: bool,
    generator,
):
    """
    generator() -> str (usually the AI call).
    Caches to disk with structured keys and maintains an index with LRU trimming.
    """

    key = _ai_cache_key_v2(model, style, section, tpl_id, location, time_bucket)
    path = _ai_cache_path_from_key(key)
    idx = _ai_index_load()
    dbg = debug or os.environ.get("GRIMBRAIN_AI_DEBUG") == "1"
    if path.exists():
        out = path.read_text(encoding="utf-8")
        _ai_index_touch(idx, key, path)
        _ai_index_save(idx)
        if dbg:
            hits = idx.get(key, {}).get("hits")
            print(f"[AI cache HIT] {path} key={key} hits={hits}")
        return out
    out = generator()
    try:
        path.write_text(out, encoding="utf-8")
        _ai_index_touch(idx, key, path)
        _ai_index_save(_ai_index_lru_trim(idx))
        if dbg:
            hits = idx.get(key, {}).get("hits")
            print(f"[AI cache MISS→WRITE] {path} key={key} hits={hits}")
    except Exception as e:  # pragma: no cover - disk errors are debug noise
        if dbg:
            print(f"[AI cache WRITE ERROR] {e}")
    return out


@lru_cache(maxsize=None)
def _load_template_pack(pack: str) -> Dict[str, list[str]]:
    path = _NARRATIVE_ROOT / f"{pack}.yaml"
    if not path.exists():
        path = _NARRATIVE_ROOT / "classic.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def pick_template_line(
    pack: str, section: str, ctx: Dict[str, Any], seed: int | None = None
) -> tuple[str, str]:
    data = _load_template_pack(pack)
    options = list(data.get(section) or [])
    if not options:
        return "", ""
    rng = random.Random(seed)
    idx = rng.randrange(len(options))
    raw = options[idx]
    tpl_id = f"{pack}:{section}:{idx}"
    return raw.format_map(defaultdict(str, ctx)), tpl_id

class TemplateNarrator:
    KIND = "template"
    REASON = "ok"
    def render(self, template: str, ctx: Dict[str, object]) -> str:
        out = template or ""
        for k, v in ctx.items():
            out = out.replace(f"{{{{{k}}}}}", str(v))
        return out

def _hash(scene_id: str, template: str, ctx: Dict[str, Any], backend_kind: str) -> str:
    """Include BACKEND KIND in the hash so template and AI never collide."""
    h = hashlib.sha256()
    h.update(backend_kind.encode("utf-8", "ignore")); h.update(b"\x00")
    h.update(scene_id.encode("utf-8", "ignore")); h.update(b"\x00")
    h.update((template or "").encode("utf-8", "ignore")); h.update(b"\x00")
    h.update(str(sorted(ctx.items())).encode("utf-8", "ignore"))
    return h.hexdigest()

class CachedNarrator:
    def __init__(self, backend, debug: bool = False, flush: bool = False):
        self.backend = backend
        self.kind = getattr(backend, "KIND", "template")
        self.reason = getattr(backend, "REASON", "ok")
        self.debug = debug
        self.flush = flush
        self._template = TemplateNarrator()

    def render(self, scene_id: str, template: str, ctx: Dict[str, Any]) -> str:
        ctx_local: Dict[str, Any] = dict(ctx or {})
        if "section" not in ctx_local:
            base, _, tail = scene_id.partition("#")
            ctx_local["section"] = tail or base or "misc"
        ctx_local.setdefault("scene", scene_id)
        ctx_local.setdefault("style", ctx_local.get("style") or "classic")
        ctx_local.setdefault("_ai_debug", self.debug)
        key = _hash(scene_id, template, ctx_local, self.kind)
        if not self.flush:
            for row in iter_cache(NARRATION_CACHE):
                if row.get("key") == key:
                    if self.debug:
                        print(f"[narration] backend={self.kind} reason={self.reason} cache=HIT scene={scene_id}")
                    return row.get("text","")
        text = self.backend.render(template, ctx_local)
        # Always preserve the underlying template text so deterministic tests can
        # assert on authored story beats even when an AI backend embellishes the
        # narration. This mirrors the template output for template narrators
        # while appending it (once) for AI responses that omit the original text.
        fallback = self._template.render(template, ctx_local)
        if self.kind != "template" and fallback:
            if fallback not in text:
                if text and not text.endswith("\n"):
                    text += "\n"
                text += fallback
        append_cache_line(NARRATION_CACHE, {"key": key, "text": text})
        if self.debug:
            print(f"[narration] backend={self.kind} reason={self.reason} cache=MISS scene={scene_id}")
        return text

def get_narrator(ai_enabled: bool, debug: bool = False, flush: bool = False):
    key = get_api_key()
    if ai_enabled and key:
        try:
            from .narrator_ai import AINarrator
            return CachedNarrator(AINarrator(api_key=key), debug=debug, flush=flush)
        except Exception as e:
            t = TemplateNarrator()
            t.REASON = f"import_error:{type(e).__name__}"
            if debug:
                print(f"[narration] ERROR importing AINarrator: {e}", file=sys.stderr)
            return CachedNarrator(t, debug=debug, flush=flush)
    t = TemplateNarrator()
    t.REASON = ("no_key" if ai_enabled and not key else "ai_disabled")
    return CachedNarrator(t, debug=debug, flush=flush)
