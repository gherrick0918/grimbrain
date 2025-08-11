# Grimbrain

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
   `md` is markdown, `js` a sidecar dict, and `prov` a list of provenance strings.
   For spells:
   ```python
   md, js, prov = run_query("fireball", type="spell")
   ```

### Embeddings flag

Use `--embeddings` to select embedding mode:
- `auto` (default) – use BGE small if available
- `bge-small` – require the BGE small model
- `none` – disable embeddings and suppress warnings

### Output flags

- `--json-out` optionally takes a path (defaults to `logs/last_sidecar.json`)
- `--md-out` writes the markdown output
