import torch

from backend.model.architecture.attention import SelfAttention


def test_self_attention_output_shape_matches_input():
    embedding_dim = 8
    num_heads = 2
    sequence_length = 4
    batch_size = 1

    attention = SelfAttention(embedding_dim, num_heads)
    x = torch.randn(batch_size, sequence_length, embedding_dim)

    output = attention(x)

    assert output.shape == x.shape
    assert output.dtype == x.dtype