import pytest

from grimbrain.retrieval.utils import (
    strip_markup,
    normalize_name,
    fmt_sources,
    coerce_obj,
    ordinal,
    hit_text,
)


class DummyNode:
    def __init__(self, text: str):
        self.text = text


class DummyNodeWithScore:
    def __init__(self, node):
        self.node = node


def test_strip_markup_removes_tags_and_formatting():
    text = "This is **bold** and _italic_ {@atk mw}\n\n\nNew"
    expected = "This is bold and italic \n\nNew"
    assert strip_markup(text) == expected


def test_normalize_name_cleans_markup_and_punctuation():
    assert normalize_name(" **Goblin** ") == "goblin"
    assert normalize_name("(Goblin)") == "goblin"


def test_fmt_sources_filters_and_joins():
    assert fmt_sources(["A", "", None, "B"]) == "_Sources considered:_ A · B"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Fireball", {"text": "Fireball"}),
        (["a", "b"], {"text": ["a", "b"]}),
        ({"name": "Fireball"}, {"name": "Fireball"}),
        (None, {}),
    ],
)
def test_coerce_obj(value, expected):
    assert coerce_obj(value) == expected


@pytest.mark.parametrize(
    "num,expected",
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (-1, "-1st"),
        ("abc", "abc"),
    ],
)
def test_ordinal(num, expected):
    assert ordinal(num) == expected


def test_hit_text_handles_various_inputs():
    node = DummyNode("hello")
    hit = DummyNodeWithScore(node)
    assert hit_text(hit) == "hello"
    assert hit_text({"text": "hi"}) == "hi"
    assert hit_text("raw") == "raw"
