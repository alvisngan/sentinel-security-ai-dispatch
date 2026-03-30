"""
parsing/router.py
-----------------
SchemaRouter — classifies an incoming email to the correct parse schema.

Builds the routing prompt dynamically from each schema's DESCRIPTION constant,
so adding a new schema to the registry is enough — no changes needed here.

Usage:
    from parsing.router import SchemaRouter
    from parsing.providers import OllamaProvider

    router = SchemaRouter(provider=OllamaProvider())
    schema_key = router.classify(email_text)   # e.g. "client_request"
"""

from parsing.schemas import REGISTRY

def _build_routing_prompt() -> str:
    categories = "\n".join(
        f"- {key}: {schema.DESCRIPTION}"
        for key, schema in REGISTRY.items()
    )
    return (
        "You are a shift scheduling assistant. Classify the email into exactly one category.\n\n"
        f"Categories:\n{categories}\n\n"
        "Respond with ONLY the category key — no explanation, no punctuation."
    )


class SchemaRouter:
    def __init__(self, provider):
        self.provider = provider

    def classify(self, email_text: str) -> str:
        prompt = _build_routing_prompt()
        raw = self.provider.complete(
            system=prompt,
            user=f"Classify this email:\n\n{email_text}",
        ).strip().lower()

        if raw not in REGISTRY:
            raise ValueError(f"Router returned unknown schema: {raw!r}")
        return raw
