"""Independent local language understanding for Medha.

The NLU is intentionally lightweight and local. It combines a trained
classifier with high-confidence structural cues so natural language does not
randomly become a privileged action.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Iterable

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
MODEL_DIR = os.path.join(DATA_DIR, "nlu")
MODEL_PATH = os.path.join(MODEL_DIR, "intent_classifier.joblib")
EXAMPLES_PATH = os.path.join(DATA_DIR, "nlu_examples.jsonl")

GENERAL_INTENTS = {
    "general", "casual", "greeting", "status", "identity", "capability",
    "thanks", "memory", "personal", "technical", "knowledge", "research",
    "permanent",
}

_DESKTOP_VERBS = r"(?:open|launch|start|run|close|quit|shut|exit)"
_DESKTOP_APPS = (
    "chrome|google chrome|browser|vscode|vs code|visual studio code|"
    "notepad|calculator|paint|explorer|terminal|cmd"
)


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
    value = " ".join(str(text or "").strip().split())
    entities: dict[str, str] = {}

    quoted = re.findall(r"[\"']([^\"']+)[\"']", value)
    if quoted:
        entities["quoted"] = quoted[0]

    app_match = re.search(
        rf"\b{_DESKTOP_VERBS}\s+(?:the\s+)?(.+?)(?:\s+(?:please|now))?$",
        value,
        re.IGNORECASE,
    )
    if app_match:
        entities["target"] = app_match.group(1).strip()

    app_mention = re.search(rf"\b({_DESKTOP_APPS})\b", value, re.IGNORECASE)
    if app_mention:
        entities["app"] = app_mention.group(1).strip()

    return entities


def _strong_desktop_request(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False

    # Explicit application control is safe to classify structurally even when
    # the statistical model has never seen that exact sentence.
    return bool(
        re.search(
            rf"\b{_DESKTOP_VERBS}\b.*\b(?:{_DESKTOP_APPS})\b",
            normalized,
            re.IGNORECASE,
        )
        or re.search(
            rf"\b{_DESKTOP_VERBS}\s+(?:the\s+)?(?:browser|terminal|coding workspace)\b",
            normalized,
            re.IGNORECASE,
        )
    )


class LocalLanguageEngine:
    def __init__(self) -> None:
        self.vectorizer = None
        self.classifier = None
        self._load_or_train()

    @property
    def available(self) -> bool:
        return self.vectorizer is not None and self.classifier is not None

    def _train(self, examples: Iterable[dict]) -> None:
        rows = list(examples)
        if len(rows) < 2:
            raise RuntimeError("Medha needs at least two NLU examples.")

        texts = [r["text"] for r in rows]
        labels = [r["intent"] for r in rows]
        if len(set(labels)) < 2:
            raise RuntimeError("Medha NLU needs at least two distinct intents.")
        self.vectorizer = FeatureUnion([
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                    max_features=12000,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    min_df=1,
                    sublinear_tf=True,
                    max_features=12000,
                ),
            ),
        ])
        matrix = self.vectorizer.fit_transform(texts)
        self.classifier = LogisticRegression(
            max_iter=1200,
            class_weight="balanced",
            random_state=42,
        )
        self.classifier.fit(matrix, labels)
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(
            {"version": 3, "vectorizer": self.vectorizer, "classifier": self.classifier},
            MODEL_PATH,
        )

    def _load_or_train(self) -> None:
        try:
            if os.path.exists(MODEL_PATH):
                payload = joblib.load(MODEL_PATH)
                if payload.get("version") != 3:
                    raise ValueError("Outdated NLU artifact")
                self.vectorizer = payload["vectorizer"]
                self.classifier = payload["classifier"]
                return
        except Exception:
            self.vectorizer = self.classifier = None
        self._train(_read_examples())

    def learn(self, text: str, intent: str) -> None:
        intent = str(intent or "").strip().lower()
        text = _normalize(text)
        if not text or not intent:
            raise ValueError("Both text and intent are required.")
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(EXAMPLES_PATH, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"text": text, "intent": intent}, ensure_ascii=False) + "\n"
            )
        self._train(_read_examples())

    def understand(self, text: str) -> Understanding:
        normalized = _normalize(text)
        entities = _extract_entities(text)

        if not normalized or not self.available:
            return Understanding(
                "desktop" if _strong_desktop_request(text) else "general",
                0.99 if _strong_desktop_request(text) else 0.0,
                entities,
            )

        if _strong_desktop_request(text):
            return Understanding("desktop", 0.99, entities)

        matrix = self.vectorizer.transform([normalized])
        probabilities = self.classifier.predict_proba(matrix)[0]
        index = int(probabilities.argmax())
        intent = str(self.classifier.classes_[index])
        confidence = float(probabilities[index])

        # The classifier should not invent a privileged intent from a weak
        # statistical match. Ambiguous language belongs to conversation.
        if intent == "desktop" and confidence < 0.78:
            return Understanding("general", confidence, entities)

        # Very low-confidence classifications should remain conversational.
        if confidence < 0.43 and intent in GENERAL_INTENTS:
            return Understanding("general", confidence, entities)

        return Understanding(intent, confidence, entities)


_engine = None


def get_language_engine() -> LocalLanguageEngine:
    global _engine
    if _engine is None:
        _engine = LocalLanguageEngine()
    return _engine
