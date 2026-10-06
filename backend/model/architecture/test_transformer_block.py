import torch

from backend.model.architecture.transformer_block import TransformerBlock


def test_transformer_block_preserves_sequence_shape():
    embedding_dim = 8
    num_heads = 2
    hidden_dim = 32
    x = torch.randn(1, 4, embedding_dim)
    block = TransformerBlock(embedding_dim, num_heads, hidden_dim)

    output = block(x)

    assert output.shape == x.shape
    assert torch.isfinite(output).all()