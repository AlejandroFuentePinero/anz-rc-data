"""A second, independent replay of every Rating, from the raw Melee files and the written rules alone.

It shares no code with anzrc on purpose: it was first written blind by a review that never saw the build, and the
test that uses it holds the shipped bundle to it, so a change to the build's replay (K, the scale, the order of RCs or
rounds, when Ratings move, which Matches count) cannot pass unnoticed. The rules are ADR 0001's.
"""

import csv
import json
import math
import re
import tomllib
from collections import defaultdict
from pathlib import Path

K = 36
S = 200 / math.log10(1.5)


def replay(raw: Path, rc_list: Path, curation: Path) -> dict:
    """Every Player's exact Ratings, keyed by the set of their Melee usernames.

    Returns {"players": {usernames: pid}, "after_rc": {view: {pid: {cycle: rating}}},
    "start_rc": {view: {pid: {cycle: rating}}}, "sides": [one per Player per Match: cycle, playoff, round, pid,
    opponent pid, result, and per view the own and opponent Rating before and the own Rating after if rated]}.
    """
    rcs = [row | {"cycle": int(row["cycle"])} for row in csv.DictReader(open(rc_list))]
    curated = tomllib.loads(Path(curation).read_text())
    agreed = {(d["cycle"], d["round"], d["table"]) for d in curated.get("intentional_draws", [])}

    # Parse every Match, and every account's real name and Cycles.
    matches, names, cycles_of, standings = [], {}, defaultdict(set), {}
    for rc in rcs:
        cycle, folder = rc["cycle"], Path(raw) / rc["melee_id"]
        ids = list(dict.fromkeys(re.findall(r'round-selector" data-id="(\d+)"', (folder / "event.html").read_text())))
        rows, by_round = [], {}
        for rid in ids:
            stand = json.loads((folder / f"standings-{rid}.json").read_text())["data"]
            by_round[rid] = stand
            for team in [row["Team"] for row in stand] + [
                c["Team"] for m in json.loads((folder / f"matches-{rid}.json").read_text())["data"] for c in m["Competitors"]
            ]:
                for p in team["Players"]:
                    names[p["Username"]] = p["DisplayName"]
                    cycles_of[p["Username"]].add(cycle)
            rows += json.loads((folder / f"matches-{rid}.json").read_text())["data"]
        swiss = sorted({r["RoundNumber"] for r in rows if r["PhaseSortOrder"] == 1})
        for r in rows:
            users = [c["Team"]["Players"][0]["Username"] for c in r["Competitors"]]
            m = {"cycle": cycle, "format": rc["format"], "playoff": r["PhaseSortOrder"] != 1, "round": r["RoundNumber"], "users": users}
            if len(users) != 2:
                m |= {"score": None, "rated": False}
            else:
                won = re.fullmatch(r"(.*) won (\d+)-(\d+)-(\d+)", r["ResultString"])
                drawn = re.fullmatch(r"(\d+)-(\d+)-(\d+) Draw", r["ResultString"])
                wins = [c["GameWins"] or 0 for c in r["Competitors"]]
                if won:
                    m |= {"score": 1.0 if wins[0] > wins[1] else 0.0, "rated": True}
                elif drawn:
                    a, b, d = map(int, drawn.groups())
                    intentional = (a, b, d) == (0, 0, 3) and (
                        (not m["playoff"] and r["RoundNumber"] in swiss[-2:] and r["TableNumber"] <= 8)
                        or (cycle, r["RoundNumber"], r["TableNumber"]) in agreed
                    )
                    m |= {"score": 0.5, "rated": not intentional}
                else:
                    raise ValueError(f"unread result {r['ResultString']!r}")
            matches.append(m)
        key = lambda rid: (by_round[rid][0]["PhaseSortOrder"], by_round[rid][0]["RoundNumber"])
        last_swiss = max((rid for rid in ids if by_round[rid][0]["PhaseSortOrder"] == 1), key=key)
        standings[cycle] = {
            "swiss": [r["Team"]["Players"][0]["Username"] for r in sorted(by_round[last_swiss], key=lambda r: r["Rank"])],
            "final": {r["Team"]["Players"][0]["Username"]: r["Rank"] for r in by_round[max(ids, key=key)]},
            "last_swiss": swiss[-1],
        }

    # Rebuild the playoff Matches Melee lost: a seeded bracket, each winner the one ranked higher at the end.
    for rc in rcs:
        cycle, st = rc["cycle"], standings[rc["cycle"]]
        have = [m for m in matches if m["cycle"] == cycle and m["playoff"]]
        if len(have) == 7:
            continue

        def won(a, b, rn):
            return {"cycle": cycle, "format": rc["format"], "playoff": True, "round": rn, "users": [a, b],
                    "score": 1.0 if st["final"][a] < st["final"][b] else 0.0, "rated": True}

        winner = lambda m: m["users"][0] if m["score"] == 1 else m["users"][1]
        base, seeds = st["last_swiss"], st["swiss"][:8]
        semis = [m for m in have if m["round"] == base + 2]
        if not have:
            quarters = [won(seeds[a], seeds[b], base + 1) for a, b in ((0, 7), (3, 4), (1, 6), (2, 5))]
            w = [winner(m) for m in quarters]
            semis = [won(w[0], w[1], base + 2), won(w[2], w[3], base + 2)]
            matches += quarters + semis
        matches.append(won(winner(semis[0]), winner(semis[1]), base + 3))

    # Identity: curation joins, and the same real name never in one RC.
    parent = {u: u for u in names}

    def find(u):
        while parent[u] != u:
            u = parent[u]
        return u

    for group in curated.get("joins", []):
        for u in group[1:]:
            parent[find(u)] = find(group[0])
    by_name = defaultdict(list)
    for u, name in names.items():
        if name != u:
            by_name[" ".join(name.casefold().split())].append(u)
    for us in by_name.values():
        if len(us) > 1 and all(not (cycles_of[a] & cycles_of[b]) for i, a in enumerate(us) for b in us[i + 1:]):
            for u in us[1:]:
                parent[find(u)] = find(us[0])
    pid = {u: find(u) for u in names}
    members = defaultdict(set)
    for u in names:
        members[pid[u]].add(u)

    # Replay: Cycle order, then Swiss before playoffs and round order; each round reads the Ratings at its start.
    rating = defaultdict(lambda: defaultdict(lambda: 1500.0))
    after_rc, start_rc, sides = defaultdict(dict), defaultdict(dict), []
    for rc in sorted(rcs, key=lambda rc: rc["cycle"]):
        cycle, views = rc["cycle"], ("Global", rc["format"])
        entrants = {pid[u] for u in names if cycle in cycles_of[u]}
        for view in views:
            for p in entrants:
                start_rc[view].setdefault(p, {})[cycle] = rating[view][p]
        here = [m for m in matches if m["cycle"] == cycle]
        for key in sorted({(m["playoff"], m["round"]) for m in here}):
            in_round = [m for m in here if (m["playoff"], m["round"]) == key]
            moves = {view: defaultdict(float) for view in views}
            for m in in_round:
                ps = [pid[u] for u in m["users"]]
                for i, p in enumerate(ps):
                    opp = ps[1 - i] if len(ps) == 2 else None
                    side = {"cycle": cycle, "playoff": m["playoff"], "round": m["round"], "pid": p, "opponent": opp,
                            "score": None if m["score"] is None else (m["score"] if i == 0 else 1 - m["score"]),
                            "rated": m["rated"], "before": {}, "opponent_before": {}, "after": {}}
                    for view in views:
                        side["before"][view] = rating[view][p]
                        if opp:
                            side["opponent_before"][view] = rating[view][opp]
                        if m["rated"]:
                            e = 1 / (1 + 10 ** ((rating[view][opp] - rating[view][p]) / S))
                            moves[view][p] += K * (side["score"] - e)
                    sides.append(side)
            for view in views:
                for p, d in moves[view].items():
                    rating[view][p] += d
            for side in sides[-2 * len(in_round):]:
                if side["cycle"] == cycle and (side["playoff"], side["round"]) == key and side["rated"]:
                    side["after"] = {view: rating[view][side["pid"]] for view in views}
        for view in views:
            for p in entrants:
                after_rc[view].setdefault(p, {})[cycle] = rating[view][p]
    return {"players": {frozenset(us): p for p, us in members.items()}, "after_rc": after_rc, "start_rc": start_rc, "sides": sides}
