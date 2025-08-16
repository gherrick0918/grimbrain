import json
from pathlib import Path

import jsonschema


def test_rules_validate_against_schema():
    schema = json.loads(Path('schema/rule.schema.json').read_text())
    rules_dir = Path('rules')
    for path in rules_dir.glob('*.json'):
        data = json.loads(path.read_text())
        jsonschema.validate(data, schema)
