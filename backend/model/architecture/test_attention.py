import torch
from backend.model.architecture.attention import SelfAttention

embedding_dim=8
num_heads=2
sequence_length=4
batch_size=1

attention=SelfAttention(
    embedding_dim,
    num_heads
)

x=torch.randn(
    batch_size,
    sequence_length,
    embedding_dim
)

output=attention(x)

print("Input shape:",x.shape)
print("Output shape:",output.shape)
print("Output:")
print(output)