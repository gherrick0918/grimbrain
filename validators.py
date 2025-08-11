import json
from pathlib import Path
import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
with open(SCHEMA_DIR / "monster.json") as f:
    MONSTER_SCHEMA = json.load(f)
with open(SCHEMA_DIR / "spell.json") as f:
    SPELL_SCHEMA = json.load(f)

def validate_monster(data: dict) -> None:
    jsonschema.validate(data, MONSTER_SCHEMA)

def validate_spell(data: dict) -> None:
    jsonschema.validate(data, SPELL_SCHEMA)
