import torch
from backend.model.architecture.positional_encoding import PositionalEncoding

embedding_dim=8

positional_encoding=PositionalEncoding(embedding_dim)

x=torch.randn(1,4,embedding_dim)

output=positional_encoding(x)

print("Input shape:",x.shape)
print("Output shape:",output.shape)
print("Input:")
print(x)
print("Output:")
print(output)