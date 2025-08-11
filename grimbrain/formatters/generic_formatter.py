class GenericFormatter:
    def __init__(self, raw_text: str, metadata: dict = None):
        self.raw_text = raw_text
        self.metadata = metadata or {}

    def format(self) -> str:
        name = self.metadata.get("name", "Unnamed Entry")
        lines = [f"📘 **{name}**"]

        for key, value in self.metadata.items():
            if key.lower() == "name":
                continue
            if value not in [None, "", "Unknown"]:
                # Capitalize and format key
                pretty_key = key.replace("_", " ").title()
                lines.append(f"**{pretty_key}:** {value}")

        return "\n".join(lines)