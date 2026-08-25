import re
from backend.model.tokenizer.vocabulary import Vocabulary

class Tokenizer:
    def __init__(self):
        self.vocab=Vocabulary()

    def tokenize(self,text):
        text=text.lower()
        return re.findall(r"\w+|[^\w\s]",text)

    def train(self,text):
        tokens=self.tokenize(text)
        self.vocab.build(tokens)

    def encode(self,text):
        tokens=self.tokenize(text)
        return self.vocab.encode(tokens)

    def decode(self,ids):
        tokens=self.vocab.decode(ids)
        return " ".join(tokens)