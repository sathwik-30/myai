"""Independent local language understanding for Medha.

This module is deliberately provider-free.  It learns intent patterns from a
small JSONL corpus plus user corrections and uses TF-IDF + logistic regression
to generalize across natural wording instead of maintaining an if/else phrase
list.

The model is intentionally small.  It is an NLU component, not a claim to be a
general-purpose LLM.  General knowledge remains in Medha's local memory and
optional search layers.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Iterable

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
MODEL_DIR = os.path.join(DATA_DIR, "nlu")
MODEL_PATH = os.path.join(MODEL_DIR, "intent_classifier.joblib")
EXAMPLES_PATH = os.path.join(DATA_DIR, "nlu_examples.jsonl")


@dataclass
class Understanding:
    intent: str
    confidence: float
    entities: dict[str, str]


def _normalize(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9'?.!\s]", " ", text)
    return " ".join(text.split())


def _read_examples() -> list[dict]:
    if not os.path.exists(EXAMPLES_PATH):
        return []
    examples = []
    with open(EXAMPLES_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("text") and item.get("intent"):
                examples.append({
                    "text": _normalize(item["text"]),
                    "intent": str(item["intent"]).strip().lower(),
                })
    return examples


def _extract_entities(text: str) -> dict[str, str]:
    value = str(text or "").strip()
    entities: dict[str, str] = {}

    quoted = re.findall(r"[\"']([^\"']+)[\"']", value)
    if quoted:
        entities["quoted"] = quoted[0]

    app_match = re.search(
        r"\b(?:open|launch|start|run|close|quit)\s+(.+?)(?:\s+(?:please|now))?$",
        value,
        re.IGNORECASE,
    )
    if app_match:
        entities["target"] = app_match.group(1).strip()

    return entities


class LocalLanguageEngine:
    """Trainable, local, dependency-free-from-LLM language understanding."""

    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.classifier: LogisticRegression | None = None
        self._load_or_train()

    @property
    def available(self) -> bool:
        return self.vectorizer is not None and self.classifier is not None

    def _train(self, examples: Iterable[dict]) -> None:
        rows = list(examples)
        if len(rows) < 2:
            raise RuntimeError("Medha needs at least two NLU examples.")

        texts = [row["text"] for row in rows]
        labels = [row["intent"] for row in rows]

        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
            max_features=12000,
        )
        matrix = self.vectorizer.fit_transform(texts)
        self.classifier = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )
        self.classifier.fit(matrix, labels)

        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "classifier": self.classifier,
            },
            MODEL_PATH,
        )

    def _load_or_train(self) -> None:
        try:
            if os.path.exists(MODEL_PATH):
                payload = joblib.load(MODEL_PATH)
                self.vectorizer = payload["vectorizer"]
                self.classifier = payload["classifier"]
                return
        except Exception:
            self.vectorizer = None
            self.classifier = None

        self._train(_read_examples())

    def learn(self, text: str, intent: str) -> None:
        intent = str(intent or "").strip().lower()
        text = _normalize(text)
        if not text or not intent:
            raise ValueError("Both text and intent are required.")

        os.makedirs(DATA_DIR, exist_ok=True)
        with open(EXAMPLES_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {"text": text, "intent": intent},
                ensure_ascii=False,
            ) + "\n")

        self._train(_read_examples())

    def understand(self, text: str) -> Understanding:
        normalized = _normalize(text)
        if not normalized or not self.available:
            return Understanding("general", 0.0, _extract_entities(text))

        matrix = self.vectorizer.transform([normalized])
        probabilities = self.classifier.predict_proba(matrix)[0]
        index = int(probabilities.argmax())
        intent = str(self.classifier.classes_[index])
        confidence = float(probabilities[index])

        return Understanding(
            intent=intent,
            confidence=confidence,
            entities=_extract_entities(text),
        )


_engine: LocalLanguageEngine | None = None


def get_language_engine() -> LocalLanguageEngine:
    global _engine
    if _engine is None:
        _engine = LocalLanguageEngine()
    return _engine
