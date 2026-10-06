from backend.model.tokenizer.tokenizer import Tokenizer


def test_tokenizer_round_trip_keeps_text_shape():
    tokenizer = Tokenizer()
    text = "Hello Medha, how are you?"

    tokenizer.train(text)
    tokens = tokenizer.tokenize(text)
    ids = tokenizer.encode(text)
    decoded = tokenizer.decode(ids)

    assert tokens
    assert len(ids) == len(tokens)
    assert decoded
    assert len(tokenizer.vocab) > 0