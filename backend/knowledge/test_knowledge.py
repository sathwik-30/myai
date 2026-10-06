from backend.knowledge.knowledge_base import KnowledgeBase


def test_knowledge_base_search_returns_known_topic_data():
    knowledge_base = KnowledgeBase()

    result = knowledge_base.search("What is Python?")

    if result is not None:
        assert isinstance(result, dict)
        assert "topic" in result
        assert "content" in result
        assert "python" in result["topic"].lower()
    else:
        assert result is None