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
   This prints a formatted entry and writes both markdown and JSON sidecars.
4. **Python API**
   ```python
   from grimbrain.retrieval.query_router import run_query
   md, js, prov = run_query("goblin", type="monster")
   ```
   `md` is markdown, `js` a sidecar dict, and `prov` a list of provenance strings. For spells:
   ```python
   md, js, prov = run_query("fireball", type="spell")
   ```
   The ``run_query`` function always returns a tuple ``(markdown, json, provenance)``.

5. **Play mode**
   ```bash
   python main.py --play --pc tests/pc.json --encounter "goblin" --seed 1 --autosave
   ```
   Loads PCs from ``pc.json`` and drops you into an interactive fight. Use
   shorthand commands like `a` for attack, `c` for cast, `s` for status and `q` to quit.

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

   Play mode also accepts a single character sheet JSON/YAML describing a PC. Missing
   attack bonuses and spell save DCs are derived from ability scores and proficiency.
   For longer running games, pass ``--campaign campaign.yaml`` to track quests and notes
   and to save session logs under ``campaigns/<name>/sessions``.

### Embeddings flag

Use `--embeddings` to select embedding mode:
- `auto` (default) – use BGE small if available
- `bge-small` – require the BGE small model
- `none` – disable embeddings and suppress warnings

### Output flags

- `--json-out` optionally takes a path (defaults to `logs/last_sidecar.json`)
- `--md-out` writes the markdown output
- `--play` enables interactive combat; combine with `--seed` for determinism
- `--autosave` appends turn summaries to paired markdown/JSON logs
