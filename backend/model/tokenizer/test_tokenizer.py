from backend.model.tokenizer.tokenizer import Tokenizer

tokenizer=Tokenizer()

text="Hello Medha, how are you?"

tokenizer.train(text)

tokens=tokenizer.tokenize(text)
ids=tokenizer.encode(text)
decoded=tokenizer.decode(ids)

print("Tokens:",tokens)
print("IDs:",ids)
print("Decoded:",decoded)
print("Vocabulary size:",len(tokenizer.vocab))