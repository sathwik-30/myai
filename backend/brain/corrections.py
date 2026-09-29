"""Explicit correction learning.

Corrections become durable training/memory candidates. They do not silently
rewrite model weights during a conversation.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Correction:
    input_text: str
    previous_output: str
    corrected_output: str
    source: str = "host"


class CorrectionStore:
    def __init__(self):
        self._items: list[Correction] = []

    def add(self, correction: Correction) -> Correction:
        if not correction.input_text.strip() or not correction.corrected_output.strip():
            raise ValueError("A correction requires input and corrected output")
        self._items.append(correction)
        return correction

    def all(self) -> list[Correction]:
        return list(self._items)


corrections = CorrectionStore()
