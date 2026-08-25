import torch
import torch.nn as nn
from backend.model.architecture.embedding import Embedding
from backend.model.architecture.positional_encoding import PositionalEncoding
from backend.model.architecture.transformer_block import TransformerBlock

class Transformer(nn.Module):
    def __init__(
        self,
        vocab_size,
        embedding_dim,
        num_heads,
        hidden_dim,
        num_layers,
        max_length=512
    ):
        super().__init__()

        self.embedding=Embedding(
            vocab_size,
            embedding_dim
        )

        self.position=PositionalEncoding(
            embedding_dim,
            max_length
        )

        self.blocks=nn.ModuleList([
            TransformerBlock(
                embedding_dim,
                num_heads,
                hidden_dim
            )
            for _ in range(num_layers)
        ])

        self.output=nn.Linear(
            embedding_dim,
            vocab_size
        )

    def forward(self,x):
        x=self.embedding(x)

        x=self.position(x)

        for block in self.blocks:
            x=block(x)

        logits=self.output(x)

        return logits