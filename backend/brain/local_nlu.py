"""Independent local language understanding for Medha."""
from __future__ import annotations
import json, os, re
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
            try: item = json.loads(line)
            except json.JSONDecodeError: continue
            if item.get("text") and item.get("intent"):
                examples.append({"text": _normalize(item["text"]), "intent": str(item["intent"]).strip().lower()})
    return examples

def _extract_entities(text: str) -> dict[str, str]:
    value = str(text or "").strip()
    entities = {}
    quoted = re.findall(r"[\"']([^\"']+)[\"']", value)
    if quoted: entities["quoted"] = quoted[0]
    app_match = re.search(r"\b(?:open|launch|start|run|close|quit)\s+(.+?)(?:\s+(?:please|now))?$", value, re.I)
    if app_match: entities["target"] = app_match.group(1).strip()
    return entities

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
        if len(rows) < 2: raise RuntimeError("Medha needs at least two NLU examples.")
        texts, labels = [r["text"] for r in rows], [r["intent"] for r in rows]
        self.vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True, max_features=12000)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1, sublinear_tf=True, max_features=12000)),
        ])
        matrix = self.vectorizer.fit_transform(texts)
        self.classifier = LogisticRegression(max_iter=1200, class_weight="balanced", random_state=42)
        self.classifier.fit(matrix, labels)
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump({"version": 2, "vectorizer": self.vectorizer, "classifier": self.classifier}, MODEL_PATH)

    def _load_or_train(self) -> None:
        try:
            if os.path.exists(MODEL_PATH):
                payload = joblib.load(MODEL_PATH)
                if payload.get("version") != 2:
                    raise ValueError("Outdated NLU artifact")
                self.vectorizer, self.classifier = payload["vectorizer"], payload["classifier"]
                return
        except Exception:
            self.vectorizer = self.classifier = None
        self._train(_read_examples())

    def learn(self, text: str, intent: str) -> None:
        intent, text = str(intent or "").strip().lower(), _normalize(text)
        if not text or not intent: raise ValueError("Both text and intent are required.")
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(EXAMPLES_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"text": text, "intent": intent}, ensure_ascii=False) + "\n")
        self._train(_read_examples())

    def understand(self, text: str) -> Understanding:
        normalized = _normalize(text)
        if not normalized or not self.available:
            return Understanding("general", 0.0, _extract_entities(text))
        matrix = self.vectorizer.transform([normalized])
        probabilities = self.classifier.predict_proba(matrix)[0]
        index = int(probabilities.argmax())
        return Understanding(
            intent=str(self.classifier.classes_[index]),
            confidence=float(probabilities[index]),
            entities=_extract_entities(text),
        )

_engine = None
def get_language_engine() -> LocalLanguageEngine:
    global _engine
    if _engine is None: _engine = LocalLanguageEngine()
    return _engine
