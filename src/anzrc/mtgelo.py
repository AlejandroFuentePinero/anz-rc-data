"""Fetch mtgeloproject's own record of every ANZ RC Match, the oracle the Rating rule is checked against.

mtgeloproject keeps every RC since 2022, ANZ ones included, and its public API gives each person's Matches with
their rating before and after and the opponent's rating before. Starting from one ANZ Player, the crawl follows
opponents through the ANZ RCs only, one request at a time with a delay, skipping anyone already stored. Each response
is kept as sent, in data/mtgeloproject/<person id>.json, and the RC codes in events.json.
"""

import json
import re
import time
from pathlib import Path

ORACLE = Path("data/mtgeloproject")
API = "https://mtgeloproject.net/api/players"
SEED = "x54o5ss2"  # an ANZ Player with ten of the RCs


def event_codes(events: dict, melee_ids: set[int]) -> dict[str, int]:
    """mtgeloproject's code for each RC on the list, read from the Melee link of a person's events."""
    codes = {}
    for event in events["data"]:
        found = re.fullmatch(r"https://melee\.gg/Tournament/View/(\d+)", event["site"] or "")
        if found and int(found.group(1)) in melee_ids:
            codes[event["code"]] = int(found.group(1))
    return codes


def crawl(melee_ids: set[int], folder: Path, http, delay: float = 1.5) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    codes_path = folder / "events.json"
    codes = json.loads(codes_path.read_text()) if codes_path.exists() else {}

    def get(url) -> bytes:
        body = http.get(url)
        time.sleep(delay)
        return body

    queue, seen = [SEED], {SEED}
    while queue:
        person = queue.pop()
        path = folder / f"{person}.json"
        if path.exists():
            matches = json.loads(path.read_text())
        else:
            body = get(f"{API}/{person}/matches")
            matches = json.loads(body)
            path.write_bytes(body)
            if len(codes) < len(melee_ids) and set(matches) - set(codes):
                codes |= event_codes(json.loads(get(f"{API}/{person}/events")), melee_ids)
                codes_path.write_text(json.dumps(codes, indent=1, sort_keys=True) + "\n")
            print(f"{len(seen)} seen, {len(queue)} queued: {person}", flush=True)
        for code, rows in matches.items():
            if code not in codes:
                continue
            for row in rows:
                opponent = (row.get("opp_data") or {}).get("id")
                if opponent and opponent not in seen:
                    seen.add(opponent)
                    queue.append(opponent)


def main() -> None:
    from anzrc import rcs
    from anzrc.fetch import Melee

    crawl({rc["melee_id"] for rc in rcs.load()}, ORACLE, Melee())
