from __future__ import annotations

import threading
from typing import Callable


class Debouncer:
    """Call ``func`` after ``wait`` seconds have passed without a new trigger."""

    def __init__(self, func: Callable[[], None], wait: float = 0.3):
        self.func = func
        self.wait = wait
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def trigger(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.wait, self.func)
            self._timer.daemon = True
            self._timer.start()
