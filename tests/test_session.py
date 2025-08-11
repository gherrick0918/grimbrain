import json
from grimbrain.engine.session import Session


def test_session_save_load(tmp_path):
    path = tmp_path / "sess.json"
    s = Session.start("market brawl", seed=123)
    s.log_step("look around", "you see stalls")
    s.save(path)

    loaded = Session.load(path)
    loaded.log_step("buy", "apple")
    loaded.save(path)

    data = json.loads(path.read_text())
    assert data["seed"] == 123
    assert data["scene"] == "market brawl"
    assert len(data["steps"]) == 2
