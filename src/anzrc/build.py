"""The build: the raw folder, the RC list and the curation file in, the site's data bundle out."""

import json
import shutil
import statistics
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
        return {1: "Winner", 2: "Runner-up", 3: "Top 4", 4: "Top 4"}.get(rank, "Top 8")
    suffix = "th" if rank % 100 in (11, 12, 13) else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix}"


def _finish_share(rank: int | None, field_size: int) -> float | None:
    """A Finish as a share of the Field Size, the Top 4 and Top 8 tiers counted at their midpoints 3.5 and 6.5."""
    if rank is None:
        return None
    return round(100 * {3: 3.5, 4: 3.5}.get(rank, 6.5 if 5 <= rank <= 8 else rank) / field_size, 1)


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
TIERS = ["Winner", "Runner-up", "Top 4", "Top 8"]  # the Top 8's Finishes, best first
TOP_8 = set(TIERS)


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
    # Global from every Match, and each Format from its own Matches only.
    views: dict[str, dict[str, float]] = {"Global": {}}
    after_rc: dict[str, dict[str, list[dict]]] = {}  # each view's Ratings after every RC a Player was in

    def card(entry: dict) -> dict:
        player = players[_username(entry)]
        return cards.setdefault(player["slug"], player | {"rcs": [], "matches": []})

    for rc in loaded:
        standings = rc["standings"]
        winner, runner_up = (
            {key: players[_username(row)][key] for key in ("slug", "name")} for row in sorted(standings, key=lambda row: row["Rank"])[:2]
        )
        rc_rows.append(
            {
                "cycle": rc["cycle"],
                "date": rc["start_date"],
                "city": rc["city"] or None,
                "format": rc["format"],
                "field_size": len(standings),
                "winner": winner,
                "runner_up": runner_up,
            }
        )
        # Every Player of the RC: the final standings, and anyone missing from them who kept their Matches.
        rc_players = {_username(row): {"entry": row, "rank": row["Rank"], "decklists": row["Decklists"]} for row in standings}
        records = {}
        format_view = ratings.rated_by(rc["format"])
        # The views this RC shows, Global and its Format, each read from the Ratings that Format shows.
        view_sources = (("Global", "Global"), (rc["format"], format_view))
        at_start = {source: dict(views.get(source, {})) for _, source in view_sources}
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
                        view: round(views.get(source, {}).get(opponent["slug"], ratings.START), 2) for view, source in view_sources
                    }
                    # A Player plays once a round and Ratings move at its end, so this is what the Match moves, and
                    # the Player's Rating after it.
                    change, rating_after = None, None
                    if result in SCORE:
                        before = {view: views.get(source, {}).get(card(me)["slug"], ratings.START) for view, source in view_sources}
                        moved = {
                            view: ratings.move(before[view], views.get(source, {}).get(opponent["slug"], ratings.START), SCORE[result])
                            for view, source in view_sources
                        }
                        change = {view: round(moved[view], 2) for view in moved}
                        rating_after = {view: round(before[view] + moved[view], 2) for view in moved}
                    card(me)["matches"].append(
                        {
                            "cycle": rc["cycle"],
                            "round": round_["name"],
                            "playoff": round_["name"] in PLAYOFF_ROUNDS,
                            "opponent": opponent and {"slug": opponent["slug"], "name": opponent["name"]},
                            "result": result,
                            "games": games,
                            "reconstructed": match.get("Reconstructed", False),
                            "opponent_rating": opponent_rating,
                            "change": change,
                            "rating_after": rating_after,
                        }
                    )
                    if result in RECORD:
                        records.setdefault(_username(me), [0, 0, 0])[RECORD[result]] += 1
                    if result in SCORE and me is sides[0]:
                        rated.append((players[_username(me)]["slug"], opponent["slug"], SCORE[result]))
            for view in ("Global", rc["format"]):
                ratings.play_round(views.setdefault(view, {}), rated)
        history[-1]["players"] = list(dict.fromkeys(players[username]["slug"] for username in rc_players))
        # The field's Global Ratings after the RC: its typical Player, the Rating a tenth of it reached, and its highest.
        field_ratings = [views["Global"].get(slug, ratings.START) for slug in history[-1]["players"]]
        rc_rows[-1]["field_rating"] = {
            "median": round(statistics.median(field_ratings), 2),
            "top_10": round(statistics.quantiles(field_ratings, n=10, method="inclusive")[-1], 2),
            "highest": round(max(field_ratings), 2),
        }
        for view in ("Global", rc["format"]):
            for slug in history[-1]["players"]:
                rating = views[view].get(slug, ratings.START)
                after_rc.setdefault(view, {}).setdefault(slug, []).append({"cycle": rc["cycle"], "rating": rating})
        for username, rc_player in rc_players.items():
            deck = rc_player["decklists"][0] if rc_player["decklists"] else None
            slug = card(rc_player["entry"])["slug"]
            wins, losses, _ = records.get(username, [0, 0, 0])
            card(rc_player["entry"])["rcs"].append(
                {
                    "cycle": rc["cycle"],
                    "date": rc["start_date"],
                    "format": rc["format"],
                    "finish": _finish(rc_player["rank"]),
                    "top_8": _finish(rc_player["rank"]) in TOP_8,
                    "field_size": len(standings),
                    "finish_share": _finish_share(rc_player["rank"], len(standings)),
                    "record": "-".join(map(str, records.get(username, [0, 0, 0]))),
                    "win_rate": _win_rate(wins, losses),
                    "rating_start": {view: round(at_start[source].get(slug, ratings.START), 2) for view, source in view_sources},
                    "rating_end": {view: round(views[source].get(slug, ratings.START), 2) for view, source in view_sources},
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
        player["summary"] = {view: _summary(player, view) for view in player["ratings"]}
        player["head_to_head"] = _head_to_head(player)
    _rank(cards)
    return rc_rows, cards, history


def _win_rate(wins: int, losses: int) -> dict:
    """Wins over wins plus losses, with that count as the sample: draws are in neither."""
    return {"rate": round(100 * wins / (wins + losses), 1) if wins + losses else None, "matches": wins + losses}


def _summary(player: dict, view: str) -> dict:
    """A Player's results in one view: Global, or one Format's RCs and Matches only."""
    rcs_ = [rc for rc in player["rcs"] if view in ("Global", rc["format"])]
    cycles = {rc["cycle"] for rc in rcs_}
    record = [0, 0, 0]
    for match in player["matches"]:
        if match["cycle"] in cycles and match["result"] in RECORD:
            record[RECORD[match["result"]]] += 1
    wins, losses = record[0], record[1]
    finished = [rc for rc in rcs_ if rc["finish"] is not None]
    # Best Finish: the Top 8 tiers in order first, then the best share of the field.
    best = min(finished, key=lambda rc: (TIERS.index(rc["finish"]) if rc["finish"] in TOP_8 else len(TIERS), rc["finish_share"]), default=None)
    return {
        "record": "-".join(map(str, record)),
        "win_rate": _win_rate(wins, losses),
        "rcs": len(rcs_),
        "top_8s": sum(rc["finish"] in TOP_8 for rc in rcs_),
        "finals": sum(rc["finish"] in TIERS[:2] for rc in rcs_),
        "best_finish": best and best["finish"],
        # Typical Finish read as the share of the field it finishes above.
        "typical_finish_above": round(100 - statistics.median(rc["finish_share"] for rc in finished), 1) if finished else None,
    }


def _head_to_head(player: dict) -> dict[str, str]:
    """The Player's W-L-D against every opponent they met, across every Format."""
    records: dict[str, list[int]] = {}
    for match in player["matches"]:
        if match["result"] in RECORD:
            records.setdefault(match["opponent"]["slug"], [0, 0, 0])[RECORD[match["result"]]] += 1
    return {slug: "-".join(map(str, record)) for slug, record in records.items()}


def _rank(cards: dict[str, dict]) -> None:
    """Each Player's rank in every view they are eligible in (the cutoff's RCs or more), else none."""
    for view in {view for player in cards.values() for view in player["summary"]}:
        in_view = [player for player in cards.values() if view in player["summary"]]
        eligible = [player["ratings"][view]["rating"] for player in in_view if player["summary"][view]["rcs"] >= ratings.CUTOFF]
        for player in in_view:
            summary = player["summary"][view]
            mine = player["ratings"][view]["rating"]
            summary["rank"] = 1 + sum(other > mine for other in eligible) if summary["rcs"] >= ratings.CUTOFF else None


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
    (out / "community.json").write_text(json.dumps(_community(rc_rows, cards), indent=1) + "\n")
    (out / "leaderboard.json").write_text(json.dumps(_leaderboard(cards), indent=1) + "\n")


TOP = 50  # the Players a Leaderboard shows


def _leaderboard(cards: dict[str, dict]) -> dict[str, list[dict]]:
    """The top eligible Players by Rating in Global and each shipped Format anyone played, ties in name order."""
    played = {view for player in cards.values() for view in player["summary"]}
    boards = {}
    for view in ["Global", *sorted(ratings.FORMAT_RATINGS & played)]:
        ranked = [player for player in cards.values() if player["summary"].get(view, {}).get("rank")]
        ranked.sort(key=lambda player: (player["summary"][view]["rank"], player["name"]))
        boards[view] = []
        for player in ranked[:TOP]:
            summary, rating = player["summary"][view], player["ratings"][view]
            boards[view].append(
                {"rank": summary["rank"], "slug": player["slug"], "name": player["name"], "rating": rating["rating"], "peak": rating["peak"]}
                | {key: summary[key] for key in ("record", "win_rate", "rcs", "top_8s", "finals", "best_finish")}
                | {"last_rc": max(rc["cycle"] for rc in player["rcs"] if view in ("Global", rc["format"]))}
            )
    return boards


# Experience: how many RCs an RC is for a Player, across every Format, in these levels.
LEVELS = ["1st", "2nd-3rd", "4th-7th", "8th+"]
LEVEL_RCS = ["1", "2-3", "4-7", "8+"]  # each level as the RCs it spans


def _level(nth: int) -> int:
    return 0 if nth == 1 else 1 if nth <= 3 else 2 if nth <= 7 else 3


def _community(rc_rows: list[dict], cards: dict[str, dict]) -> dict:
    """The scene across every RC: each field by experience, and the Top 8 rate at each level of experience.

    The rate leaves out the first RC, where everyone is at their first by construction, established Players too.
    """
    fields = {rc["cycle"]: [0] * len(LEVELS) for rc in rc_rows}
    entries, top_8s = [0] * len(LEVELS), [0] * len(LEVELS)  # an entry is one Player at one RC
    for player in cards.values():
        for nth, rc in enumerate(player["rcs"], start=1):
            level = _level(nth)
            fields[rc["cycle"]][level] += 1
            if rc["cycle"] != rc_rows[0]["cycle"]:
                entries[level] += 1
                top_8s[level] += rc["finish"] in TOP_8
    def rate(top: int, n: int) -> dict:
        """Top 8s over Entries, and how many times the rate at a first RC that is."""
        if not n:
            return {"top_8s": top, "entries": n, "rate": None, "vs_first": None}
        first = top_8s[0] / entries[0] if entries[0] else 0
        return {"top_8s": top, "entries": n, "rate": round(100 * top / n, 1), "vs_first": round(top / n / first, 1) if first else None}

    return {
        "levels": LEVELS,
        "field_by_experience": [
            {"cycle": cycle, "players": counts, "shares": [round(100 * n / sum(counts), 1) for n in counts]}
            for cycle, counts in fields.items()
        ],
        "top_8_rate_by_experience": [
            {"level": name, "rcs": span} | rate(top, n) for name, span, top, n in zip(LEVELS, LEVEL_RCS, top_8s, entries)
        ],
    }


def main() -> None:
    build(rcs.RAW, rcs.RC_LIST, CURATION, BUNDLE)
