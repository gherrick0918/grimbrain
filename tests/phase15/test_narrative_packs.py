from grimbrain.engine.narrator import pick_template_line


def test_pick_template_line_deterministic():
    ctx = {
        "lead": "Aria",
        "lead_race": "Human",
        "lead_background": "Soldier",
        "lead_race_hook": "Human ",
        "lead_background_hook": "Soldier ",
        "time": "morning",
        "location": "Wilderness",
    }
    a = pick_template_line("classic", "travel_start", ctx, seed=123)
    b = pick_template_line("classic", "travel_start", ctx, seed=123)
    c = pick_template_line("classic", "travel_start", ctx, seed=124)
    assert a == b and a != c
