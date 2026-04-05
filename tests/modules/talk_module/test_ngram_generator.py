import pytest
from collections import defaultdict

from src.modules.talk import NGramGenerator


@pytest.fixture
def ngram_generator() -> NGramGenerator:
    generator = NGramGenerator(n=2)
    generator.learn_text("first", ["Я", "люблю", "кошек", ".", "И", "её", "."])
    generator.learn_text("second", ["Я", "люблю", "гулять", "."])

    return generator


def assert_compare_counts(
    real: dict[tuple[str, ...], dict[str, float]],
    expected: dict[tuple[str, ...], dict[str, float]],
):
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


def test_learn_text(ngram_generator):
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

    assert_compare_counts(ngram_generator.ngrams_to_next_word_counts, expected_counts)


def test_forget_text(ngram_generator):
    ngram_generator.forget_text("first")

    expected_counts = {
        ("я",): {"люблю": 1},
        ("я", "люблю"): {"гулять": 1},
        ("люблю",): {"гулять": 1},
        ("люблю", "гулять"): {".": 1},
        ("гулять",): {".": 1},
    }

    assert_compare_counts(ngram_generator.ngrams_to_next_word_counts, expected_counts)


def test_forget_text_not_found(ngram_generator):
    with pytest.raises(KeyError) as e:
        ngram_generator.forget_text("third")

    assert "third" in e.value.args[0]


def test_generate_word(ngram_generator):
    words = ["Я"]
    result = ngram_generator.generate_word(words)
    assert result == "люблю"

    words = ["люблю", "кошек"]
    result = ngram_generator.generate_word(words)
    assert result == "."


def test_generate_word__random(ngram_generator):
    words = ["Я", "люблю"]

    results = defaultdict(int)
    n = 1000
    for _ in range(n):
        result = ngram_generator.generate_word(words)
        results[result] += 1

    assert results["кошек"] + results["гулять"] == n
    assert abs(results["кошек"] / n - 0.5) < 0.1
    assert abs(results["гулять"] / n - 0.5) < 0.1


def test_serialize(ngram_generator):
    serialized_text = ngram_generator.serialize_to_text()
    new_ngram_module = NGramGenerator.deserialize_from_text(serialized_text)

    assert_compare_counts(new_ngram_module.ngrams_to_next_word_counts, ngram_generator.ngrams_to_next_word_counts)


def test_serialize_ngram():
    ngram = ("abc", "a#a", "a,a,a", '"aaa"', '"r#r"', "42", "#a")
    assert NGramGenerator.deserialize_ngram(NGramGenerator.serialize_ngram(ngram)) == ngram
