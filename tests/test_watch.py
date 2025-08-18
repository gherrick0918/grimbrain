import time

from grimbrain.content.watch import Debouncer


def test_debouncer(monkeypatch):
    calls = []

    deb = Debouncer(lambda: calls.append(1), wait=0.05)
    deb.trigger()
    deb.trigger()
    time.sleep(0.1)
    assert calls == [1]
