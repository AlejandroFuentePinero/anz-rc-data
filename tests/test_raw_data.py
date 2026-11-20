"""The committed raw data against the sources file (docs/sources.md)."""

import json
import re
from pathlib import Path

from anzrc import rcs
from anzrc.build import CURATION, build
from anzrc.melee import round_ids

ROOT = Path(__file__).parent.parent


def players_column() -> dict[int, int]:
    """Melee ID to the sources file's Players column."""
    rows = re.findall(r"^\| (\d+) \|[^|]*\|[^|]*\|[^|]*\| (\d+) \| \[(\d+)\]", (ROOT / "docs/sources.md").read_text(), re.M)
    return {int(melee_id): int(players) for _, players, melee_id in rows}


def rounds(melee_id: int) -> list[str]:
    return round_ids((ROOT / rcs.RAW / str(melee_id) / "event.html").read_text())


def grid(melee_id: int, name: str) -> list[dict]:
    return json.loads((ROOT / rcs.RAW / str(melee_id) / name).read_text())["data"]


def test_the_raw_data_holds_8227_matches():
    total = sum(
        len(grid(rc["melee_id"], f"matches-{r}.json")) for rc in rcs.load(ROOT / rcs.RC_LIST) for r in rounds(rc["melee_id"])
    )
    assert total == 8227


def test_every_rcs_final_standings_count_the_sources_files_players():
    expected = players_column()
    assert len(expected) == 13
    counted = {rc["melee_id"]: len(grid(rc["melee_id"], f"standings-{rounds(rc['melee_id'])[-1]}.json")) for rc in rcs.load(ROOT / rcs.RC_LIST)}
    assert counted == expected


# Decklists outside 60 or more main and 15 or fewer sideboard cards, as Melee holds them: id to (main, sideboard).
DECKLIST_COUNT_EXCEPTIONS: dict[str, tuple[int, int]] = {}


def final_decklist_ids(melee_id: int) -> list[str]:
    rows = grid(melee_id, f"standings-{rounds(melee_id)[-1]}.json")
    return [entry["DecklistId"] for row in rows for entry in row["Decklists"]]


def test_every_final_standings_decklist_is_stored():
    missing = [
        (rc["cycle"], decklist_id)
        for rc in rcs.load(ROOT / rcs.RC_LIST)
        for decklist_id in final_decklist_ids(rc["melee_id"])
        if not (ROOT / rcs.DECKLISTS / str(rc["melee_id"]) / f"{decklist_id}.json").exists()
    ]
    assert missing == []


def test_main_decks_count_60_or_more_and_sideboards_15_or_fewer_bar_the_listed_exceptions():
    outside = {}
    for path in (ROOT / rcs.DECKLISTS).glob("*/*.json"):
        deck = json.loads(path.read_text())
        main, sideboard = (sum(card["quantity"] for card in deck[part]) for part in ("main", "sideboard"))
        if main < 60 or sideboard > 15:
            outside[deck["decklist_id"]] = (main, sideboard)
    assert outside == DECKLIST_COUNT_EXCEPTIONS


def test_the_real_data_builds_921_players_with_the_six_same_real_name_pairs_joined(tmp_path):
    build(ROOT / rcs.RAW, ROOT / rcs.RC_LIST, ROOT / CURATION, tmp_path)
    index = json.loads((tmp_path / "players.json").read_text())
    by_username = {username: player for player in index for username in player["usernames"]}

    assert len(by_username) == 927
    assert len(index) == 921
    pairs = [
        ("Swiftclaw", "Swiftclaw_"),
        ("Dimmers", "Dimmer"),
        ("Pandaexpress", "RowanMillers"),
        ("Davnderp", "rdavey88"),
        ("Solarion", "Solarionmtg"),
        ("tylervisser", "tylervisserr"),
    ]
    assert all(by_username[a] is by_username[b] for a, b in pairs)
    assert by_username["alejandrofp"]["name"] == "Alejandro de la Fuente"
