# Grimbrain

![CI](https://img.shields.io/github/actions/workflow/status/gherrick0918/grimbrain/ci.yml?branch=main)
![coverage](https://img.shields.io/badge/coverage-local-informational)

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
   python main.py play --pc pc_wizard.json --encounter "goblin" --packs srd --seed 1
   ```
   Use `--seed` for deterministic combat. Handy commands in play mode:
   `status`, `actions [pc]`, `attack <target> "<attack>"`, `cast "<spell>" [all|<target>]`, `end`, `save <path>`.

To continue a campaign:
```bash
python -m grimbrain --play --pc pc_wizard.json --encounter "goblin" \
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

### Character quickstart

Create a level‑1 Wizard:
```bash
grimbrain character create --name Elora --class Wizard --race "High Elf" \
  --background Sage --ac 12 --str 8 --dex 14 --con 12 --int 16 --wis 10 --cha 12 \
  --out pc_wizard.json
```
Level to 3:
```bash
grimbrain character level pc_wizard.json --to 3
```

Create with standard array assigned to INT, DEX, CON, STR, WIS, CHA:
```bash
grimbrain character array --name Elora --class Wizard \
  --assign int,dex,con,str,wis,cha --out pc_wizard.json
```
Create via point‑buy (27‑point):
```bash
grimbrain character pointbuy --name Nox --class Warlock --stats 15,14,13,10,10,8
```

Supports full casters (Wizard, Cleric, Druid, Sorcerer, Bard), half‑casters
(Paladin, Ranger), third‑casters (Eldritch Knight, Arcane Trickster), and
Warlock pact magic slot rules.

Create an Eldritch Knight:
```bash
grimbrain character create --name Tharn --class Fighter --subclass "Eldritch Knight" --ac 17 \
  --str 16 --dex 12 --con 14 --int 10 --wis 10 --cha 8 --out pc_tharn.json
```
Create an Arcane Trickster:
```bash
grimbrain character create --name Sable --class Rogue --subclass "Arcane Trickster" --ac 15 \
  --str 10 --dex 16 --con 12 --int 14 --wis 10 --cha 8 --out pc_sable.json
```

Render to terminal:
```bash
grimbrain character sheet pc_wizard.json --fmt tty
```
Export to Markdown:
```bash
grimbrain character sheet pc_wizard.json --fmt md --out outputs/elora_sheet.md
```
Export to PDF:
```bash
grimbrain character sheet pc_wizard.json --fmt pdf --out outputs/elora_sheet.pdf
```

Include metadata footer and show zero slots:
```bash
grimbrain character sheet pc_elora.json --fmt md --meta campaign=Starter --meta seed=1 --show-zero-slots
```

PDF with logo and metadata:
```bash
grimbrain character sheet pc_elora.json --fmt pdf --logo assets/grimbrain_logo.png \
  --meta campaign=Starter --meta seed=1 --out outputs/elora_sheet.pdf
```

### Starter equipment

Create a PC with class/background starter packs:
```bash
grimbrain character create --name Elora --class Wizard --background Sage --ac 12 \
  --str 8 --dex 14 --con 12 --int 16 --wis 10 --cha 12 --starter --out pc_elora.json
```

Apply a kit to an existing PC:

```bash
grimbrain character equip pc_elora.json --preset Wizard
grimbrain character equip pc_elora.json --preset Sage
```

Sheets will now list Languages and Tools under Proficiencies.

### Spells & Casting

Learn and prepare:
```bash
grimbrain character learn pc_elora.json --spell "Magic Missile"
grimbrain character prepare pc_elora.json --spell "Magic Missile"
```

Casting & rest:

```bash
grimbrain character cast pc_elora.json --level 1
grimbrain character rest pc_elora.json --type long
```

Get spell stats:

```bash
grimbrain character spellstats pc_elora.json
# → Spell Save DC: 13 | Spell Attack: +5
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

## Data-driven rules (Phase 7)

The new rules engine loads JSON rule documents and resolves them through a
lightweight vector search index.  Enable it by setting ``GB_ENGINE=data``:

```bash
GB_ENGINE=data python main.py rules show attack
```

Before the first run, index your rule files:

```bash
python -m grimbrain.rules.index --rules rules --out .chroma
```

At runtime you can reload rules and rebuild the index via:

```bash
GB_ENGINE=data python main.py rules reload
```

See ``schema/rule.schema.json`` for the rule document format.

Set ``GB_RULES_INSTANT_DEATH=true`` to enable the instant death variant.

### Stabilize actions

You can now stabilize a dying creature with a Medicine check or by casting *Spare the Dying*.

### Data-driven quickstart

PowerShell
```powershell
$env:GB_ENGINE="data"; $env:GB_RULES_DIR="rules"; $env:GB_CHROMA_DIR=".chroma"
python tools/convert_data_to_rules.py
python -m grimbrain.rules.index --rules $env:GB_RULES_DIR --out $env:GB_CHROMA_DIR
python .\main.py rules list
python .\main.py rules show attack.shortsword
python -m grimbrain.rules.cli "attack.shortsword Goblin"
```

bash
```bash
export GB_ENGINE="data"
export GB_RULES_DIR="rules"
export GB_CHROMA_DIR=".chroma"
python tools/convert_data_to_rules.py
python -m grimbrain.rules.index --rules "$GB_RULES_DIR" --out "$GB_CHROMA_DIR"
python main.py rules list
python main.py rules show attack.shortsword
python -m grimbrain.rules.cli "attack.shortsword Goblin"
```

## Unified content indexing

The `content` command indexes rules, monsters, spells and other docs.

```bash
export GB_ENGINE="data"
export GB_RULES_DIR="rules"
export GB_DATA_DIR="data"
export GB_CHROMA_DIR=".chroma"
python main.py content reload
python main.py content list --type monster
python main.py content show monster/monster.goblin
```

IDs are canonical (for example `monster/goblin`), but older forms remain available as aliases. If an id is unknown, the CLI now prints the nearest suggestions.

### Monsters & spells from legacy data

```bash
$env:GB_ENGINE="data"
$env:GB_RULES_DIR="data"
$env:GB_CHROMA_DIR=".chroma"
python -m grimbrain.rules.index --rules $env:GB_RULES_DIR --out $env:GB_CHROMA_DIR --adapter legacy-data
python .\main.py content list --type monster --grep goblin
python .\main.py content show spell/spell.fire.bolt
python .\main.py rules packs
```

## Auto-reload in dev

Automatically rebuild the rule index when editing files during development:

```powershell
python .\main.py rules reload --watch
```

Press <kbd>Ctrl+C</kbd> to stop watching.

## Resolver & Suggestions

| Env var | Default | Purpose |
| --- | --- | --- |
| `GB_RESOLVER_K` | `5` | Number of vector matches to query |
| `GB_RESOLVER_MIN_SCORE` | `0.45` | Base cosine similarity cutoff |
| `GB_RESOLVER_MIN_SCORE_RULE` | – | Override min score for rules |
| `GB_RESOLVER_MIN_SCORE_SPELL` | – | Override min score for spells |
| `GB_RESOLVER_MIN_SCORE_MONSTER` | – | Override min score for monsters |
| `GB_RESOLVER_WARM_COUNT` | `200` | Docs to pre-warm on reload/play |

`GB_CHROMA_DIR` controls where the vector index is persisted (default `.chroma`).
