"""The committed raw data against the sources file (docs/sources.md)."""

import json
import re
from pathlib import Path

from anzrc import rcs
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
