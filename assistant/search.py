"""Simple weighted keyword retrieval; scores are not confidence estimates."""
import re
from .models import Passage, SearchResult

STOP_WORDS = set("a an the and or to of for in on at is are was be do does how what "
                 "when where who can i my me we our you your please should with it "
                 "this that from have has about tell".split())


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower())
            if word not in STOP_WORDS}


def search(question: str, passages: list[Passage], top_k: int = 3) -> list[SearchResult]:
    query = tokens(question)
    if not query or top_k <= 0:
        return []
    ranked = []
    for passage in passages:
        body = tokens(passage.text)
        section = tokens(passage.section) if passage.section != passage.title else set()
        title = tokens(passage.title)
        if not query & (body | section):
            continue
        matched = query & (body | section | title)
        # Require meaningful overlap: half the query terms, with at least two
        # for multi-word questions. A single specific term may also be searched.
        required = 1 if len(query) == 1 else max(2, (len(query) + 1) // 2)
        if len(matched) < required:
            continue
        score = (len(query & body) + 2 * len(query & section)
                 + len(query & title)) / len(query)
        ranked.append((score, passage))
    ranked.sort(key=lambda item: (-item[0], item[1].path, item[1].start_line))
    return [SearchResult(f"S{index}", passage, score)
            for index, (score, passage) in enumerate(ranked[:top_k], 1)]
