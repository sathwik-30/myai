import torch

from backend.model.architecture.positional_encoding import PositionalEncoding


def test_positional_encoding_preserves_sequence_shape():
    embedding_dim = 8
    positional_encoding = PositionalEncoding(embedding_dim)
    x = torch.randn(1, 4, embedding_dim)

    output = positional_encoding(x)

    assert output.shape == x.shape
    assert torch.isfinite(output).all()