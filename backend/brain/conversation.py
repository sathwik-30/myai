import logging
import re

from backend.agent.autonomy import autonomy
from backend.agent.kill_switch import require_enabled
from backend.agent.permissions import PermissionProfile
from backend.brain.context import ConversationContext
from backend.brain.intent import understand
from backend.brain.response import generate_response
from backend.chats.store import get_user_by_id
from backend.core.authority import authority_for_user, CREATOR, HOST
from backend.core.policy import apply_override
from backend.desktop.agent import DesktopAgent, DesktopAgentError
from backend.memory.evaluator import evaluate_memory
from backend.memory.manager import MemoryManager
from backend.observability.audit_store import audit_store

logger = logging.getLogger("medha.conversation")
DESKTOP_CONFIDENCE_THRESHOLD = 0.70
CORRECTION_PREFIXES = (
    "no,",
    "no ",
    "actually,",
    "actually ",
    "that's wrong",
    "that is wrong",
    "correct answer:",
    "the correct answer is",
)

class ConversationEngine:
    """Local conversation engine with guarded actions and durable corrections."""

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.context = ConversationContext()
        self.search_manager = None
        self.memory = MemoryManager(user_id=user_id)
        self.desktop = DesktopAgent()

    def _get_search_manager(self):
        if self.search_manager is None:
            from backend.search.search_manager import SearchManager
            self.search_manager = SearchManager(user_id=self.user_id)
        return self.search_manager

    def _resolve_desktop_target(self, target: str) -> str:
        value = " ".join(str(target or "").lower().split())
        aliases = {
            "google chrome": "chrome", "browser": "chrome", "web browser": "chrome",
            "visual studio code": "vscode", "vs code": "vscode",
            "code editor": "vscode", "coding workspace": "vscode",
            "my coding workspace": "vscode",
        }
        if value in aliases:
            return aliases[value]
        memory = self.memory.search_personal(target)
        if memory:
            answer = " ".join(str(memory.get("answer", "")).lower().split())
            for key, app in aliases.items():
                if key in answer:
                    return app
            if answer in self.desktop.SUPPORTED_APPS:
                return answer
        return value

    def _desktop_action(self, message: str, parsed: dict):
        if float(parsed.get("confidence", 0.0)) < DESKTOP_CONFIDENCE_THRESHOLD:
            return ("I think this may be a desktop request, but I'm not confident enough "
                    "to operate your computer from that wording. Please name the application "
                    "and action explicitly.", "desktop_uncertain")
        user = get_user_by_id(self.user_id) if self.user_id is not None else None
        actor = authority_for_user(user or {"sub": self.user_id})
        if actor not in (CREATOR, HOST):
            return "Creator/host authority required for desktop control.", "authority_denied"
        if not PermissionProfile.from_policy().can("desktop"):
            return "Desktop control is disabled by the current Medha authority policy.", "permission_denied"
        if not autonomy.allows_execution():
            return "Desktop execution is disabled at the current autonomy level.", "autonomy_blocked"
        try:
            require_enabled()
        except RuntimeError as exc:
            return str(exc), "kill_switch"
        policy = apply_override("", message)
        if not policy["allowed"]:
            return policy["response"], "core_override"
        entities = parsed.get("entities") or {}
        target = entities.get("target", "").strip()
        if not target:
            match = re.search(r"\b(?:open|launch|start|run|close|quit)\s+(.+?)(?:\s+(?:please|now))?$",
                               message, re.IGNORECASE)
            target = match.group(1).strip() if match else ""
        if not target:
            return "Tell me which application you want me to control.", "desktop"
        action_match = re.match(r"^\s*(open|launch|start|run|close|quit)\b", message, re.IGNORECASE)
        action = action_match.group(1).lower() if action_match else "open"
        target = self._resolve_desktop_target(target)
        try:
            if action in {"close", "quit"}:
                result = self.desktop.close_app(target)
                audit_store.record("desktop.close", user_id=self.user_id, app=target, result=result)
                return f"Closed {target}.", "desktop"
            result = self.desktop.open_app(target)
            audit_store.record("desktop.open", user_id=self.user_id, app=target, result=result)
            return f"Opened {target}.", "desktop"
        except DesktopAgentError as exc:
            audit_store.record("desktop.error", user_id=self.user_id, app=target, error=str(exc))
            return str(exc), "desktop_error"

    @staticmethod
    def _is_explicit_correction(message: str) -> bool:
        value = " ".join(str(message or "").lower().split())
        return any(value.startswith(prefix) for prefix in CORRECTION_PREFIXES)

    def _learn_correction(self, history, message):
        if len(history) < 2 or history[-1].get("role") != "assistant":
            return False
        if not self._is_explicit_correction(message):
            return False
        previous_question = history[-2].get("message", "")
        if not previous_question:
            return False
        correction = re.sub(
            r"^(?:no,?\s*|actually,?\s*|that's wrong\s*|that is wrong\s*|correct answer:\s*|the correct answer is\s*)",
            "",
            message.strip(),
            flags=re.IGNORECASE,
        ).strip()
        if not correction:
            return False
        self.memory.learn_personal(previous_question, correction, importance=5)
        audit_store.record(
            "memory.correction",
            user_id=self.user_id,
            original=previous_question,
            correction=correction,
        )
        return True

    def chat(self, message):
        history = self.context.get_messages()
        parsed = understand(message)
        try:
            if parsed["intent"] == "desktop":
                response, source = self._desktop_action(message, parsed)
            elif self._learn_correction(history, message):
                response, source = "Got it. I've updated my memory for that question.", "memory_correction"
            else:
                result = generate_response(
                    message, history, None, self._get_search_manager(), self.user_id
                )
                if isinstance(result, dict):
                    response = result.get("answer", "")
                    source = result.get("source", "memory")
                else:
                    response, source = str(result), "memory"

                learned_from_followup = False
                if history and history[-1].get("role") == "assistant":
                    previous_answer = history[-1].get("message", "")
                    if previous_answer.startswith("I don't know that yet.") and message.strip():
                        previous_question = history[-2].get("message", "") if len(history) >= 2 else ""
                        if previous_question:
                            self.memory.learn_personal(previous_question, message.strip(), importance=5)
                            response, source = "Got it. I'll remember that for our future conversations.", "memory_saved"
                            learned_from_followup = True

                if not learned_from_followup:
                    intent = parsed["intent"]
                    if intent == "permanent":
                        self.memory.learn_permanent(message, message, source="user", importance=5)
                        response, source = "Got it. I'll keep that in my permanent memory.", "permanent_memory_saved"
                    elif intent in {"memory", "personal"}:
                        self.memory.learn_personal(message, message, importance=5 if intent == "memory" else 4)
                        response = "Got it. I'll remember that." if intent == "memory" else "Got it. I'll keep that in mind for future conversations."
                        source = "memory_saved"
                    else:
                        decision = evaluate_memory(message, response, source)
                        if decision["save"]:
                            self.memory.learn(message, response, source=source,
                                              importance=decision["importance"],
                                              memory_type=decision["memory_type"])
        except Exception:
            logger.exception("Conversation generation failed; using local fallback")
            response, source = self._safe_local_response(message)

        self.context.add("user", message)
        self.context.add("assistant", response)
        return {"response": response, "source": source}

    @staticmethod
    def _safe_local_response():
        return (
            "I hit a temporary problem while processing that. Please try again.",
            "fallback",
        )

    def history(self):
        return self.context.get_messages()
