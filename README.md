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
   Golden files under `tests/golden` lock in expected output.
3. **Play a fight**
   ```bash
   python main.py --play --pc pc_wizard.json --encounter "goblin" --packs srd --seed 1
   ```
   Use `--seed` for deterministic combat. Handy commands in play mode:
   `status`, `actions [pc]`, `attack <target> "<attack>"`, `cast "<spell>" [all|<target>]`, `end`, `save <path>`.

To continue a campaign:
```bash
python main.py --play --pc pc_wizard.json --encounter "goblin" \
  --campaign campaign.yaml --packs srd,homebrew --seed 1 --autosave
```
`campaign.yaml`:
```yaml
name: demo
party_files:
  - pc_wizard.json
quests:
  - id: q1
    title: Defeat the goblins
```

`pc_wizard.json`:
```json
{
  "party": [
    {
      "name": "Elora",
      "ac": 12,
      "hp": 8,
      "attacks": [
        {"name": "Fire Bolt", "to_hit": 5, "damage_dice": "1d10", "type": "spell"},
        {"name": "Quarterstaff", "to_hit": 2, "damage_dice": "1d6", "type": "melee"}
      ]
    }
  ]
}
```

## Python API
```python
from grimbrain.retrieval.query_router import run_query
md, js, prov = run_query("goblin", type="monster")
```
`md` is markdown, `js` is a sidecar dict, and `prov` lists provenance strings. The
function always returns a `(markdown, json, provenance)` tuple.

## Output flags
- `--json-out` optionally takes a path (defaults to `logs/last_sidecar.json`)
- `--md-out` writes the markdown output
- `--play` enables interactive combat
- `--autosave` appends turn summaries to paired markdown/JSON logs
