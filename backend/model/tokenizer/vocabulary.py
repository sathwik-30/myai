class Vocabulary:
    def __init__(self):
        self.token_to_id={}
        self.id_to_token={}

        self.add_token("<PAD>")
        self.add_token("<UNK>")
        self.add_token("<BOS>")
        self.add_token("<EOS>")

    def add_token(self,token):
        if token not in self.token_to_id:
            idx=len(self.token_to_id)
            self.token_to_id[token]=idx
            self.id_to_token[idx]=token

    def build(self,tokens):
        for token in tokens:
            self.add_token(token)

    def encode(self,tokens):
        return [
            self.token_to_id.get(token,self.token_to_id["<UNK>"])
            for token in tokens
        ]

    def decode(self,ids):
        return [
            self.id_to_token.get(idx,"<UNK>")
            for idx in ids
        ]

    def __len__(self):
        return len(self.token_to_id)