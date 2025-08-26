.PHONY: setup test fmt cov golden rules play
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -e . && pip install pre-commit && pre-commit install

test:
        pytest -q

fmt:
	ruff --fix . || true
	black .
	isort .

rules:
        python -m grimbrain content --reload

play:
        python -m grimbrain play --pc pc_wizard.json --encounter goblin --packs srd --seed 1 --md-out outputs/run.md --json-out logs/run.ndjson

cov:
        pytest --cov=grimbrain --cov-report=term-missing

golden:
        pytest -q tests/test_golden_encounter.py -q
