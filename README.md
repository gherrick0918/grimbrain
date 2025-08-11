# Grimbrain
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

## Quickstart (90 seconds)

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run tests**
   ```bash
   pytest
   ```
3. **Sample query**
   ```bash
   python main.py --scene "market brawl" --json-out logs/side.json --md-out logs/side.md
   ```
   This prints a formatted entry and writes the markdown and sidecar JSON to disk.
4. **Python API**
   ```python
   from query_router import run_query
   md, js, prov = run_query("goblin", type="monster")
   ```
   `md` is markdown, `js` a sidecar dict, and `prov` a list of provenance strings. For spells:
   ```python
   md, js, prov = run_query("fireball", type="spell")
   ```
   The ``run_query`` function always returns a tuple ``(markdown, json, provenance)``.

5. **Combat round**
   ```bash
   python main.py --pc tests/pc.json --encounter "goblin" --rounds 1
   ```
   This loads PCs from ``pc.json``, runs a single combat round against a goblin and prints the log.

   Example ``pc.json``:
   ```json
   [
     {"name": "Hero1", "ac": 15, "hp": 20,
      "attacks": [{"name": "Sword", "to_hit": 5, "damage_dice": "1d8+3", "type": "melee"}]},
     {"name": "Hero2", "ac": 15, "hp": 20,
      "attacks": [{"name": "Axe", "to_hit": 5, "damage_dice": "1d8+3", "type": "melee"}]}
   ]
   ```

   Sample output:
   ```
   Goblin hits Hero for 5
   Hero misses Goblin
   ```

### Embeddings flag

Use `--embeddings` to select embedding mode:
- `auto` (default) – use BGE small if available
- `bge-small` – require the BGE small model
- `none` – disable embeddings and suppress warnings

### Output flags

- `--json-out` optionally takes a path (defaults to `logs/last_sidecar.json`)
- `--md-out` writes the markdown output
