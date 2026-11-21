"""The build: the raw folder, the RC list and the curation file in, the site's data bundle out."""

import json
import shutil
from collections import Counter
from pathlib import Path

from anzrc import identity, ratings, rcs
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
# Only a played Match moves a Rating: Intentional Draws and anything not played move nothing.
SCORE = {"Win": 1, "Loss": 0, "Draw": 0.5}


# A 0-0-3 is an Intentional Draw where Players still in the hunt for the Top 8 agree to one: the last two Swiss rounds
# at these tables. Anywhere else it is a played draw. mtgeloproject draws the line the same way (the owner's ruling).
LATE_ROUNDS, TOP_TABLES = 2, 8


def _sides(match: dict, where: str, late_round: bool, curated_draw: bool) -> list[tuple[dict, str, str | None]]:
    """Each side of a Match with its result and its game score (wins-losses-draws), as that Player sees it.

    Not played: a single side (a bye of either kind, the late-entry forfeit, "not reported"). A Match Melee left
    unconfirmed counts by its game score like any other (the owner's ruling: Cycle 13's 0-0-1 is a played draw), but a
    Match with no games recorded at all has no result to count and stops the build for a ruling. A 0-0-3 is an
    Intentional Draw at a top table in a late round, or where the curation names it; anywhere else a played draw.
    """
    sides = match["Competitors"]
    if match.get("Reconstructed"):  # winner first, and no game score
        return [(sides[0], "Win", None), (sides[1], "Loss", None)]
    if len(sides) == 1:
        if match["ByeReason"] is not None:
            result = "Bye"
        elif match["LossReason"] is not None:
            result = "Forfeit"
        else:
            result = "Not reported"
        return [(sides[0], result, None)]
    wins = [side["GameWins"] or 0 for side in sides]  # a loser's null game count reads as 0
    draws = match["GameDraws"] or 0
    if not any(wins) and not draws:
        raise ValueError(f"{where}: a Match with no games recorded needs a ruling in the curation file")
    agreed = curated_draw or (late_round and match["TableNumber"] <= TOP_TABLES)
    played = []
    for me, mine, theirs in ((sides[0], wins[0], wins[1]), (sides[1], wins[1], wins[0])):
        if mine == theirs:
            result = "Intentional Draw" if mine == 0 and draws == 3 and agreed else "Draw"
        else:
            result = "Win" if mine > theirs else "Loss"
        played.append((me, result, f"{mine}-{theirs}-{draws}"))
    return played


PLAYOFF_ROUNDS = ["Quarterfinal", "Semifinal", "Final"]


# Seeding from the end-of-Swiss standings, 1 v 8 and so on, the winners meeting in this order. Every complete bracket follows it.
QUARTERFINALS = [(1, 8), (4, 5), (2, 7), (3, 6)]


def _rebuild_playoffs(rc: dict, swiss_standings: list[dict]) -> None:
    """Fill the playoff rounds Melee holds no Matches for, a lost final or a whole lost bracket.

    The bracket is seeded from the end-of-Swiss standings, and each Match's winner is the Player whose final rank
    shows them going on: the Top 4 out of a quarterfinal, the Top 2 out of a semifinal, the Title out of the final.
    So a rebuilt final is always the rank 1 Player beating the rank 2 Player.
    """
    playoffs = [round_ for round_ in rc["rounds"] if round_["name"] in PLAYOFF_ROUNDS]
    if all(round_["matches"] for round_ in playoffs):
        return
    final_rows = {_username(row): row for row in rc["standings"]}
    seeds = {row["Rank"]: final_rows[_username(row)] for row in swiss_standings if row["Rank"] <= 8}
    pairs = [(seeds[a], seeds[b]) for a, b in QUARTERFINALS]
    for round_, going_on in zip(playoffs, (4, 2, 1), strict=True):
        matches = []
        for a, b in pairs:
            if (a["Rank"] <= going_on) == (b["Rank"] <= going_on):
                raise ValueError(f"Cycle {rc['cycle']}: the final standings do not fit a seeded bracket at {_username(a)} v {_username(b)}")
            matches.append({"Competitors": [a, b] if a["Rank"] <= going_on else [b, a], "Reconstructed": True})
        if not round_["matches"]:
            round_["matches"] = matches
        winners = [match["Competitors"][0] for match in matches]
        pairs = list(zip(winners[::2], winners[1::2]))


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
        _rebuild_playoffs(loaded[-1], _rows(folder, "standings", ids[playoff.count(False) - 1]))
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


