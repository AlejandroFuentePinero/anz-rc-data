"""The Rating rule against mtgeloproject's own record of the same ANZ RC Matches (data/mtgeloproject, anzrc.mtgelo).

mtgeloproject publishes each person's rating before and after every Match and the opponent's rating before it, to
two decimals. Their ratings carry history from events outside the ANZ RCs, so the absolute numbers differ from ours;
the rule that moves them is what must be the same.
"""

import json
from pathlib import Path

import pytest

from anzrc import ratings, rcs
from anzrc.build import CURATION, replayed
from anzrc.melee import round_ids

ORACLE = Path("data/mtgeloproject")
SCORES = {"Won": 1, "Lost": 0, "Draw": 0.5}
# Their start, opponent start and end are each rounded to 0.01, so a faithful rule lands within 0.005 + 0.005 of
# their end, plus a hair from the opponent's rounding.
ROUNDING = 0.0105


def oracle_rows() -> list[dict]:
    codes = json.loads((ORACLE / "events.json").read_text())
    rows = []
    for path in sorted(ORACLE.glob("*.json")):
        if path.name == "events.json":
            continue
        for code, matches in json.loads(path.read_text()).items():
            if code in codes:
                rows += [match | {"person": path.stem, "code": code} for match in matches]
    return rows


ROWS = oracle_rows()


def test_the_oracle_holds_every_anz_rc():
    assert len(json.loads((ORACLE / "events.json").read_text())) == 13
    assert len({row["code"] for row in ROWS}) == 13


def test_every_played_match_moves_a_rating_by_k_times_score_minus_expectation_as_mtgeloproject_does():
    played = [row for row in ROWS if row["result"].split()[0] in SCORES]
    misses = []
    for row in played:
        start, opponent = row["own_elo"]["start"], row["opp_data"]["start"]
        ours = start + ratings.move(start, opponent, SCORES[row["result"].split()[0]])
        if abs(ours - row["own_elo"]["end"]) > ROUNDING:
            misses.append((row["code"], row["round"], row["table"], row["result"], start, opponent, row["own_elo"]["end"], ours))
    assert len(played) > 10000
    assert misses == []


def test_mtgeloprojects_intentional_draws_move_nothing():
    intentional = [row for row in ROWS if row["result"] == "ID"]
    assert intentional
    assert all(row["own_elo"]["start"] == row["own_elo"]["end"] for row in intentional)


@pytest.mark.parametrize("k, scale", [(35, ratings.SCALE), (37, ratings.SCALE), (ratings.K, 1100), (ratings.K, 1150)])
def test_a_k_or_a_scale_one_step_off_misses_mtgeloprojects_numbers(k, scale, monkeypatch):
    # Guards the conformance test itself: it must be able to tell a near-miss rule from the real one.
    monkeypatch.setattr(ratings, "SCALE", scale)
    row = max((r for r in ROWS if r["result"].startswith("Won")), key=lambda r: abs(r["own_elo"]["start"] - r["opp_data"]["start"]))
    start, opponent = row["own_elo"]["start"], row["opp_data"]["start"]
    assert abs(start + ratings.move(start, opponent, 1, k) - row["own_elo"]["end"]) > ROUNDING


# Which Matches count, with which result, and who is one Player, against mtgeloproject's record.
#
# Each mtgeloproject row is found among Melee's Matches by RC, round and table. The person behind a row is the side
# whose game wins equal the person's own in the row's game score, so names are never needed. Rebuilt playoff Matches
# have no Melee table and are found by their two Players.

# Where mtgeloproject's record and ours part, and why. Anything else that differs fails.
KNOWN_DIFFERENCES = {
    # Melee's result names the other Player the winner ("Lisa McGlaughlin won 2-1-0", "Ryan McCartney won 2-1-0").
    (1, "3", 65): "Melee names the other winner",
    (1, "5", 60): "Melee names the other winner",
}
# Two Melee accounts that mtgeloproject splits by a change of name, and a same-real-name join it does not make.
KNOWN_SPLITS = {"natebass", "miketaylor", "tylervisser"}
SCORES_OF = {"Won": 1, "Lost": 0, "Draw": 0.5, "ID": None}


