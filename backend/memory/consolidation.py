"""Memory consolidation primitives.

Long-term memory is derived from explicit, high-value facts rather than every
conversation token.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    importance: float
    source: str = "conversation"

    def eligible(self, threshold: float = 0.7) -> bool:
        return bool(self.content.strip()) and self.importance >= threshold


def consolidate(candidates: list[MemoryCandidate], threshold: float = 0.7) -> list[MemoryCandidate]:
    seen = set()
    result = []
    for item in sorted(candidates, key=lambda x: x.importance, reverse=True):
        key = item.content.strip().casefold()
        if item.eligible(threshold) and key not in seen:
            seen.add(key)
            result.append(item)
    return result
