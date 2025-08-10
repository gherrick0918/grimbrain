class MinimalFakeLLM:
    def __init__(self, log_entries=None):
        self.log_entries = log_entries if log_entries is not None else []

    def complete(self, prompt: str, **kwargs):
        msg = f"🟡 [FakeLLM] Fallback used for prompt: {prompt[:80]}..."
        print(msg)

        self.log_entries.append({
            "file": "N/A",
            "entries": 0,
            "collection": "LLM",
            "status": msg
        })

        class FakeResponse:
            def __init__(self, text):
                self.text = text
        return FakeResponse(text="(FakeLLM fallback — no LLM output)")