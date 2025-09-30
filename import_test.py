import sys
import importlib
import pathlib

print("--- sys.path[0] (CWD):", pathlib.Path(sys.path[0]).resolve())
print("--- First 5 sys.path entries:")
for p in sys.path[:5]:
    print("   ", pathlib.Path(p).resolve())
print("--- Import grimbrain ...")
try:
    m = importlib.import_module("grimbrain")
    print("grimbrain.__file__:", pathlib.Path(m.__file__).resolve())
    try:
        mp = importlib.import_module("grimbrain.scripts.campaign_play")
        print("campaign_play.__file__:", pathlib.Path(mp.__file__).resolve())
        print("has 'app' attr:", hasattr(mp, "app"))
    except Exception as e:
        print("import error:", e)
except Exception as e:
    print("import error:", e)