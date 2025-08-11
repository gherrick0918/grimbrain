from typing import Dict, Any

class ItemFormatter:
    def format(self, text: str, meta: Dict[str, Any] | None = None) -> str:
        meta = meta or {}
        name = meta.get("name", "Unknown Item")
        type_ = meta.get("type", "")
        rarity = meta.get("rarity", "")
        body = meta.get("text", text or "")
        lines = [f"🎁 **{name}**"]
        if type_:
            lines.append(f"**Type:** {type_}")
        if rarity:
            lines.append(f"**Rarity:** {rarity}")
        if body:
            lines.append("")
            lines.append(body.strip())
        return "\n".join(lines).rstrip()


def item_to_json(markdown: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    meta = meta or {}
    lines = [ln.strip() for ln in markdown.splitlines()]
    out: Dict[str, Any] = {
        "name": meta.get("name", ""),
        "type": meta.get("type", ""),
        "rarity": meta.get("rarity", ""),
        "text": meta.get("text", ""),
        "provenance": meta.get("provenance", []),
    }
    for ln in lines:
        if ln.startswith("**Type:**"):
            out["type"] = ln.split("**Type:**", 1)[1].strip()
        elif ln.startswith("**Rarity:**"):
            out["rarity"] = ln.split("**Rarity:**", 1)[1].strip()
    if not out["name"] and lines:
        out["name"] = lines[0].strip("🎁 *")
    if not out["text"]:
        out["text"] = "\n".join(lines[lines.index("")+1:]).strip() if "" in lines else ""
    return out
