import json, urllib.request, urllib.error, sys
from .narrator import TemplateNarrator

class AINarrator:
    KIND = "openai:gpt-4o-mini"
    REASON = "ok"
    def __init__(self, api_key: str):
        self.api_key = api_key

    def render(self, template: str, ctx: dict) -> str:
        try:
            # First locally expand {{vars}} so the model gets specific context.
            prompt = TemplateNarrator().render(template, ctx)
            body = {
                "model": "gpt-4o-mini",
                "input": [
                    {"role":"system","content":"You are a concise fantasy narrator. 1–3 short sentences."},
                    {"role":"user","content": prompt}
                ],
                "max_output_tokens": 120,
                "temperature": 0.7,
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(body).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            out = ""
            for item in data.get("output", []):
                if isinstance(item, dict) and item.get("content"):
                    for c in item["content"]:
                        if isinstance(c, dict) and c.get("type") == "output_text":
                            out += c.get("text","")
            return (out or prompt).strip()
        except urllib.error.HTTPError as e:
            print(f"[narration] ERROR http {e.code}: {e.reason}", file=sys.stderr)
            return TemplateNarrator().render(template, ctx)
        except Exception as e:
            print(f"[narration] ERROR {type(e).__name__}: {e}", file=sys.stderr)
            return TemplateNarrator().render(template, ctx)
