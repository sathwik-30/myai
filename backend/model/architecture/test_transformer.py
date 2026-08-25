import torch
from backend.model.architecture.transformer import Transformer

vocab_size=100
embedding_dim=32
num_heads=4
hidden_dim=128
num_layers=2
sequence_length=10

model=Transformer(
    vocab_size=vocab_size,
    embedding_dim=embedding_dim,
    num_heads=num_heads,
    hidden_dim=hidden_dim,
    num_layers=num_layers,
    max_length=sequence_length
)

x=torch.randint(
    0,
    vocab_size,
    (1,sequence_length)
)

output=model(x)

print("Input shape:",x.shape)
print("Output shape:",output.shape)
print("Model parameters:",sum(p.numel() for p in model.parameters()))