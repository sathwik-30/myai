import torch
import torch.nn as nn
from backend.model.architecture.attention import SelfAttention
from backend.model.architecture.feed_forward import FeedForward

class TransformerBlock(nn.Module):
    def __init__(self,embedding_dim,num_heads,hidden_dim):
        super().__init__()

        self.attention=SelfAttention(
            embedding_dim,
            num_heads
        )

        self.norm1=nn.LayerNorm(embedding_dim)

        self.feed_forward=FeedForward(
            embedding_dim,
            hidden_dim
        )

        self.norm2=nn.LayerNorm(embedding_dim)

    def forward(self,x):
        attention_output=self.attention(x)

        x=self.norm1(
            x+attention_output
        )

        feed_forward_output=self.feed_forward(x)

        x=self.norm2(
            x+feed_forward_output
        )

        return x