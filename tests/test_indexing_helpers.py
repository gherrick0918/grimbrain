from grimbrain.retrieval import indexing


def test_calculate_sha256(tmp_path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("abc")
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert indexing.calculate_sha256(file_path) == expected


def test_load_and_save_hash_cache(tmp_path, monkeypatch):
    cache_file = tmp_path / "hash.json"
    monkeypatch.setattr(indexing, "HASH_CACHE_FILE", str(cache_file))
    data = {"a": "b"}
    indexing.save_hash_cache(data)
    assert cache_file.exists()
    assert indexing.load_hash_cache() == data


def test_wipe_chroma_store(tmp_path, monkeypatch):
    store_dir = tmp_path / "chroma_store"
    store_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    log = []
    indexing.wipe_chroma_store(log)
    assert not store_dir.exists()
    assert log == [
        {
            "file": "ALL",
            "entries": 0,
            "collection": "ALL",
            "status": "Wiped Chroma store",
        }
    ]


def test_flatten_field():
    assert indexing.flatten_field({"a": 1, "b": 2}) == "a: 1, b: 2"
    assert indexing.flatten_field("value") == "value"