@pytest.fixture(scope="module")
def ours():
    _, cards, history = replayed(rcs.RAW, rcs.RC_LIST, CURATION)
    slug = {username: card["slug"] for card in cards.values() for username in card["usernames"]}
    rated = {}  # (Cycle, round index, Player, opponent) -> the Player's score
    for rc in history:
        for index, matches in enumerate(rc["rounds"]):
            for a, b, score in matches:
                rated[(rc["cycle"], index, a, b)] = score
                rated[(rc["cycle"], index, b, a)] = 1 - score
    tables = {}  # (Cycle, round index, table) -> [(Player, game wins)]
    for rc in rcs.load():
        folder = rcs.RAW / str(rc["melee_id"])
        for index, round_id in enumerate(round_ids((folder / "event.html").read_text())):
            for match in json.loads((folder / f"matches-{round_id}.json").read_text())["data"]:
                players = [(slug[side["Team"]["Players"][0]["Username"]], side["GameWins"] or 0) for side in match["Competitors"]]
                tables[(rc["cycle"], index, match["TableNumber"])] = players
    rounds = {rc["cycle"]: len(rc["rounds"]) for rc in history}
    return rated, tables, rounds


def _index(rounds, cycle, label):
    """mtgeloproject numbers Swiss rounds and names the three playoff rounds Q, S and F."""
    return int(label) - 1 if label.isdigit() else rounds[cycle] - 3 + "QSF".index(label)


def _cycle_of():
    codes = json.loads((ORACLE / "events.json").read_text())
    by_melee_id = {rc["melee_id"]: rc["cycle"] for rc in rcs.load()}
    return {code: by_melee_id[melee_id] for code, melee_id in codes.items()}


def _own_side(row, cycle, tables, rounds) -> list[str]:
    """The Players of the row's Melee Match whose game wins are the person's own: one when a decided Match tells the
    sides apart, none when it cannot (a draw, an Intentional Draw, a rebuilt Match, a listed difference)."""
    result, *score = row["result"].split()
    sides = tables.get((cycle, _index(rounds, cycle, row["round"]), row["table"]))
    if result not in ("Won", "Lost") or not sides or len(sides) != 2 or (cycle, row["round"], row["table"]) in KNOWN_DIFFERENCES:
        return []
    own_games = int(score[0].split("-")[0])
    return [player for player, games in sides if games == own_games]


def test_each_mtgeloproject_person_is_one_player_here_and_each_player_one_person_there(ours):
    _, tables, rounds = ours
    cycle_of = _cycle_of()
    players_of: dict[str, set] = {}
    for row in ROWS:
        players_of.setdefault(row["person"], set()).update(_own_side(row, cycle_of[row["code"]], tables, rounds))
    players_of = {person: players for person, players in players_of.items() if players}
    joined_there = {person: players for person, players in players_of.items() if len(players) > 1}
    people_of: dict[str, set] = {}
    for person, players in players_of.items():
        for player in players:
            people_of.setdefault(player, set()).add(person)
    split_there = {player for player, people in people_of.items() if len(people) > 1}
    assert joined_there == {}
    assert split_there == KNOWN_SPLITS


def test_every_match_mtgeloproject_rates_we_rate_with_the_same_result_and_every_one_it_leaves_out_we_leave_out(ours):
    rated, tables, rounds = ours
    cycle_of = _cycle_of()
    person_of = {}  # mtgeloproject person -> Player, from the rows that tell sides apart
    for row in ROWS:
        mine = _own_side(row, cycle_of[row["code"]], tables, rounds)
        if len(mine) == 1:
            person_of.setdefault(row["person"], mine[0])
    differences, seen = {}, set()
    for row in ROWS:
        cycle = cycle_of[row["code"]]
        index = _index(rounds, cycle, row["round"])
        me, them = person_of[row["person"]], person_of[row["opp_data"]["id"]]
        seen.add((cycle, index, me, them))
        if rated.get((cycle, index, me, them)) != SCORES_OF[row["result"].split()[0]]:
            differences[(cycle, row["round"], row["table"])] = row["result"]
    assert set(differences) == set(KNOWN_DIFFERENCES)
    unrecorded = [key for key in rated if key not in seen]
    assert unrecorded == []
