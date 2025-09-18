import hashlib, sys
from typing import Dict, Any
from .config import get_api_key, NARRATION_CACHE, append_cache_line, iter_cache

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

    def render(self, scene_id: str, template: str, ctx: Dict[str, Any]) -> str:
        key = _hash(scene_id, template, ctx, self.kind)
        if not self.flush:
            for row in iter_cache(NARRATION_CACHE):
                if row.get("key") == key:
                    if self.debug:
                        print(f"[narration] backend={self.kind} reason={self.reason} cache=HIT scene={scene_id}")
                    return row.get("text","")
        text = self.backend.render(template, ctx)
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
