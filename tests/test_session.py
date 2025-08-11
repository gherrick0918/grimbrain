from engine.session import start_scene


def test_start_scene_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    md, js = start_scene("market brawl")
    assert md.exists()
    assert js.exists()
