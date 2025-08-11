from typing import Dict, Any

class RuleFormatter:
    def format(self, text: str, meta: Dict[str, Any] | None = None) -> str:
        meta = meta or {}
        name = meta.get("name", "Unnamed Rule")
        category = meta.get("category", "")
        body = meta.get("text", text or "")
        lines = [f"📘 **{name}**"]
        if category:
            lines.append(f"**Category:** {category}")
        if body:
            lines.append("")
            lines.append(body.strip())
        return "\n".join(lines).rstrip()


def rule_to_json(markdown: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    meta = meta or {}
    lines = [ln.strip() for ln in markdown.splitlines()]
    out: Dict[str, Any] = {
        "name": meta.get("name", ""),
        "category": meta.get("category", ""),
        "text": meta.get("text", ""),
        "provenance": meta.get("provenance", []),
    }
    for ln in lines:
        if ln.startswith("**Category:**"):
            out["category"] = ln.split("**Category:**", 1)[1].strip()
    if not out["name"] and lines:
        out["name"] = lines[0].strip("📘 *")
    if not out["text"]:
        out["text"] = "\n".join(lines[lines.index("")+1:]).strip() if "" in lines else ""
    return out
