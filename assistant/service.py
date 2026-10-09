"""Coordinate retrieval and reject answers with missing or invalid citations."""
from .models import Answer
from .search import search

ABSTENTION = "I don't have enough information in the available documents to answer that."


class AssistantService:
    def __init__(self, passages, generator, top_k=3):
        self.passages = passages
        self.generator = generator
        self.top_k = top_k

    def answer_question(self, question: str) -> Answer:
        sources = search(question, self.passages, self.top_k)
        if not sources:
            return Answer(ABSTENTION, abstained=True)
        try:
            payload = self.generator.generate(question, sources)
        except (ValueError, TypeError) as error:
            # Configuration errors remain actionable; invalid model JSON abstains.
            import json
            if isinstance(error, json.JSONDecodeError):
                return Answer(ABSTENTION + " The generated response was invalid.", abstained=True)
            raise
        if not isinstance(payload, dict) or payload.get("insufficient_evidence") is not False:
            return Answer(ABSTENTION, abstained=True)
        claims = payload.get("claims")
        if not isinstance(claims, list) or not claims:
            return Answer(ABSTENTION, abstained=True)
        allowed = {source.identifier for source in sources}
        used = set()
        rendered = []
        for claim in claims:
            if not isinstance(claim, dict):
                return Answer(ABSTENTION, abstained=True)
            text, identifiers = claim.get("text"), claim.get("source_ids")
            if (not isinstance(text, str) or not text.strip() or "[" in text
                    or not isinstance(identifiers, list) or not identifiers
                    or any(not isinstance(i, str) or i not in allowed for i in identifiers)):
                return Answer(ABSTENTION + " The generated citations could not be validated.", abstained=True)
            used.update(identifiers)
            rendered.append(text.strip() + " " + " ".join(f"[{i}]" for i in dict.fromkeys(identifiers)))
        return Answer("\n".join(rendered), [s for s in sources if s.identifier in used])
