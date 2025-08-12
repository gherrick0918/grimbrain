from pathlib import Path
import runpy, sys

def main() -> None:
    # If you later move the CLI into the package (grimbrain/main.py), prefer it.
    try:
        from .main import main as run  # optional future path
        run()
        return
    except Exception:
        pass

    # Dev path: resolve repo root from this file's location, not CWD.
    pkg_dir = Path(__file__).resolve().parent      # .../grimbrain
    repo_root = pkg_dir.parent                     # repo root
    root_main = repo_root / "main.py"
    if root_main.exists():
        runpy.run_path(str(root_main), run_name="__main__")
        return

    print("grimbrain: CLI not found. Run from the repo root or move the CLI into the package.", file=sys.stderr)
    sys.exit(2)
