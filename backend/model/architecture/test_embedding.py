import torch
from backend.model.architecture.embedding import Embedding

vocab_size=20
embedding_dim=8

model=Embedding(vocab_size,embedding_dim)

tokens=torch.tensor([[4,5,6,7]])

output=model(tokens)

print("Input:",tokens)
print("Output shape:",output.shape)
print("Embeddings:")
print(output)