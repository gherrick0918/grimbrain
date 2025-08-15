from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Optional project imports; provide fallbacks so this script runs standalone in tests.
try:
    from grimbrain.content import load_packs  # type: ignore
except Exception:  # pragma: no cover
    def load_packs(_names: List[str]) -> Dict[str, dict]:
        return {}

try:
    from grimbrain.monsters import parse_monster_spec, MonsterSidecar, select_monster  # type: ignore
except Exception:  # pragma: no cover
    @dataclass
    class MonsterSidecar:  # type: ignore
        name: str = "Goblin"
        ac: int = 15
        hp: int = 6
        attacks: list = None
        dex_mod: int = 2
        str_mod: int = 0

    def parse_monster_spec(spec: str, _lookup) -> List[Any]:  # type: ignore
        n = 1
        m = re.search(r"x\s*(\d+)", spec)
        if m:
            n = int(m.group(1))
        name = spec.split("x")[0].strip().title() or "Goblin"
        attacks = [{"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}]
        return [MonsterSidecar(name=name, ac=15, hp=6, attacks=attacks) for _ in range(n)]

    def select_monster(*_args, **_kwargs):  # type: ignore
        return "goblin"


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1]
    return s


def _d(n: int, rng: random.Random) -> int:
    return rng.randint(1, n)


def _roll_expr(expr: str, rng: random.Random) -> int:
    m = re.fullmatch(r"\s*(\d+)d(\d+)([+-]\d+)?\s*", expr)
    if not m:
        raise ValueError(f"Bad dice: {expr}")
    nd, sides, mod = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    total = sum(_d(sides, rng) for _ in range(nd)) + mod
    return total


@dataclass
class Combatant:
    name: str
    ac: int
    hp: int
    attacks: List[dict]
    side: str
    dex_mod: int = 0
    str_mod: int = 0
    max_hp: Optional[int] = None
    defeated: bool = False
    init: int = 0
    downed: bool = False
    stable: bool = False
    death_successes: int = 0
    death_failures: int = 0

    def __post_init__(self):
        if self.max_hp is None:
            self.max_hp = self.hp


@dataclass
class ActionState:
    dodge: bool = False
    hidden: bool = False
    help_advantage_token: bool = False


@dataclass
class ConditionFlags:
    prone: bool = False
    restrained: bool = False
    frightened: bool = False
    grappled: bool = False


def _serialize_combatant(c: Combatant) -> dict:
    return {
        "name": c.name,
        "ac": c.ac,
        "hp": c.hp,
        "side": c.side,
        "dex_mod": c.dex_mod,
        "str_mod": c.str_mod,
        "attacks": c.attacks,
        "defeated": c.defeated,
        "init": c.init,
        "downed": c.downed,
        "stable": c.stable,
        "ds_success": c.death_successes,
        "ds_fail": c.death_failures,
        "max_hp": c.max_hp,
    }


def _deserialize_combatants(data: List[dict]) -> List[Combatant]:
    res: List[Combatant] = []
    for d in data:
        c = Combatant(
            name=d["name"],
            ac=d["ac"],
            hp=d["hp"],
            attacks=d.get("attacks", []),
            side=d.get("side", "party"),
            dex_mod=d.get("dex_mod", 0),
            str_mod=d.get("str_mod", 0),
            max_hp=d.get("max_hp", d.get("hp", 0)),
        )
        c.defeated = d.get("defeated", False)
        c.init = d.get("init", 0)
        c.downed = d.get("downed", False)
        c.stable = d.get("stable", False)
        c.death_successes = d.get("ds_success", 0)
        c.death_failures = d.get("ds_fail", 0)
        res.append(c)
    return res


def _apply_damage(target: Combatant, amount: int, attack_type: str = "melee", crit: bool = False) -> None:
    if target.defeated:
        return
    target.hp -= amount
    if target.hp > 0:
        return
    target.hp = 0
    if target.downed or target.stable:
        was_stable = target.stable
        target.stable = False
        fails = 2 if crit and attack_type == "melee" else 1
        target.death_failures += fails
        if was_stable:
            print(f"{target.name} suffers {fails} failure{'s' if fails > 1 else ''}")
        else:
            print(f"{target.name} suffers {fails} death save failure{'s' if fails > 1 else ''}")
        print(f"[Downed S:{target.death_successes}/F:{target.death_failures}]")
        if target.death_failures >= 3:
            target.defeated = True
            print(f"{target.name} dies")
    else:
        target.downed = True
        target.death_successes = 0
        target.death_failures = 0
        print(f"{target.name} is downed")


def heal_target(target: Combatant, amount: int) -> str:
    if target.defeated:
        return f"{target.name} is dead."
    before = target.hp
    target.hp = min(target.hp + amount, target.max_hp or (target.hp + amount))
    cleared = False
    if before <= 0:
        target.downed = False
        target.stable = False
        target.death_successes = 0
        target.death_failures = 0
        target.defeated = False
        cleared = True
    note = "; death saves cleared" if cleared else ""
    return f"{target.name} heals {amount} (HP {before} -> {target.hp}){note}"


def _print_status(round_num: int, combatants: List[Combatant],
                  action_state: Optional[Dict[str, ActionState]] = None,
                  condition_state: Optional[Dict[str, ConditionFlags]] = None) -> None:
    print(f"Round {round_num}")
    print("Initiative: " + ", ".join(c.name for c in combatants))
    for c in combatants:
        tags = ""
        if action_state:
            st = action_state.get(c.name)
            if st:
                if st.dodge: tags += " [Dodge]"
                if st.hidden: tags += " [Hidden]"
                if st.help_advantage_token: tags += " [Help]"
        if condition_state:
            cf = condition_state.get(c.name)
            if cf:
                if cf.prone: tags += " [Prone]"
                if cf.restrained: tags += " [Restrained]"
                if cf.frightened: tags += " [Frightened]"
                if cf.grappled: tags += " [Grappled]"
        if c.defeated:
            tags += " [Dead]"
        elif c.hp <= 0:
            if c.stable:
                tags += " [Stable]"
            else:
                tags += f" [Downed S:{c.death_successes}/F:{c.death_failures}]"
        print(f"{c.name}: {c.hp} HP, AC {c.ac}{tags}")


def _save_game(path: str, seed: Optional[int], round_num: int, turn: int,
               combatants: List[Combatant],
               conditions: Optional[Dict[str, ConditionFlags]] = None) -> None:
    state = {
        "seed": seed,
        "round": round_num,
        "turn": turn,
        "combatants": [_serialize_combatant(c) for c in combatants],
        "conditions": {k: vars(v) for k, v in (conditions or {}).items()},
    }
    Path(path).write_text(json.dumps(state))


def _load_game(path: str) -> tuple[Optional[int], int, int, List[Combatant], Dict[str, ConditionFlags]]:
    d = json.loads(Path(path).read_text())
    seed = d.get("seed")
    rn = d.get("round", 1)
    turn = d.get("turn", 0)
    cmb = _deserialize_combatants(d.get("combatants", []))
    cond = {k: ConditionFlags(**v) for k, v in d.get("conditions", {}).items()}
    return seed, rn, turn, cmb, cond


ATTACK_RE = re.compile(
    r'^(?:a|attack)\s+'
    r'(?:(?P<actor>\w+)\s+)?'
    r'(?P<target>[^"]+?)\s+'
    r'"(?P<attack>[^"]+)"'
    r'(?:\s+(?P<adv>adv|dis))?$', re.I
)

CAST_RE = re.compile(
    r'^(?:c|cast)\s+"(?P<spell>[^"]+)"\s+(?P<target>all|[^"]+)$', re.I
)


def play_cli(pcs_raw: List[dict],
             monsters_raw: List[Any],
             seed: Optional[int] = None,
             max_rounds: int = 20,
             autosave: bool = False,
             script: Optional[Any] = None) -> None:
    rng = random.Random(seed)
    if seed is not None:
        print(f"Using seed: {seed}")

    combatants: List[Combatant] = []
    for pc in pcs_raw:
        combatants.append(Combatant(
            name=pc["name"], ac=pc["ac"], hp=pc["hp"],
            attacks=pc.get("attacks", []), side="party",
            dex_mod=pc.get("dex_mod", 0), str_mod=pc.get("str_mod", 0),
            max_hp=pc.get("max_hp", pc["hp"])
        ))
    for m in monsters_raw:
        name = getattr(m, "name", "Monster")
        ac = getattr(m, "ac", 12)
        hp = getattr(m, "hp", 5)
        attacks = getattr(m, "attacks", [])
        dex_mod = getattr(m, "dex_mod", 0)
        str_mod = getattr(m, "str_mod", 0)
        combatants.append(Combatant(name=name, ac=ac, hp=hp, attacks=attacks,
                                    side="monsters", dex_mod=dex_mod, str_mod=str_mod))

    action_state: Dict[str, ActionState] = {c.name: ActionState() for c in combatants}
    condition_state: Dict[str, ConditionFlags] = {c.name: ConditionFlags() for c in combatants}

    def _find_any(name: str) -> Optional[Combatant]:
        return next((c for c in combatants if c.name == name), None)

    def _enemies_of(actor: Combatant) -> List[Combatant]:
        return [c for c in combatants if c.side != actor.side and not c.defeated and not (c.hp <= 0 and c.stable)]

    def _combine_adv(a: str, b: str) -> str:
        if a == b: return a
        if a == "normal": return b
        if b == "normal": return a
        return "normal"

    def _derive_action_adv(attacker: Combatant, defender: Combatant) -> str:
        adv = "normal"
        if action_state[defender.name].dodge:
            adv = _combine_adv(adv, "dis")
        if action_state[attacker.name].help_advantage_token:
            action_state[attacker.name].help_advantage_token = False
            adv = _combine_adv(adv, "adv")
        if action_state[attacker.name].hidden:
            adv = _combine_adv(adv, "adv")
            action_state[attacker.name].hidden = False
        return adv

    def _derive_condition_adv(attacker: Combatant, defender: Combatant, atype: str) -> str:
        adv = "normal"
        if condition_state[defender.name].prone:
            adv = _combine_adv(adv, "adv" if atype != "ranged" else "dis")
        return adv

    def _attack_do(actor: Combatant, target: Combatant, attack: dict) -> None:
        if actor.hp <= 0:
            print(f"{actor.name} is at 0 HP and cannot act")
            return
        adv = _combine_adv(
            _derive_action_adv(actor, target),
            _derive_condition_adv(actor, target, attack.get("type", "melee"))
        )
        def roll_d20():
            return _d(20, rng)
        if adv == "adv":
            face = max(roll_d20(), roll_d20())
        elif adv == "dis":
            face = min(roll_d20(), roll_d20())
        else:
            face = roll_d20()
        total = face + int(attack.get("to_hit", 0))
        crit = face == 20
        if os.getenv("GB_TESTING"):
            print(f"[dbg] adv_mode={adv}")
        if total >= target.ac:
            dmg_expr = str(attack.get("damage_dice", "1d4"))
            if crit:
                # roll dice twice (bonus added once implicitly by our simple roller)
                dmg = _roll_expr(dmg_expr, rng) + _roll_expr(dmg_expr, rng)
            else:
                dmg = _roll_expr(dmg_expr, rng)
            print(f"{actor.name} hits {target.name} for {dmg}")
            _apply_damage(target, dmg, attack.get("type", "melee"), crit)
        else:
            print(f"{actor.name} misses {target.name}")

    input_fn: Callable[[str], str]
    if script is not None:
        lines = script.readlines() if hasattr(script, "readlines") else []
        it = iter(lines)
        def scripted_input(prompt: str) -> str:
            try:
                line = next(it)
            except StopIteration:
                return "quit"
            return line.rstrip("\n")
        input_fn = scripted_input
    else:
        input_fn = lambda prompt: input(prompt)

    round_num = 1
    turn_index = 0

    order = [c for c in combatants if c.side == "party"] + [c for c in combatants if c.side == "monsters"]
    combatants = order

    while round_num <= max_rounds:
        actor = combatants[turn_index % len(combatants)]
        if actor.defeated or (actor.hp <= 0 and actor.stable):
            turn_index += 1
            if turn_index % len(combatants) == 0:
                round_num += 1
            continue

        action_state[actor.name].dodge = False

        line = input_fn("> ").strip()
        if not line:
            continue
        cmd = line
        parts = [p for p in re.split(r"\s+", cmd) if p]

        if actor.side == "party":
            if parts[0].lower() in ("status", "s", "hp"):
                _print_status(round_num, combatants, action_state, condition_state)
            elif parts[0].lower() in ("actions", "list"):
                for a in actor.attacks or []:
                    print(a.get("name", ""))
            elif parts[0].lower() == "dodge":
                action_state[actor.name].dodge = True
                print(f"{actor.name} takes the Dodge action")
            elif parts[0].lower() == "help" and len(parts) >= 2:
                ally = _find_any(parts[1])
                if not ally:
                    print("Unknown target")
                else:
                    action_state[ally.name].help_advantage_token = True
                    print(f"{actor.name} helps {ally.name}")
            elif parts[0].lower() == "hide":
                action_state[actor.name].hidden = True
                print(f"{actor.name} hides")
            elif parts[0].lower() == "stabilize" and len(parts) >= 2:
                tgt = _find_any(parts[1])
                if not tgt:
                    print("Unknown target")
                elif tgt.defeated:
                    print(f"{tgt.name} is dead.")
                elif tgt.hp > 0:
                    print("Cannot stabilize")
                else:
                    tgt.stable = True
                    tgt.downed = True
                    print(f"{tgt.name} is stable")
            elif parts[0].lower() == "heal" and len(parts) >= 3:
                tgt = _find_any(parts[1])
                if not tgt:
                    print("Unknown target")
                elif tgt.defeated:
                    print(f"{tgt.name} is dead.")
                else:
                    try:
                        amt = int(parts[2])
                    except ValueError:
                        print("Usage: heal <target> <amount>")
                    else:
                        before = tgt.hp
                        _ = heal_target(tgt, amt)
                        print(f"{tgt.name} heals {amt}")
                        if before <= 0 and tgt.hp > 0:
                            print("death saves cleared")
            elif parts[0].lower() == "use" and "potion of healing" in cmd.lower():
                m = re.search(r'on\s+(.+)$', cmd, re.I)
                if not m:
                    print("Usage: use \"Potion of Healing\" on <target>")
                else:
                    who = _unquote(m.group(1).strip())
                    tgt = _find_any(who)
                    if not tgt:
                        print("Unknown target")
                    elif tgt.defeated:
                        print(f"{tgt.name} is dead.")
                    else:
                        rolled = _d(4, rng) + _d(4, rng) + 2
                        print(f'Potion of Healing on {tgt.name}: rolled 2d4+2 = {rolled}')
                        before = tgt.hp
                        _ = heal_target(tgt, rolled)
                        print(f"{tgt.name} heals {rolled}")
                        if before <= 0 and tgt.hp > 0:
                            print("death saves cleared")
            elif parts[0].lower() == "shove" and len(parts) >= 3:
                tgt = _find_any(parts[1])
                mode = parts[2].lower()
                if not tgt:
                    print("Unknown target")
                elif mode == "prone":
                    condition_state[tgt.name].prone = True
                    print(f"{tgt.name} is knocked prone")
                else:
                    print("Unknown command")
            elif parts[0].lower() == "stand":
                if condition_state[actor.name].prone:
                    condition_state[actor.name].prone = False
                print(f"{actor.name} stands")
            elif ATTACK_RE.match(cmd):
                m = ATTACK_RE.match(cmd)
                assert m
                actor_name = m.group("actor")
                target_name = m.group("target").strip()
                atk_name = m.group("attack")
                adv_word = (m.group("adv") or "").lower()
                atk_actor = _find_any(actor_name) if actor_name else actor
                tgt = _find_any(target_name)
                if not atk_actor or not tgt:
                    print("Unknown target")
                else:
                    atk = next((a for a in (atk_actor.attacks or []) if a.get("name","").lower()==atk_name.lower()), None)
                    if not atk:
                        print("Unknown action")
                    else:
                        if adv_word == "adv":
                            action_state[atk_actor.name].help_advantage_token = True
                        elif adv_word == "dis":
                            action_state[tgt.name].dodge = True
                        _attack_do(atk_actor, tgt, atk)
            elif CAST_RE.match(cmd):
                m = CAST_RE.match(cmd)
                assert m
                spell = m.group("spell")
                target_spec = m.group("target")
                spec = next((a for a in (actor.attacks or []) if a.get("name","").lower()==spell.lower()), None)
                if not spec:
                    print("Unknown action")
                else:
                    dmg_expr = spec.get("damage_dice", "1d6")
                    save_dc = int(spec.get("save_dc", 10))
                    save_ability = spec.get("save_ability", "dex").lower()
                    tgts: List[Combatant]
                    if target_spec.lower() == "all":
                        tgts = [c for c in _enemies_of(actor)]
                    else:
                        t = _find_any(_unquote(target_spec))
                        tgts = [t] if t else []
                    dmg_full = _roll_expr(dmg_expr, rng)
                    for t in tgts:
                        mod = getattr(t, f"{save_ability}_mod", 0)
                        face = _d(20, rng)
                        total = face + mod
                        ok = total >= save_dc
                        print(f"{save_ability.capitalize()} save {t.name} total {total} vs DC {save_dc} -> {'success' if ok else 'failure'}")
                        dealt = dmg_full//2 if ok else dmg_full
                        print(f"{spell} hits {t.name} for {dealt}")
                        _apply_damage(t, dealt, "spell", False)
            elif parts[0].lower() in ("end", "e", "next"):
                turn_index += 1
                if turn_index % len(combatants) == 0:
                    round_num += 1
            elif parts[0].lower() == "save" and len(parts) == 2:
                _save_game(parts[1], seed, round_num, turn_index, combatants, condition_state)
            elif parts[0].lower() == "load" and len(parts) == 2:
                seed, round_num, turn_index, combatants, condition_state = _load_game(parts[1])
            elif parts[0].lower() in ("quit", "q", "exit"):
                return
            elif parts[0].lower() == "help":
                print('Commands: status, dodge, help <ally>, hide, grapple <target>, shove <target> prone|push, save <target> <ability> <dc>, stand, attack <pc> <target> "<attack>" [adv|dis], cast <pc> "<spell>" [all|<target>], end, save <path>, load <path>, actions [pc], heal <target> <amount>, quit')
            else:
                print("Unknown command")
        else:
            enemies = _enemies_of(actor)
            if not enemies:
                turn_index += 1
                if turn_index % len(combatants) == 0:
                    round_num += 1
                continue
            tgt = min(enemies, key=lambda c: (c.hp, c.ac, c.name))
            if actor.attacks:
                atk = actor.attacks[0]
                _attack_do(actor, tgt, atk)
            turn_index += 1
            if turn_index % len(combatants) == 0:
                round_num += 1


def load_party_file(path: Path) -> List[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _lookup_fallback(name: str) -> MonsterSidecar:  # type: ignore
    return MonsterSidecar(name=name)  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description="Grimbrain CLI")
    parser.add_argument("--play", action="store_true", help="Run combat simulator")
    parser.add_argument("--campaign", help="Path to campaign directory or YAML", default=None)
    parser.add_argument("--start", help="Starting scene for campaign", default=None)
    parser.add_argument("--pc", help="Path to party JSON file", default=None)
    parser.add_argument("--encounter", help="Monster spec for play mode", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--packs", help="Comma-separated pack names or paths", default=None)
    parser.add_argument("--autosave", action="store_true", help="Autosave play log")
    parser.add_argument("--save", help="Path to save campaign state", default=None)
    parser.add_argument("--resume", help="Resume state JSON", default=None)
    parser.add_argument("--pc-wizard", action="store_true", help="Create party JSON interactively or from preset")
    parser.add_argument("--preset", help="Preset name for pc-wizard", default=None)
    parser.add_argument("--out", help="Output path for pc-wizard", default=None)
    parser.add_argument("--script", type=argparse.FileType("r"),
                        help="Path to a text file of commands to feed into the in-combat CLI")

    args = parser.parse_args()

    if args.pc_wizard:
        try:
            from pc_wizard import main as wizard_main  # type: ignore
        except Exception:
            print("pc_wizard not available")
            return
        wizard_main(out=args.out, preset=args.preset)  # type: ignore
        return

    if args.play:
        camp = None
        base = None
        if args.campaign:
            try:
                from grimbrain import campaign_engine  # type: ignore
            except Exception:
                campaign_engine = None  # type: ignore
            if campaign_engine:
                camp = campaign_engine.load_campaign(args.campaign)  # type: ignore
                base = Path(args.campaign).parent if Path(args.campaign).is_file() else Path(args.campaign)
        if args.pc:
            pcs = load_party_file(Path(args.pc))
        elif camp:
            pcs = campaign_engine.load_party(camp, base)  # type: ignore
        else:
            raise SystemExit("--pc is required for play mode")

        packs = load_packs(args.packs.split(",")) if args.packs else {}

        def _lookup(name: str) -> MonsterSidecar:  # type: ignore
            data = packs.get(name.lower()) if packs else None
            if data:
                return MonsterSidecar(**data)  # type: ignore
            return _lookup_fallback(name)

        encounter_spec: Any = args.encounter
        if encounter_spec is None:
            if not camp:
                raise SystemExit("--encounter is required for play mode")
            scene_id = args.start or getattr(camp, "start", None)
            visited = set()
            while True:
                scenes = getattr(camp, "scenes", {})
                scene = scenes.get(scene_id) if isinstance(scenes, dict) else None
                if not scene:
                    raise SystemExit(f"Scene '{scene_id}' not found in campaign.")
                enc = scene.get("encounter") if isinstance(scene, dict) else getattr(scene, "encounter", None)
                if enc:
                    encounter_spec = enc
                    break
                visited.add(scene_id)
                choices = scene.get("choices") if isinstance(scene, dict) else getattr(scene, "choices", None)
                if choices:
                    nxt = choices[0].get("goto") or choices[0].get("next") if isinstance(choices[0], dict) else getattr(choices[0], "goto", None) or getattr(choices[0], "next", None)
                    if not nxt or nxt in visited:
                        break
                    scene_id = nxt
                else:
                    break

        print(f"DEBUG: Encounter spec loaded: {encounter_spec}")
        if isinstance(encounter_spec, dict) and "random" in encounter_spec:
            opts = encounter_spec["random"]
            encounter_spec = select_monster(tags=opts.get("tags"), cr=opts.get("cr"), seed=args.seed)  # type: ignore

        monsters = parse_monster_spec(str(encounter_spec), _lookup)
        monsters = [m for m in monsters if m is not None]
        if not monsters:
            print(f"ERROR: No valid monsters loaded from encounter spec: {encounter_spec}")
            sys.exit(1)

        play_cli(pcs, monsters, seed=args.seed, max_rounds=args.max_rounds,
                 autosave=args.autosave, script=args.script)
        return

    if args.campaign:
        try:
            from grimbrain.main_campaign import run_campaign_cli  # type: ignore
        except Exception:
            print("Campaign mode not available")
            return
        run_campaign_cli(args.campaign, start=args.start, seed=args.seed, save=args.save,
                         resume=args.resume, max_rounds=args.max_rounds)  # type: ignore
        return

    parser.print_help()


if __name__ == "__main__":
    main()
