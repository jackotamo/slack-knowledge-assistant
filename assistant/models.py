"""Shared records used by loading, retrieval, and answering."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Passage:
    title: str
    path: str
    section: str
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class SearchResult:
    identifier: str
    passage: Passage
    score: float


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[SearchResult] = field(default_factory=list)
    abstained: bool = False
