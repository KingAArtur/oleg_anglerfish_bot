import pytest

from src.modules import NGramTalkModule


@pytest.fixture()
def ngram_module() -> NGramTalkModule:
    module = NGramTalkModule(n=2)
    module.learn_text("first", "Я люблю кошек. И её.")
    module.learn_text("second", "Я люблю гулять.")

    return module


def assert_compare_counts(real: dict[tuple[str, ...], dict[str, int]], expected: dict[tuple[str, ...], dict[str, int]]):
    for ngram in real:
        assert ngram in expected

        for next_word, cnt in real[ngram].items():
            assert next_word in expected[ngram]
            assert expected[ngram][next_word] == cnt

    for ngram in expected:
        assert ngram in real

        for next_word, cnt in expected[ngram].items():
            assert next_word in real[ngram]
            assert real[ngram][next_word] == cnt


def test_learn_text(ngram_module):
    expected_counts = {
        ("я",): {"люблю": 2},
        ("я", "люблю"): {"кошек": 1, "гулять": 1},
        ("люблю",): {"кошек": 1, "гулять": 1},
        ("люблю", "кошек"): {".": 1},
        ("кошек",): {".": 1},
        ("кошек", "."): {"и": 1},
        (".",): {"и": 1},
        (".", "и"): {"её": 1},
        ("и",): {"её": 1},
        ("и", "её"): {".": 1},
        ("её",): {".": 1},
        ("люблю", "гулять"): {".": 1},
        ("гулять",): {".": 1},
    }

    assert_compare_counts(ngram_module.ngrams_to_next_word_counts, expected_counts)


def test_forget_text(ngram_module):
    ngram_module.forget_text("first")

    expected_counts = {
        ("я",): {"люблю": 1},
        ("я", "люблю"): {"гулять": 1},
        ("люблю",): {"гулять": 1},
        ("люблю", "гулять"): {".": 1},
        ("гулять",): {".": 1},
    }

    assert_compare_counts(ngram_module.ngrams_to_next_word_counts, expected_counts)


def test_forget_text_not_found(ngram_module):
    with pytest.raises(KeyError) as e:
        ngram_module.forget_text("third")

    assert "third" in e.value.args[0]


def test_generate_sentence(ngram_module):
    reply_words = ngram_module._generate_sentence_from_words_list(["Я"], n_max_words=1)
    assert reply_words == ["я", "люблю", "."]


def test_generate_text(ngram_module):
    text = "Эти слова не важны. Я!"
    reply_texts = {
        ngram_module.generate_text(text, n_last_words=1)
        for _ in range(100)
    }
    assert "Я люблю кошек." in reply_texts
    assert "Я люблю гулять." in reply_texts


def test_serialize(ngram_module):
    serialized = ngram_module.serialize_to_text()
    new_ngram_module = NGramTalkModule(n=ngram_module.n)
    new_ngram_module.deserialize_from_text(serialized)

    expected_counts = {
        ("я",): {"люблю": 2},
        ("я", "люблю"): {"кошек": 1, "гулять": 1},
        ("люблю",): {"кошек": 1, "гулять": 1},
        ("люблю", "кошек"): {".": 1},
        ("кошек",): {".": 1},
        ("кошек", "."): {"и": 1},
        (".",): {"и": 1},
        (".", "и"): {"её": 1},
        ("и",): {"её": 1},
        ("и", "её"): {".": 1},
        ("её",): {".": 1},
        ("люблю", "гулять"): {".": 1},
        ("гулять",): {".": 1},
    }

    assert_compare_counts(new_ngram_module.ngrams_to_next_word_counts, expected_counts)


def test_serialize_ngram():
    ngram = ("abc", "a#a", "a,a,a", '"aaa"', '"r#r"', "42", "#a")
    assert NGramTalkModule.deserialize_ngram(NGramTalkModule.serialize_ngram(ngram)) == ngram
