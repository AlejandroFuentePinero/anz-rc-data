"""The build: the raw folder, the RC list and the curation file in, the site's data bundle out."""

import json
import shutil
from pathlib import Path

from anzrc import identity, rcs
from anzrc.melee import round_ids

BUNDLE = Path("site/data")
CURATION = Path("data/curation.toml")


def _rows(folder: Path, kind: str, round_id: str) -> list[dict]:
    return json.loads((folder / f"{kind}-{round_id}.json").read_text())["data"]


def _username(entry: dict) -> str:
    return entry["Team"]["Players"][0]["Username"]


def _finish(rank: int | None) -> str | None:
    """Rank in the final standings. Melee's order inside the Top 4 and the Top 8 is arbitrary, so those read as tiers."""
    if rank is None:
        return None
    if rank <= 8:
        return {1: "Title", 2: "Finalist", 3: "Top 4", 4: "Top 4"}.get(rank, "Top 8")
    suffix = "th" if rank % 100 in (11, 12, 13) else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix}"


# W-L-D counts every draw, Intentional Draws included; a Match not played is in no record.
RECORD = {"Win": 0, "Loss": 1, "Draw": 2, "Intentional Draw": 2}


def _sides(match: dict) -> list[tuple[dict, str, str | None]]:
    """Each side of a Match with its result and its game score (wins-losses-draws), as that Player sees it.

    Not played: a single side (a bye of either kind, the late-entry forfeit, "not reported") or no result.
    """
    sides = match["Competitors"]
    if len(sides) == 1:
        if match["ByeReason"] is not None:
            result = "Bye"
        elif match["LossReason"] is not None:
            result = "Forfeit"
        else:
            result = "Not reported"
        return [(sides[0], result, None)]
    if not match["HasResult"]:
        return [(side, "No result", None) for side in sides]
    wins = [side["GameWins"] or 0 for side in sides]  # a loser's null game count reads as 0
    draws = match["GameDraws"] or 0
    played = []
    for me, mine, theirs in ((sides[0], wins[0], wins[1]), (sides[1], wins[1], wins[0])):
        if mine == theirs:
            result = "Intentional Draw" if mine == 0 and draws == 3 else "Draw"
        else:
            result = "Win" if mine > theirs else "Loss"
        played.append((me, result, f"{mine}-{theirs}-{draws}"))
    return played


PLAYOFF_ROUNDS = ["Quarterfinal", "Semifinal", "Final"]


def _load(raw: Path, rc_list: Path) -> list[dict]:
    """Every RC with its rounds, Matches and final standings, as Melee shapes."""
    loaded = []
    for rc in rcs.load(rc_list):
        folder = Path(raw) / str(rc["melee_id"])
        ids = round_ids((folder / "event.html").read_text())
        # Swiss and playoff rounds are told apart by the standings' matching method; round names vary between events.
        playoff = [_rows(folder, "standings", r)[0]["MatchingMethodDescription"] == "Playoffs/Top Cut" for r in ids]
        names = [f"Round {n}" for n in range(1, playoff.count(False) + 1)] + PLAYOFF_ROUNDS[len(PLAYOFF_ROUNDS) - playoff.count(True):]
        rounds = [{"name": name, "matches": _rows(folder, "matches", r)} for name, r in zip(names, ids, strict=True)]
        loaded.append(rc | {"rounds": rounds, "standings": _rows(folder, "standings", ids[-1])})
    return loaded


def _accounts(loaded: list[dict]) -> dict[str, dict]:
    """Every Melee account in any RC's standings or Matches, with the Cycles it played in order."""
    accounts = {}
    for rc in loaded:
        entries = rc["standings"] + [side for round_ in rc["rounds"] for match in round_["matches"] for side in match["Competitors"]]
        for entry in entries:
            player = entry["Team"]["Players"][0]
            account = accounts.setdefault(player["Username"], {"display_name": player["DisplayName"], "cycles": []})
            if rc["cycle"] not in account["cycles"]:
                account["cycles"].append(rc["cycle"])
    return accounts


def build(raw: Path, rc_list: Path, curation: Path, out: Path) -> None:
    loaded = _load(raw, rc_list)
    players = identity.players(_accounts(loaded), identity.load_curation(curation))
    rc_rows, cards = [], {}

    def card(entry: dict) -> dict:
        player = players[_username(entry)]
        return cards.setdefault(player["slug"], player | {"rcs": [], "matches": []})

    for rc in loaded:
        standings = rc["standings"]
        champion = next(row for row in standings if row["Rank"] == 1)
        rc_rows.append(
            {
                "cycle": rc["cycle"],
                "date": rc["start_date"],
                "city": rc["city"] or None,
                "format": rc["format"],
                "field_size": len(standings),
                "champion": champion["Team"]["Players"][0]["DisplayName"],
            }
        )
        # Every Player of the RC: the final standings, and anyone missing from them who kept their Matches.
        rc_players = {_username(row): {"entry": row, "rank": row["Rank"], "decklists": row["Decklists"]} for row in standings}
        records = {}
        for round_ in rc["rounds"]:
            for match in round_["matches"]:
                sides = match["Competitors"]
                for me, result, games in _sides(match):
                    rc_players.setdefault(_username(me), {"entry": me, "rank": None, "decklists": me["Decklists"]})
                    them = next((side for side in sides if side is not me), None)
                    opponent = card(them) if them else None
                    card(me)["matches"].append(
                        {
                            "cycle": rc["cycle"],
                            "round": round_["name"],
                            "opponent": opponent and {"slug": opponent["slug"], "name": opponent["name"]},
                            "result": result,
                            "games": games,
                        }
                    )
                    if result in RECORD:
                        records.setdefault(_username(me), [0, 0, 0])[RECORD[result]] += 1
        for username, rc_player in rc_players.items():
            deck = rc_player["decklists"][0] if rc_player["decklists"] else None
            card(rc_player["entry"])["rcs"].append(
                {
                    "cycle": rc["cycle"],
                    "date": rc["start_date"],
                    "format": rc["format"],
                    "finish": _finish(rc_player["rank"]),
                    "field_size": len(standings),
                    "record": "-".join(map(str, records.get(username, [0, 0, 0]))),
                    "deck": deck and deck["DecklistName"],
                    "decklist": deck and f"https://melee.gg/Decklist/View/{deck['DecklistId']}",
                }
            )

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rcs.json").write_text(json.dumps(rc_rows, indent=1) + "\n")
    shutil.rmtree(out / "players", ignore_errors=True)
    (out / "players").mkdir()
    for player in cards.values():
        (out / "players" / f"{player['slug']}.json").write_text(json.dumps(player, indent=1) + "\n")
    index = [{key: player[key] for key in ("slug", "name", "usernames")} for player in cards.values()]
    (out / "players.json").write_text(json.dumps(index, indent=1) + "\n")


def main() -> None:
    build(rcs.RAW, rcs.RC_LIST, CURATION, BUNDLE)
