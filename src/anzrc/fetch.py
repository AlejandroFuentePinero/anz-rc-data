"""Fetch each RC's raw Melee responses into the repo, one folder per RC, and its decklists parsed, skipping what is stored."""

import json
import time
from pathlib import Path

from anzrc.melee import decklist, round_ids

BASE = "https://melee.gg"


# The standings endpoint answers anything short of its full column spec with a 500.
STANDINGS_COLUMNS = (
    "Rank",
    "Player",
    "Decklists",
    "MatchRecord",
    "GameRecord",
    "Points",
    "OpponentMatchWinPercentage",
    "TeamGameWinPercentage",
    "OpponentGameWinPercentage",
)


def _form(columns: tuple[str, ...], **extra: str) -> dict:
    """The form a Melee DataTables endpoint wants, asking for every row at once."""
    form = {"draw": "1", "start": "0", "length": "1000", "order[0][column]": "0", "order[0][dir]": "asc", **extra}
    for index, column in enumerate(columns):
        form |= {
            f"columns[{index}][data]": column,
            f"columns[{index}][name]": column,
            f"columns[{index}][searchable]": "true",
            f"columns[{index}][orderable]": "true",
            f"columns[{index}][search][value]": "",
            f"columns[{index}][search][regex]": "false",
        }
    return form


def _complete_grid(body: bytes) -> bool:
    """A DataTables response holding every row it counts, not an error."""
    grid = json.loads(body)
    return "Error" not in grid and grid["recordsTotal"] == len(grid["data"])


def fetch_rc(melee_id: int, raw_root: Path, decklist_root: Path, http, delay: float = 1.5) -> None:
    """Store the RC's raw responses as sent, then every decklist on its final standings, parsed."""
    folder = Path(raw_root) / str(melee_id)
    folder.mkdir(parents=True, exist_ok=True)

    def stored(name: str, request, usable=_complete_grid) -> bytes:
        path = folder / name
        if path.exists():
            return path.read_bytes()
        body = request()
        if not usable(body):
            raise RuntimeError(f"RC {melee_id}: Melee sent an unusable {name}; rerun to retry")
        path.write_bytes(body)
        time.sleep(delay)
        return body

    page = stored(
        "event.html",
        lambda: http.get(f"{BASE}/Tournament/View/{melee_id}"),
        usable=lambda body: bool(round_ids(body.decode())),
    )
    for round_id in round_ids(page.decode()):
        stored(f"matches-{round_id}.json", lambda: http.post(f"{BASE}/Match/GetRoundMatches/{round_id}", _form(("TableNumber",))))
        final_standings = stored(
            f"standings-{round_id}.json",
            lambda: http.post(f"{BASE}/Standing/GetRoundStandings", _form(STANDINGS_COLUMNS, roundId=round_id)),
        )

    # A decklist page is about 110 KB of markup around a 1 KB list, so only the parsed list is kept (issue #3).
    decklists = Path(decklist_root) / str(melee_id)
    decklists.mkdir(parents=True, exist_ok=True)
    for row in json.loads(final_standings)["data"]:
        for decklist_id in (entry["DecklistId"] for entry in row["Decklists"]):
            path = decklists / f"{decklist_id}.json"
            if path.exists():
                continue
            try:
                deck = decklist(http.get(f"{BASE}/Decklist/View/{decklist_id}").decode())
            except ValueError as error:
                raise RuntimeError(f"RC {melee_id}: decklist {decklist_id} is unreadable ({error}); rerun to retry") from error
            path.write_text(json.dumps({"decklist_id": decklist_id} | deck, indent=1, ensure_ascii=False) + "\n")
            time.sleep(delay)


class Melee:
    """The real site. Melee refuses clients without a browser user agent."""

    def __init__(self):
        import requests

        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )

    def get(self, url: str) -> bytes:
        response = self.session.get(url, timeout=90)
        response.raise_for_status()
        return response.content

    def post(self, url: str, data: dict) -> bytes:
        headers = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://melee.gg/"}
        response = self.session.post(url, data=data, timeout=90, headers=headers)
        response.raise_for_status()
        return response.content


def main() -> None:
    from anzrc import rcs

    melee = Melee()
    for rc in rcs.load():
        print(f"Cycle {rc['cycle']} ({rc['melee_id']})", flush=True)
        fetch_rc(rc["melee_id"], rcs.RAW, rcs.DECKLISTS, melee)
