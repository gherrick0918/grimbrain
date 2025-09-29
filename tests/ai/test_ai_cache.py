import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from grimbrain.ai import CacheInputs, call_with_cache, make_cache_key


def _inputs(prompt: str = "Hello", **param_overrides) -> CacheInputs:
    params = {
        "temperature": 0.7,
        "top_p": None,
        "presence_penalty": None,
        "frequency_penalty": None,
        "seed": None,
    }
    params.update(param_overrides)
    return CacheInputs(
        model="gpt-test",
        messages=[{"role": "user", "content": prompt}],
        tools=None,
        params=params,
        style="grim",
    )


def _read_index(cache_dir) -> dict:
    path = cache_dir / "index.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("GRIMBRAIN_AI_DISABLE_CACHE", raising=False)
    monkeypatch.delenv("GRIMBRAIN_AI_REFRESH_CACHE", raising=False)
    monkeypatch.delenv("GRIMBRAIN_AI_CACHE_MAX_BYTES", raising=False)
    monkeypatch.delenv("GRIMBRAIN_AI_CACHE_TTL_DAYS", raising=False)


def test_returns_cached_result(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    calls: list[str] = []

    def generator():
        calls.append("x")
        return "cached text"

    inputs = _inputs()
    out1 = call_with_cache(inputs, generator)
    out2 = call_with_cache(inputs, generator)

    assert out1 == out2 == "cached text"
    assert len(calls) == 1
    idx = _read_index(tmp_path)
    entry = next(iter(idx["entries"].values()))
    assert entry["hits"] == 2


def test_different_params_produce_different_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    calls: list[str] = []

    def generator(label: str):
        def inner():
            calls.append(label)
            return label

        return inner

    inputs_a = _inputs("Hello", temperature=0.5)
    inputs_b = _inputs("Hello", temperature=0.9)

    out_a = call_with_cache(inputs_a, generator("A"))
    out_b = call_with_cache(inputs_b, generator("B"))

    assert {out_a, out_b} == {"A", "B"}
    assert calls == ["A", "B"]
    assert make_cache_key(inputs_a) != make_cache_key(inputs_b)
    txt_files = {p.name for p in tmp_path.glob("*.txt")}
    assert len(txt_files) == 2


def test_concurrent_calls_share_single_write(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    calls: list[str] = []

    def generator():
        calls.append("hit")
        return "value"

    inputs = _inputs("Concurrency test")

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: call_with_cache(inputs, generator), range(5)))

    assert results == ["value"] * 5
    assert calls == ["hit"]  # generator executed once
    idx = _read_index(tmp_path)
    key = make_cache_key(inputs)
    assert idx["entries"][key]["hits"] == 5


def test_stale_index_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    inputs = _inputs("Stale")
    key = make_cache_key(inputs)
    index_path = tmp_path / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 2,
                "entries": {
                    key: {
                        "filename": f"{key}.txt",
                        "model": "gpt-test",
                        "created_at": "2000-01-01T00:00:00+00:00",
                        "last_hit_at": "2000-01-01T00:00:00+00:00",
                        "hits": 1,
                        "size": 123,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    calls: list[str] = []

    def generator():
        calls.append("fresh")
        return "new text"

    out = call_with_cache(inputs, generator)
    assert out == "new text"
    assert calls == ["fresh"]
    idx = _read_index(tmp_path)
    entry = idx["entries"][key]
    assert entry["hits"] == 1
    assert (tmp_path / f"{key}.txt").read_text(encoding="utf-8") == "new text"


def test_disable_and_refresh_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    inputs = _inputs()

    calls: list[str] = []

    def generator():
        value = f"value-{len(calls)}"
        calls.append(value)
        return value

    monkeypatch.setenv("GRIMBRAIN_AI_DISABLE_CACHE", "1")
    out1 = call_with_cache(inputs, generator)
    out2 = call_with_cache(inputs, generator)
    assert out1 == "value-0"
    assert out2 == "value-1"
    assert not (tmp_path / "index.json").exists()

    monkeypatch.setenv("GRIMBRAIN_AI_DISABLE_CACHE", "0")
    out3 = call_with_cache(inputs, generator)
    assert out3 == "value-2"

    monkeypatch.setenv("GRIMBRAIN_AI_REFRESH_CACHE", "1")
    out4 = call_with_cache(inputs, generator)
    assert out4 == "value-3"

    monkeypatch.delenv("GRIMBRAIN_AI_REFRESH_CACHE", raising=False)
    out5 = call_with_cache(inputs, generator)
    assert out5 == "value-3"
    assert calls == ["value-0", "value-1", "value-2", "value-3"]
    idx = _read_index(tmp_path)
    entry = next(iter(idx["entries"].values()))
    assert entry["hits"] == 2


def test_eviction_respects_max_bytes(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("GRIMBRAIN_AI_CACHE_MAX_BYTES", "60")

    def generator_factory(label: str):
        payload = label * 40

        def inner():
            return payload

        return inner

    inputs_a = _inputs("A")
    inputs_b = _inputs("B")
    inputs_c = _inputs("C")

    call_with_cache(inputs_a, generator_factory("A"))  # ~1 byte
    call_with_cache(inputs_b, generator_factory("B"))
    call_with_cache(inputs_c, generator_factory("C"))

    idx = _read_index(tmp_path)
    assert len(idx["entries"]) <= 2
    existing_files = {p.name for p in tmp_path.glob("*.txt")}
    assert len(existing_files) == len(idx["entries"])