def replayed(raw: Path, rc_list: Path, curation: Path) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """The RC table, every Player's card, and each RC's rated Matches round by round, as the Ratings replay them."""
    loaded = _load(raw, rc_list)
    curated = identity.load_curation(curation)
    players = identity.players(_accounts(loaded), curated)
    # 0-0-3s the curation calls Intentional Draws outside the late top tables, each to be found among the Matches.
    agreed = {(draw["cycle"], f"Round {draw['round']}", draw["table"]) for draw in curated["intentional_draws"]}
    found = set()
    rc_rows, cards, history = [], {}, []
    seen = set()  # every Player at an earlier RC
    # Global from every Match, and each Format from its own Matches only.
    views: dict[str, dict[str, float]] = {"Global": {}}
    after_rc: dict[str, dict[str, list[dict]]] = {}  # each view's Ratings after every RC a Player was in

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
                "champion": {key: players[_username(champion)][key] for key in ("slug", "name")},
            }
        )
        # Every Player of the RC: the final standings, and anyone missing from them who kept their Matches.
        rc_players = {_username(row): {"entry": row, "rank": row["Rank"], "decklists": row["Decklists"]} for row in standings}
        records = {}
        format_view = ratings.rated_by(rc["format"])
        history.append({"cycle": rc["cycle"], "format": rc["format"], "rounds": []})
        swiss = [round_["name"] for round_ in rc["rounds"] if round_["name"].startswith("Round")]
        for round_ in rc["rounds"]:
            rated = []
            history[-1]["rounds"].append(rated)
            for match in round_["matches"]:
                sides = match["Competitors"]
                where = (rc["cycle"], round_["name"], match.get("TableNumber"))
                late_round = round_["name"] in swiss[-LATE_ROUNDS:]
                for me, result, games in _sides(match, "Cycle {} {} table {}".format(*where), late_round, where in agreed):
                    if result == "Intentional Draw" and where in agreed:
                        found.add(where)
                    rc_players.setdefault(_username(me), {"entry": me, "rank": None, "decklists": me["Decklists"]})
                    them = next((side for side in sides if side is not me), None)
                    opponent = card(them) if them else None
                    # The opponent's Ratings as the round started, in Global and in the RC's Format as its card shows them.
                    opponent_rating = opponent and {
                        view: round(views.get(source, {}).get(opponent["slug"], ratings.START), 2)
                        for view, source in (("Global", "Global"), (rc["format"], format_view))
                    }
                    card(me)["matches"].append(
                        {
                            "cycle": rc["cycle"],
                            "round": round_["name"],
                            "opponent": opponent and {"slug": opponent["slug"], "name": opponent["name"]},
                            "result": result,
                            "games": games,
                            "reconstructed": match.get("Reconstructed", False),
                            "opponent_rating": opponent_rating,
                        }
                    )
                    if result in RECORD:
                        records.setdefault(_username(me), [0, 0, 0])[RECORD[result]] += 1
                    if result in SCORE and me is sides[0]:
                        rated.append((players[_username(me)]["slug"], opponent["slug"], SCORE[result]))
            for view in ("Global", rc["format"]):
                ratings.play_round(views.setdefault(view, {}), rated)
        history[-1]["players"] = list(dict.fromkeys(players[username]["slug"] for username in rc_players))
        # A New Player is one at their first RC; everyone the RC has counts, the standings-missing included.
        new = set(history[-1]["players"]) - seen
        rc_rows[-1] |= {"new_players": len(new), "returning_players": len(history[-1]["players"]) - len(new)}
        seen |= new
        for view in ("Global", rc["format"]):
            for slug in history[-1]["players"]:
                rating = views[view].get(slug, ratings.START)
                after_rc.setdefault(view, {}).setdefault(slug, []).append({"cycle": rc["cycle"], "rating": rating})
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

    if agreed - found:
        named = ", ".join("Cycle {} {} table {}".format(*draw) for draw in sorted(agreed - found))
        raise ValueError(f"The curation's intentional draws name no 0-0-3: {named}")
    for player in cards.values():
        def view_rating(view):
            points = after_rc[view][player["slug"]]
            return {
                "rating": round(points[-1]["rating"], 2),
                "peak": round(max(point["rating"] for point in points), 2),
                "after_rc": [point | {"rating": round(point["rating"], 2)} for point in points],
            }

        player["ratings"] = {"Global": view_rating("Global")}
        for format_ in dict.fromkeys(rc["format"] for rc in player["rcs"]):
            player["ratings"][format_] = view_rating(ratings.rated_by(format_)) | {"rated_by": ratings.rated_by(format_)}
    return rc_rows, cards, history


def build(raw: Path, rc_list: Path, curation: Path, out: Path) -> None:
    rc_rows, cards, _ = replayed(raw, rc_list, curation)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rcs.json").write_text(json.dumps(rc_rows, indent=1) + "\n")
    shutil.rmtree(out / "players", ignore_errors=True)
    (out / "players").mkdir()
    for player in cards.values():
        (out / "players" / f"{player['slug']}.json").write_text(json.dumps(player, indent=1) + "\n")
    index = [{key: player[key] for key in ("slug", "name", "usernames")} for player in cards.values()]
    (out / "players.json").write_text(json.dumps(index, indent=1) + "\n")
    # How many Players have played each number of RCs, in Global and in each Format's RCs alone.
    rcs_played = {}
    for view in ["Global", *dict.fromkeys(rc["format"] for rc in rc_rows)]:
        counts = Counter(sum(view in ("Global", rc["format"]) for rc in player["rcs"]) for player in cards.values())
        rcs_played[view] = [{"rcs": n, "players": counts[n]} for n in sorted(counts) if n]
    (out / "community.json").write_text(json.dumps({"rcs_played": rcs_played}, indent=1) + "\n")


def main() -> None:
    build(rcs.RAW, rcs.RC_LIST, CURATION, BUNDLE)
