import nltk


nltk.download('punkt_tab')
PUNKT_END_OF_SENTENCE = {".", "?", "!", "..."}


def tokenize(text: str) -> list[str]:
    return nltk.word_tokenize(text)


def detokenize(tokens: list[str]) -> str:
    result = nltk.tokenize.treebank.TreebankWordDetokenizer().detokenize(tokens)
    for punkt in PUNKT_END_OF_SENTENCE:
        result = result.replace(f" {punkt}", punkt)

    result = result.replace("\n ", "\n")

    return result
