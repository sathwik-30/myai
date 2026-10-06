from backend.brain import conversation


def test_conversation_engine_returns_structured_response(monkeypatch):
    monkeypatch.setattr(
        conversation,
        "generate_response",
        lambda *args, **kwargs: {"answer": "I can help.", "source": "memory"},
    )

    engine = conversation.ConversationEngine(user_id=1)
    result = engine.chat("hello there")

    assert isinstance(result, dict)
    assert result["response"] == "I can help."
    assert result["source"] == "memory"
    assert engine.history()[-1]["role"] == "assistant"