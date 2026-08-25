import torch
import torch.nn as nn
import math

class SelfAttention(nn.Module):
    def __init__(self,embedding_dim,num_heads):
        super().__init__()

        if embedding_dim%num_heads!=0:
            raise ValueError("embedding_dim must be divisible by num_heads")

        self.embedding_dim=embedding_dim
        self.num_heads=num_heads
        self.head_dim=embedding_dim//num_heads

        self.query=nn.Linear(embedding_dim,embedding_dim)
        self.key=nn.Linear(embedding_dim,embedding_dim)
        self.value=nn.Linear(embedding_dim,embedding_dim)

        self.output=nn.Linear(embedding_dim,embedding_dim)

    def forward(self,x):
        batch_size,sequence_length,_=x.shape

        q=self.query(x)
        k=self.key(x)
        v=self.value(x)

        q=q.view(
            batch_size,
            sequence_length,
            self.num_heads,
            self.head_dim
        ).transpose(1,2)

        k=k.view(
            batch_size,
            sequence_length,
            self.num_heads,
            self.head_dim
        ).transpose(1,2)

        v=v.view(
            batch_size,
            sequence_length,
            self.num_heads,
            self.head_dim
        ).transpose(1,2)

        scores=torch.matmul(q,k.transpose(-2,-1))
        scores=scores/math.sqrt(self.head_dim)

        attention=torch.softmax(scores,dim=-1)

        output=torch.matmul(attention,v)

        output=output.transpose(1,2).contiguous()

        output=output.view(
            batch_size,
            sequence_length,
            self.embedding_dim
        )

        return self.output(output)