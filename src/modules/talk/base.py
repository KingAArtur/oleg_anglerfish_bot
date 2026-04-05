import nltk


nltk.download('punkt_tab')
PUNKT_END_OF_SENTENCE = {".", "?", "!", "..."}


def tokenize(text: str) -> list[str]:
    return nltk.word_tokenize(text)


def detokenize(tokens: list[str]) -> str:
    return nltk.tokenize.treebank.TreebankWordDetokenizer().detokenize(tokens)
