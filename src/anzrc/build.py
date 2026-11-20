"""The build: the raw folder and the RC list in, the site's data bundle out."""

import json
from pathlib import Path

from anzrc import rcs
from anzrc.melee import round_ids

BUNDLE = Path("site/data")


def _final_standings(folder: Path) -> list[dict]:
    last_round = round_ids((folder / "event.html").read_text())[-1]
    return json.loads((folder / f"standings-{last_round}.json").read_text())["data"]


def build(raw: Path, rc_list: Path, out: Path) -> None:
    rows = []
    for rc in rcs.load(rc_list):
        standings = _final_standings(Path(raw) / str(rc["melee_id"]))
        champion = next(row for row in standings if row["Rank"] == 1)
        rows.append(
            {
                "cycle": rc["cycle"],
                "date": rc["start_date"],
                "city": rc["city"] or None,
                "format": rc["format"],
                "field_size": len(standings),
                "champion": champion["Team"]["Players"][0]["DisplayName"],
            }
        )
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rcs.json").write_text(json.dumps(rows, indent=1) + "\n")


def main() -> None:
    build(rcs.RAW, rcs.RC_LIST, BUNDLE)
