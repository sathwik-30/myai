import torch

from backend.model.architecture.embedding import Embedding


def test_embedding_output_shape_matches_token_shape():
    vocab_size = 20
    embedding_dim = 8
    model = Embedding(vocab_size, embedding_dim)
    tokens = torch.tensor([[4, 5, 6, 7]])

    output = model(tokens)

    assert output.shape == (1, 4, embedding_dim)
    assert output.dtype == torch.float32