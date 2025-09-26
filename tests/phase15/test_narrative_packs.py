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
    a_text, a_tpl = pick_template_line("classic", "travel_start", ctx, seed=123)
    b_text, b_tpl = pick_template_line("classic", "travel_start", ctx, seed=123)
    c_text, c_tpl = pick_template_line("classic", "travel_start", ctx, seed=124)
    assert a_text == b_text and a_tpl == b_tpl
    assert a_text != c_text or a_tpl != c_tpl
