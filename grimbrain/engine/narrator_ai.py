import json, urllib.request, urllib.error, sys, time
from .narrator import TemplateNarrator, ai_cached_generate_v2

class AINarrator:
    KIND = "openai:gpt-4o-mini"
    REASON = "ok"
    def __init__(self, api_key: str):
        self.api_key = api_key

    def render(self, template: str, ctx: dict) -> str:
        prompt = TemplateNarrator().render(template, ctx)
        model = "gpt-4o-mini"
        style = (ctx or {}).get("style") or "classic"
        section = (ctx or {}).get("section") or "misc"
        debug = bool((ctx or {}).get("_ai_debug"))

        def _call(prompt_text: str, model_name: str) -> str:
            try:
                start = time.time()
                print(f"[narration] CALLING OpenAI backend={self.KIND}", file=sys.stderr)
                body = {
                    "model": model_name,
                    "input": [
                        {
                            "role": "system",
                            "content": "You are a concise fantasy narrator. 1–3 short sentences.",
                        },
                        {"role": "user", "content": prompt_text},
                    ],
                    "max_output_tokens": 120,
                    "temperature": 0.7,
                }
                req = urllib.request.Request(
                    "https://api.openai.com/v1/responses",
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = json.loads(r.read().decode("utf-8"))
                elapsed = int((time.time() - start) * 1000)
                out = ""
                for item in data.get("output", []):
                    if isinstance(item, dict) and item.get("content"):
                        for c in item["content"]:
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                out += c.get("text", "")
                usage = data.get("usage") or {}
                tokens = usage.get("output_tokens") or usage.get("total_tokens") or "?"
                print(
                    f"[narration] DONE backend={self.KIND} tokens={tokens} time={elapsed}ms",
                    file=sys.stderr,
                )
                return (out or prompt_text).strip()
            except urllib.error.HTTPError as e:
                print(f"[narration] ERROR http {e.code}: {e.reason}", file=sys.stderr)
                return TemplateNarrator().render(template, ctx)
            except Exception as e:
                print(f"[narration] ERROR {type(e).__name__}: {e}", file=sys.stderr)
                return TemplateNarrator().render(template, ctx)

        tpl_id = (ctx or {}).get("tpl_id", "")
        location = (ctx or {}).get("location", "")
        tod = ((ctx or {}).get("time") or "").lower()
        time_bucket = {
            "morning": "am",
            "afternoon": "pm",
            "evening": "pm",
            "night": "night",
        }.get(tod, (ctx or {}).get("time", ""))

        return ai_cached_generate_v2(
            model,
            style,
            section,
            tpl_id,
            location,
            time_bucket,
            debug=debug,
            generator=lambda: _call(prompt, model),
        )
