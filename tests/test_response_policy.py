from unittest.mock import Mock, patch

from backend.brain import response
from backend.core import policy


def test_question_can_be_answered_when_override_is_unavailable(tmp_path):
    missing_policy = tmp_path / "missing-override.md"
    search_manager = Mock()
    search_manager.process.return_value = {
        "answer": "Photosynthesis converts light into chemical energy.",
        "source": "test_search",
    }

    with (
        patch.object(policy, "OVERRIDE_PATH", str(missing_policy)),
        patch.object(
            response,
            "understand",
            return_value={"intent": "knowledge", "confidence": 1.0},
        ),
        patch.object(response.UNDERSTANDING, "best_memory_answer", return_value=None),
        patch.object(response, "_decoder_answer", return_value=None),
    ):
        result = response.generate_response(
            "What is photosynthesis?", [], None, search_manager
        )

    assert result["answer"] == "Photosynthesis converts light into chemical energy."
    assert result["source"] == "test_search"


def test_actions_remain_blocked_when_override_is_unavailable(tmp_path):
    missing_policy = tmp_path / "missing-override.md"

    with patch.object(policy, "OVERRIDE_PATH", str(missing_policy)):
        result = policy.apply_override("", "open chrome")

    assert result["allowed"] is False
    assert result["reason"] == "core_override_unavailable"
