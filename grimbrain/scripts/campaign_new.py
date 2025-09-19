import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import typer

from grimbrain.engine.campaign import CampaignState, PartyMemberRef, save_campaign
from grimbrain.engine.characters import load_pc

app = typer.Typer(help="Create a new campaign file.")


@app.command()
def run(
    path: str = typer.Argument(...),
    seed: int = 4242,
    party: str | None = typer.Option(
        None, "--party", help="Comma-separated PC JSON paths"
    ),
):
    if party:
        members = []
        for pc_path in party.split(","):
            pc_path = pc_path.strip()
            if not pc_path:
                continue
            members.append(load_pc(pc_path))
    else:
        members = [
            PartyMemberRef(
                id="PC1",
                name="Fighter",
                str_mod=3,
                dex_mod=1,
                con_mod=2,
                int_mod=0,
                wis_mod=0,
                cha_mod=0,
                ac=16,
                max_hp=24,
                pb=2,
                speed=30,
                weapon_primary="Longsword",
            ),
            PartyMemberRef(
                id="PC2",
                name="Archer",
                str_mod=0,
                dex_mod=3,
                con_mod=1,
                int_mod=0,
                wis_mod=0,
                cha_mod=0,
                ac=14,
                max_hp=16,
                pb=2,
                speed=30,
                ranged=True,
                weapon_primary="Longbow",
            ),
        ]
    st = CampaignState(seed=seed, party=members)
    save_campaign(st, path)
    print(f"Wrote {path}")


if __name__ == "__main__":
    app()
