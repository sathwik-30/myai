import torch
from backend.model.architecture.transformer_block import TransformerBlock

embedding_dim=8
num_heads=2
hidden_dim=32

block=TransformerBlock(
    embedding_dim,
    num_heads,
    hidden_dim
)

x=torch.randn(
    1,
    4,
    embedding_dim
)

output=block(x)

print("Input shape:",x.shape)
print("Output shape:",output.shape)
print("Output:")
print(output)