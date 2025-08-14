"""Dev-friendly launcher for grimbrain.

- If you later move the CLI into the package (e.g., grimbrain/main.py),
  we call that first.
- Otherwise we execute the repo-root main.py, making sure the repo root
  is on sys.path and the CWD matches ``python main.py``.
"""

from pathlib import Path
import os
import runpy
import sys
import re  # <-- Added

# Added regex patterns
REST_RE = re.compile(r'^rest\s+(short|long)\s+([A-Za-z][\w\s\'"-]+)(?:\s+(\d+))?$', re.I)
CAST_RE = re.compile(r'^cast\s+"([^"]+)"(?:\s+"([^"]+)")?(?:\s+--level\s+(\d+))?$', re.I)
REACTION_RE = re.compile(r'^reaction\s+"([^"]+)"\s+([A-Za-z][\w\s\'"-]+)$', re.I)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # A) Prefer in-package CLI if it ever exists
    try:
        from .main import main as run  # optional future path
    except Exception:
        run = None
    if run:
        return int(run() or 0)

    # B) Dev path: locate repo root from this file (editable install)
    pkg_dir = Path(__file__).resolve().parent          # .../grimbrain
    repo_root = pkg_dir.parent                         # repo root
    root_main = repo_root / "main.py"
    if root_main.exists():
        # Ensure `import content`, `import engine`, etc. resolve
        sys.path.insert(0, str(repo_root))

        # Make relative paths/logging match `python main.py`
        old_cwd = os.getcwd()
        try:
            os.chdir(repo_root)
            # Keep CLI args intact for main.py
            runpy.run_path(str(root_main), run_name="__main__")
        finally:
            os.chdir(old_cwd)
        return 0

    # C) Friendly error if neither path exists
    print(
        "grimbrain: could not locate CLI. Run from the repo root, "
        "or move the CLI into the package (grimbrain/main.py).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
