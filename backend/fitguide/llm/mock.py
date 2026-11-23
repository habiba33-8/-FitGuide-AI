from __future__ import annotations
import json


class MockLLM:
    def __init__(self, *answers: str | dict):
        self.answers = [a if isinstance(a, str) else json.dumps(a) for a in answers]
        self.calls: list[list[dict]] = []

    async def chat(self, messages, *, json_mode=False, temperature=0.3, max_tokens=1200) -> str:
        self.calls.append(messages)
        if not self.answers:
            raise RuntimeError("MockLLM ran out of answers")
        return self.answers.pop(0)
