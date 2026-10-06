import torch

from backend.model.architecture.feed_forward import FeedForward


def test_feed_forward_returns_same_shape_as_input():
    embedding_dim = 8
    hidden_dim = 32
    x = torch.randn(1, 4, embedding_dim)
    feed_forward = FeedForward(embedding_dim, hidden_dim)

    output = feed_forward(x)

    assert output.shape == x.shape
    assert output.dtype == x.dtype