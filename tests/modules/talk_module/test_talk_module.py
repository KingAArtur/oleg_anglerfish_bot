import pytest

from src.modules.talk import NGramGenerator, SwearReplacer, TalkModule


@pytest.fixture
def talk_module():
    ngram_generator = NGramGenerator(n=1)
    ngram_generator.learn_text(text_id="first", text=["кошка", "любит", "собаку"])

    swear_replacer = SwearReplacer(chance_to_replace=1.0)
    swear_replacer.learn_from_list(["девочка", "маму"])

    talk_module = TalkModule(ngram_generator=ngram_generator, swear_replacer=swear_replacer)
    return talk_module


def test_talk_module(talk_module):
    text = "Кошка"
    result = talk_module.generate_text(text=text)
    assert result == "Кошка любит маму?"
