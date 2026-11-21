"""The build, driven through its public interface: raw folder, RC list and curation file in, bundle out.

Fixtures are small RCs in Melee's response shapes, cut down from real responses. A Player is written as
(username, display name); Melee shows the username as the display name when a Player hides their real name.
"""

import json

import pytest

from anzrc.build import build
from anzrc import ratings
from anzrc.ratings import K

SWISS, PLAYOFFS = "Swiss", "Playoffs/Top Cut"


def melee_player(who):
    username, display_name = who
    return {"DisplayName": display_name, "Username": username}


def competitor(who, game_wins):
    return {"GameWins": game_wins, "Team": {"Players": [melee_player(who)]}, "Decklists": []}


def played(a, b, a_wins, b_wins, draws=0, table=1):
    """A Match with a result between two Players. Melee leaves a loser's game wins null at times."""
    return {
        "Competitors": [competitor(a, a_wins), competitor(b, b_wins)],
        "GameDraws": draws,
        "TableNumber": table,
        "HasResult": True,
        "ByeReason": None,
        "LossReason": None,
    }


def bye(who):
    return {"Competitors": [competitor(who, None)], "GameDraws": 0, "HasResult": True, "ByeReason": 0, "LossReason": None}


def late_entry_forfeit(who):
    return {"Competitors": [competitor(who, None)], "GameDraws": 0, "HasResult": True, "ByeReason": None, "LossReason": 2}


def not_reported(who):
    return {"Competitors": [competitor(who, 0)], "GameDraws": 0, "HasResult": True, "ByeReason": None, "LossReason": None}


def no_result(a, b):
    """Cycle 13's one Match Melee left unconfirmed: no result flag and no game wins, one drawn game."""
    return played(a, b, None, None, draws=1) | {"HasResult": False}


def standing(rank, who, deck="Izzet Prowess", decklist_id=None):
    """A final standings row cut down from Melee's shape."""
    decklist_id = decklist_id or f"deck-{who[0]}"
    return {
        "Team": {"Players": [melee_player(who)]},
        "Rank": rank,
        "Decklists": [{"DecklistId": decklist_id, "DecklistName": deck}],
    }


def write_rc(raw, melee_id, rounds, final, swiss=None):
    """One RC: rounds as (matching method, Matches), every round's standings holding the final rows.

    Given end-of-Swiss rows, the Swiss rounds' standings hold those instead, as Cycles 1 to 5 return them.
    """
    folder = raw / str(melee_id)
    folder.mkdir(parents=True)
    round_ids = [str(melee_id * 100 + n) for n in range(1, len(rounds) + 1)]
    buttons = "".join(f'<button class="btn btn-gray round-selector" data-id="{r}" data-name="x">\n' for r in round_ids)
    (folder / "event.html").write_text(f"<html>\n{buttons}{buttons}</html>")
    for round_id, (method, matches) in zip(round_ids, rounds):
        rows = [row | {"MatchingMethodDescription": method} for row in (swiss if swiss and method == SWISS else final)]
        (folder / f"matches-{round_id}.json").write_text(json.dumps({"recordsTotal": len(matches), "data": matches}))
        (folder / f"standings-{round_id}.json").write_text(json.dumps({"recordsTotal": len(rows), "data": rows}))


class Bundle:
    def __init__(self, folder):
        self.folder = folder

    def card(self, slug):
        return json.loads((self.folder / "players" / f"{slug}.json").read_text())

    def index(self):
        return json.loads((self.folder / "players.json").read_text())

    def rcs(self):
        return json.loads((self.folder / "rcs.json").read_text())

    def community(self):
        return json.loads((self.folder / "community.json").read_text())

    def leaderboard(self):
        return json.loads((self.folder / "leaderboard.json").read_text())


def run_build(tmp_path, rcs, curation=""):
    """Build from RCs given as (cycle, format, rounds, final standings[, end-of-Swiss standings]); Melee IDs are made up."""
    raw = tmp_path / "raw"
    lines = ["cycle,melee_id,format,city,start_date"]
    for cycle, format_, rounds, final, *swiss in rcs:
        melee_id = 1000 + cycle
        write_rc(raw, melee_id, rounds, final, *swiss)
        lines.append(f"{cycle},{melee_id},{format_},,2023-0{cycle}-01")
    rc_list = tmp_path / "rcs.csv"
    rc_list.write_text("\n".join(lines) + "\n")
    curation_file = tmp_path / "curation.toml"
    curation_file.write_text(curation)
    build(raw, rc_list, curation_file, tmp_path / "bundle")
    return Bundle(tmp_path / "bundle")


ANA = ("ana", "Ana Lopez")
BEN = ("ben", "Ben Hall")
CAL = ("cal", "cal")
DEE = ("dee", "Dee Kim")


def test_a_bare_card_shows_the_rc_history_and_the_match_history(tmp_path):
    bundle = run_build(
        tmp_path,
        [(1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 1), played(CAL, DEE, 2, 0)])], [
            standing(1, ANA, deck="Rakdos Midrange", decklist_id="d-ana"),
            standing(2, CAL),
            standing(3, BEN),
            standing(4, DEE),
        ])],
    )

    card = bundle.card("ana")
    assert card["name"] == "Ana Lopez"
    assert card["rcs"] == [
        {
            "cycle": 1,
            "date": "2023-01-01",
            "format": "Pioneer",
            "finish": "Winner",
            "top_8": True,
            "field_size": 4,
            "finish_share": 25.0,
            "record": "1-0-0",
            "win_rate": {"rate": 100.0, "matches": 1},
            "rating_start": {"Global": 1500.0, "Pioneer": 1500.0},
            "rating_end": {"Global": 1518.0, "Pioneer": 1518.0},
            "deck": "Rakdos Midrange",
            "decklist": "https://melee.gg/Decklist/View/d-ana",
        }
    ]
    assert card["matches"] == [
        {"cycle": 1, "round": "Round 1", "playoff": False, "opponent": {"slug": "ben", "name": "Ben Hall"}, "result": "Win",
         "games": "2-1-0", "reconstructed": False, "opponent_rating": {"Global": 1500.0, "Pioneer": 1500.0},
         "change": {"Global": 18.0, "Pioneer": 18.0}, "rating_after": {"Global": 1518.0, "Pioneer": 1518.0}}
    ]
    assert bundle.card("ben")["matches"][0]["result"] == "Loss"
    assert bundle.card("ben")["matches"][0]["games"] == "1-2-0"


def test_the_rc_table_gives_each_rc_its_field_size_and_winner_as_the_player_their_card_names(tmp_path):
    owner = ("alejandrofp", "alejandrofp")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(2, ANA), standing(1, BEN), standing(3, CAL)]),
            (2, "Modern", [(SWISS, [played(owner, ANA, 2, 0)])], [standing(1, owner), standing(2, ANA)]),
        ],
        curation='[display_names]\nalejandrofp = "Alejandro de la Fuente"\n',
    )

    assert [{key: rc[key] for key in ("cycle", "date", "city", "format", "field_size", "winner")} for rc in bundle.rcs()] == [
        {"cycle": 1, "date": "2023-01-01", "city": None, "format": "Pioneer", "field_size": 3,
         "winner": {"slug": "ben", "name": "Ben Hall"}},
        {"cycle": 2, "date": "2023-02-01", "city": None, "format": "Modern", "field_size": 2,
         "winner": {"slug": "alejandrofp", "name": "Alejandro de la Fuente"}},
    ]


def test_the_rc_table_gives_each_rc_its_winner_and_runner_up_by_rank_as_players(tmp_path):
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 5)}
    p[2] = ("Ana_L", "Ana Lopez")  # Ana's second account, one Player with "ana" by the real-name rule
    # Melee's rows out of rank order, so the table follows the Rank, not the row order.
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(p[1], p[2], 2, 0), played(p[3], p[4], 2, 0)])],
             [standing(3, p[1]), standing(2, p[2]), standing(1, p[3]), standing(4, p[4])]),
        ],
    )

    row = bundle.rcs()[1]
    del row["field_rating"]  # tested on its own
    assert row == {
        "cycle": 2, "date": "2023-02-01", "city": None, "format": "Modern", "field_size": 4,
        "winner": {"slug": "p3", "name": "Player 3"}, "runner_up": {"slug": "ana", "name": "Ana Lopez"},
    }


def test_each_rc_splits_its_field_by_experience_across_formats_and_joined_accounts(tmp_path):
    ben_new = ("Ben_H", "Ben Hall")  # Ben's second account from Cycle 4, one Player with "ben" by the real-name rule
    eve = ("eve", "Eve Moss")  # disqualified in Cycle 8: off the standings, still at the RC
    formats = ["Pioneer", "Modern", "Standard", "Pioneer", "Modern", "Standard", "Pioneer", "Modern"]
    rcs = [(c, formats[c - 1], [(SWISS, [played(ANA, BEN if c <= 3 else ben_new, 2, 0)])], [standing(1, ANA), standing(2, BEN if c <= 3 else ben_new)])
           for c in range(1, 8)]
    rcs.append((8, "Modern", [(SWISS, [played(ANA, ben_new, 2, 0), played(CAL, eve, 2, 0)])],
                [standing(1, ANA), standing(2, ben_new), standing(3, CAL)]))

    bundle = run_build(tmp_path, rcs)

    community = bundle.community()
    assert community["levels"] == ["1st", "2nd-3rd", "4th-7th", "8th+"]
    assert [(rc["cycle"], rc["players"]) for rc in community["field_by_experience"]] == [
        (1, [2, 0, 0, 0]),
        (2, [0, 2, 0, 0]),
        (3, [0, 2, 0, 0]),
        (4, [0, 0, 2, 0]),
        (5, [0, 0, 2, 0]),
        (6, [0, 0, 2, 0]),
        (7, [0, 0, 2, 0]),
        (8, [2, 0, 0, 2]),  # cal and eve at their first; ana and ben at their eighth
    ]
    assert community["field_by_experience"][-1]["shares"] == [50.0, 0.0, 0.0, 50.0]


def test_the_top_8_rate_by_experience_leaves_out_the_first_rc_where_everyone_was_at_their_first(tmp_path):
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 10)}
    n1, n2 = ("n1", "New One"), ("n2", "New Two")
    cycle_1 = [standing(n, p[n]) for n in range(1, 10)]  # p9 misses the Top 8
    # Cycle 2: p1 to p8 back at their second RC, n1 and n2 at their first; n1 takes the Title, p1 drops to 9th.
    cycle_2 = [standing(1, n1)] + [standing(n, p[n]) for n in range(2, 9)] + [standing(9, p[1]), standing(10, n2)]
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(p[n], p[n + 1], 2, 0) for n in (1, 3, 5, 7)])], cycle_1),
            (2, "Modern", [(SWISS, [played(n1, p[1], 2, 0), played(p[2], n2, 2, 0)])], cycle_2),
        ],
    )

    community = bundle.community()
    # Each level's rate, and how many times the rate at a first RC it is.
    assert community["top_8_rate_by_experience"] == [
        {"level": "1st", "rcs": "1", "top_8s": 1, "entries": 2, "rate": 50.0, "vs_first": 1.0},  # n1 of n1, n2
        {"level": "2nd-3rd", "rcs": "2-3", "top_8s": 7, "entries": 8, "rate": 87.5, "vs_first": 1.8},  # p2 to p8 of p1 to p8; 87.5 / 50 = 1.75
        {"level": "4th-7th", "rcs": "4-7", "top_8s": 0, "entries": 0, "rate": None, "vs_first": None},
        {"level": "8th+", "rcs": "8+", "top_8s": 0, "entries": 0, "rate": None, "vs_first": None},
    ]


def test_every_match_class_shows_its_result_and_only_played_matches_and_intentional_draws_count_in_the_record(tmp_path):
    rounds = [
        (SWISS, [played(ANA, BEN, 1, 0), played(CAL, DEE, None, 2)]),  # 1-0-0, and a null loser read as 0
        (SWISS, [played(ANA, CAL, 1, 0, draws=1), played(BEN, DEE, 0, 3)]),  # 1-0-1 and 3-0-0
        (SWISS, [played(ANA, DEE, 1, 1), played(BEN, CAL, 1, 1, draws=1)]),  # played draws 1-1-0 and 1-1-1
        (SWISS, [bye(ANA), late_entry_forfeit(BEN), not_reported(CAL)]),
        (SWISS, [played(ANA, BEN, 0, 0, draws=3), played(CAL, DEE, 0, 0, draws=3, table=2)]),  # Intentional Draws
        (SWISS, [no_result(ANA, DEE)]),
    ]
    final = [standing(1, DEE), standing(2, ANA), standing(3, CAL), standing(4, BEN)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    ana = bundle.card("ana")
    assert [(m["round"], m["opponent"] and m["opponent"]["slug"], m["result"], m["games"]) for m in ana["matches"]] == [
        ("Round 1", "ben", "Win", "1-0-0"),
        ("Round 2", "cal", "Win", "1-0-1"),
        ("Round 3", "dee", "Draw", "1-1-0"),
        ("Round 4", None, "Bye", None),
        ("Round 5", "ben", "Intentional Draw", "0-0-3"),
        ("Round 6", "dee", "Draw", "0-0-1"),
    ]
    assert ana["rcs"][0]["record"] == "2-0-3"
    assert [(m["result"], m["games"]) for m in bundle.card("ben")["matches"]] == [
        ("Loss", "0-1-0"),
        ("Loss", "0-3-0"),
        ("Draw", "1-1-1"),
        ("Forfeit", None),
        ("Intentional Draw", "0-0-3"),
    ]
    assert bundle.card("ben")["rcs"][0]["record"] == "0-2-2"
    assert [m["result"] for m in bundle.card("cal")["matches"]][-2:] == ["Not reported", "Intentional Draw"]
    assert bundle.card("dee")["rcs"][0]["record"] == "2-0-3"


def test_playoff_rounds_are_told_apart_by_the_standings_matching_method_not_by_round_number(tmp_path):
    # Melee numbers these playoff rounds on from the Swiss ("Round 3" to "Round 5"), as in Cycles 2, 5 and 6.
    rounds = [
        (SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 2, 0)]),
        (SWISS, [played(ANA, CAL, 2, 0), played(BEN, DEE, 2, 0)]),
        (PLAYOFFS, [played(ANA, DEE, 2, 0), played(CAL, BEN, 2, 0)]),
        (PLAYOFFS, [played(ANA, CAL, 2, 0)]),
        (PLAYOFFS, [played(ANA, BEN, 2, 0)]),
    ]
    final = [standing(1, ANA), standing(2, BEN), standing(3, CAL), standing(4, DEE)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    assert [m["round"] for m in bundle.card("ana")["matches"]] == ["Round 1", "Round 2", "Quarterfinal", "Semifinal", "Final"]
    assert [m["playoff"] for m in bundle.card("ana")["matches"]] == [False, False, True, True, True]


def test_a_final_melee_lost_is_rebuilt_as_rank_1_beating_rank_2_with_no_game_score(tmp_path):
    # As in Cycles 7, 8 and 10: the quarterfinals and semifinals are held, the final round is empty.
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 9)}
    rounds = [
        (SWISS, [played(p[1], p[2], 2, 0), played(p[3], p[4], 2, 0), played(p[5], p[6], 2, 0), played(p[7], p[8], 2, 0)]),
        (PLAYOFFS, [played(p[1], p[8], 2, 0), played(p[4], p[5], 2, 1), played(p[2], p[7], 2, 0), played(p[3], p[6], 2, 0)]),
        (PLAYOFFS, [played(p[1], p[4], 0, 2), played(p[2], p[3], 1, 2)]),
        (PLAYOFFS, []),
    ]
    final = [standing(rank, p[n]) for rank, n in enumerate([4, 3, 1, 2, 5, 6, 7, 8], start=1)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    winner, runner_up = bundle.card("p4"), bundle.card("p3")
    for card in (winner, runner_up):  # the Ratings around the Match are tested on their own
        del card["matches"][-1]["opponent_rating"]
        del card["matches"][-1]["change"]
        del card["matches"][-1]["rating_after"]
    assert winner["matches"][-1] == {
        "cycle": 1, "round": "Final", "playoff": True, "opponent": {"slug": "p3", "name": "Player 3"}, "result": "Win", "games": None, "reconstructed": True
    }
    assert runner_up["matches"][-1] == {
        "cycle": 1, "round": "Final", "playoff": True, "opponent": {"slug": "p4", "name": "Player 4"}, "result": "Loss", "games": None, "reconstructed": True
    }
    assert [m["reconstructed"] for m in winner["matches"][:-1]] == [False, False, False]
    # Swiss loss, then the quarterfinal, the semifinal and the rebuilt final won.
    assert winner["rcs"][0]["record"] == "3-1-0"
    assert runner_up["rcs"][0]["record"] == "3-1-0"
    assert (winner["rcs"][0]["finish"], runner_up["rcs"][0]["finish"]) == ("Winner", "Runner-up")


def test_a_bracket_melee_holds_no_matches_for_is_rebuilt_from_end_of_swiss_seeding_and_the_final_standings(tmp_path):
    # As in Cycles 3 and 4: three playoff rounds, none with a Match. Seeds 1 to 8 are p1 to p8 at the end of the Swiss.
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 11)}
    rounds = [
        (SWISS, [played(p[n], p[n + 1], 2, 0) for n in range(1, 11, 2)]),
        (PLAYOFFS, []),
        (PLAYOFFS, []),
        (PLAYOFFS, []),
    ]
    swiss = [standing(n, p[n]) for n in range(1, 11)]
    # Quarterfinals 8 beat 1, 4 beat 5, 2 beat 7, 6 beat 3; semifinals 4 beat 8, 6 beat 2; final 6 beat 4.
    final = [standing(rank, p[n]) for rank, n in enumerate([6, 4, 8, 2, 1, 5, 7, 3, 9, 10], start=1)]

    bundle = run_build(tmp_path, [(1, "Pioneer", rounds, final, swiss)])

    def playoffs(slug):
        return [(m["round"], m["opponent"]["slug"], m["result"], m["games"], m["reconstructed"])
                for m in bundle.card(slug)["matches"] if m["round"] != "Round 1"]

    assert playoffs("p6") == [
        ("Quarterfinal", "p3", "Win", None, True), ("Semifinal", "p2", "Win", None, True), ("Final", "p4", "Win", None, True)
    ]
    assert playoffs("p4") == [
        ("Quarterfinal", "p5", "Win", None, True), ("Semifinal", "p8", "Win", None, True), ("Final", "p6", "Loss", None, True)
    ]
    assert playoffs("p8") == [("Quarterfinal", "p1", "Win", None, True), ("Semifinal", "p4", "Loss", None, True)]
    assert playoffs("p2") == [("Quarterfinal", "p7", "Win", None, True), ("Semifinal", "p6", "Loss", None, True)]
    assert playoffs("p1") == [("Quarterfinal", "p8", "Loss", None, True)]
    assert playoffs("p9") == []
    assert bundle.card("p6")["rcs"][0]["record"] == "3-1-0"


def test_finishes_show_winner_runner_up_and_top_4_and_top_8_tiers_never_melees_order_inside_a_tier(tmp_path):
    field = [(f"p{n}", f"Player {n}") for n in range(1, 11)]
    rounds = [(SWISS, [played(field[n], field[n + 1], 2, 0) for n in range(0, 10, 2)])]
    final = [standing(n, who) for n, who in enumerate(field, start=1)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    finishes = [(bundle.card(f"p{n}")["rcs"][0]["finish"], bundle.card(f"p{n}")["rcs"][0]["field_size"]) for n in range(1, 11)]
    assert finishes == [
        ("Winner", 10),
        ("Runner-up", 10),
        ("Top 4", 10),
        ("Top 4", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("9th", 10),
        ("10th", 10),
    ]
    assert [bundle.card(f"p{n}")["rcs"][0]["top_8"] for n in range(1, 11)] == [True] * 8 + [False] * 2


def test_a_player_missing_from_the_standings_keeps_their_matches_and_gets_no_finish(tmp_path):
    # Cycle 8's disqualified Player: Matches played, then gone from the standings. Their deck is on their Matches.
    dee_lost = played(CAL, DEE, 2, 1)
    dee_lost["Competitors"][1]["Decklists"] = [{"DecklistId": "d-dee", "DecklistName": "Boros Energy"}]
    rounds = [(SWISS, [played(ANA, BEN, 2, 0), dee_lost]), (SWISS, [played(ANA, CAL, 2, 0), bye(BEN)])]
    final = [standing(1, ANA), standing(2, CAL), standing(3, BEN)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    dee = bundle.card("dee")
    assert [(m["opponent"]["slug"], m["result"]) for m in dee["matches"]] == [("cal", "Loss")]
    assert dee["rcs"] == [
        {"cycle": 1, "date": "2023-01-01", "format": "Modern", "finish": None, "top_8": False, "field_size": 3, "finish_share": None, "record": "0-1-0",
         "win_rate": {"rate": 0.0, "matches": 1}, "rating_start": {"Global": 1500.0, "Modern": 1500.0},
         "rating_end": {"Global": 1482.0, "Modern": 1482.0}, "deck": "Boros Energy", "decklist": "https://melee.gg/Decklist/View/d-dee"}
    ]


def test_finishes_past_the_top_8_read_as_english_ordinals(tmp_path):
    field = [(f"p{n}", f"Player {n}") for n in range(1, 25)]
    rounds = [(SWISS, [played(field[n], field[n + 1], 2, 0) for n in range(0, 24, 2)])]
    final = [standing(n, who) for n, who in enumerate(field, start=1)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    assert [bundle.card(f"p{n}")["rcs"][0]["finish"] for n in (11, 12, 13, 21, 22, 23, 24)] == [
        "11th", "12th", "13th", "21st", "22nd", "23rd", "24th"
    ]


def test_accounts_with_the_same_real_name_that_never_shared_an_rc_are_one_player(tmp_path):
    ana_old, ana_new = ("ana", "Ana Lopez"), ("Ana_L", "ana  LOPEZ")  # as Swiftclaw / Swiftclaw_
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ana_old, BEN, 2, 0)])], [standing(1, ana_old), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(BEN, ana_new, 2, 1)])], [standing(1, BEN), standing(2, ana_new)]),
        ],
    )

    ana = bundle.card("ana")
    assert ana["usernames"] == ["ana", "Ana_L"]
    assert [(rc["cycle"], rc["finish"]) for rc in ana["rcs"]] == [(1, "Winner"), (2, "Runner-up")]
    assert [(m["cycle"], m["result"]) for m in ana["matches"]] == [(1, "Win"), (2, "Loss")]
    assert [m["opponent"]["slug"] for m in bundle.card("ben")["matches"]] == ["ana", "ana"]
    assert sorted(player["slug"] for player in bundle.index()) == ["ana", "ben"]


def test_namesakes_who_shared_an_rc_stay_two_players(tmp_path):
    sam_a, sam_b = ("samA", "Sam Lee"), ("samB", "Sam Lee")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(sam_a, sam_b, 2, 0)])], [standing(1, sam_a), standing(2, sam_b)]),
            (2, "Pioneer", [(SWISS, [played(sam_a, BEN, 2, 0)])], [standing(1, sam_a), standing(2, BEN)]),
        ],
    )

    assert sorted(player["slug"] for player in bundle.index()) == ["ben", "sama", "samb"]
    assert len(bundle.card("sama")["rcs"]) == 2
    assert len(bundle.card("samb")["rcs"]) == 1


def test_a_curation_join_makes_two_accounts_one_player(tmp_path):
    cal_new = ("calvinm", "Calvin Moss")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(CAL, BEN, 2, 0)])], [standing(1, CAL), standing(2, BEN)]),
            (2, "Pioneer", [(SWISS, [played(cal_new, BEN, 2, 0)])], [standing(1, cal_new), standing(2, BEN)]),
        ],
        curation='joins = [["cal", "calvinm"]]\n',
    )

    assert bundle.card("cal")["usernames"] == ["cal", "calvinm"]
    assert [rc["cycle"] for rc in bundle.card("cal")["rcs"]] == [1, 2]
    assert sorted(player["slug"] for player in bundle.index()) == ["ben", "cal"]


def test_a_curation_join_that_puts_one_player_twice_in_an_rc_fails_the_build(tmp_path):
    with pytest.raises(ValueError, match=r"Joining ana, ben would put one Player twice in Cycle 1"):
        run_build(
            tmp_path,
            [(1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)])],
            curation='joins = [["ana", "ben"]]\n',
        )


def test_display_names_follow_the_override_then_the_real_name_then_the_username(tmp_path):
    owner = ("alejandrofp", "alejandrofp")  # hides their real name on Melee
    bundle = run_build(
        tmp_path,
        [(1, "Modern", [(SWISS, [played(owner, ANA, 2, 0), played(CAL, BEN, 2, 0)])], [
            standing(1, owner), standing(2, ANA), standing(3, CAL), standing(4, BEN),
        ])],
        curation='[display_names]\nalejandrofp = "Alejandro de la Fuente"\n',
    )

    assert sorted((p["slug"], p["name"], p["usernames"]) for p in bundle.index()) == [
        ("alejandrofp", "Alejandro de la Fuente", ["alejandrofp"]),
        ("ana", "Ana Lopez", ["ana"]),
        ("ben", "Ben Hall", ["ben"]),
        ("cal", "cal", ["cal"]),
    ]
    assert bundle.card("ana")["matches"][0]["opponent"] == {"slug": "alejandrofp", "name": "Alejandro de la Fuente"}


def test_a_joined_player_shows_a_real_name_from_any_account_over_a_newer_accounts_username(tmp_path):
    # Nathan shows his real name on his first account and only a username on his newer one (the owner's ruling).
    first, newer = ("nathan1", "Nathan Whalen"), ("natw", "natw")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(first, ANA, 2, 0)])], [standing(1, first), standing(2, ANA)]),
            (2, "Pioneer", [(SWISS, [played(newer, ANA, 2, 0)])], [standing(1, newer), standing(2, ANA)]),
        ],
        curation='joins = [["nathan1", "natw"]]\n',
    )

    assert [(p["slug"], p["name"]) for p in bundle.index() if p["slug"] == "nathan1"] == [("nathan1", "Nathan Whalen")]


# Ratings (ADR 0001). Expected values are worked by hand from mtgeloproject's rule: E = 1 / (1 + 10^(-gap / D)),
# D set so a 200 point gap is a 60% expectation, and a Match moves each Rating by K * (score - E).


def rating(bundle, slug, view="Global"):
    return bundle.card(slug)["ratings"][view]["rating"]


def test_a_single_match_between_two_new_players_moves_each_rating_by_half_of_k(tmp_path):
    bundle = run_build(tmp_path, [(1, "Modern", [(SWISS, [played(ANA, BEN, 2, 1)])], [standing(1, ANA), standing(2, BEN)])])

    assert rating(bundle, "ana") == pytest.approx(1500 + K / 2)
    assert rating(bundle, "ben") == pytest.approx(1500 - K / 2)


def test_a_played_draw_between_equals_and_every_match_not_played_move_nothing(tmp_path):
    # After round 1 Ana and Ben stand at 1518 and 1482, so any of the later Matches would move them if it counted.
    rounds = [
        (SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 1, 1, draws=1)]),  # Cal and Dee: a played draw between two 1500s
        (SWISS, [played(ANA, BEN, 0, 0, draws=3), bye(CAL), late_entry_forfeit(DEE)]),  # an Intentional Draw, a bye, a forfeit
        (SWISS, [not_reported(ANA)]),
    ]
    final = [standing(1, ANA), standing(2, BEN), standing(3, CAL), standing(4, DEE)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    assert [rating(bundle, slug) for slug in ("ana", "ben", "cal", "dee")] == [1500 + K / 2, 1500 - K / 2, 1500, 1500]


def test_a_played_draw_moves_the_higher_rated_player_down(tmp_path):
    # Ana beats Ben (1518 v 1482), then draws Ben: Ana expected 1 / (1 + 10^(-36 / 1135.77)) = 0.518238, so she gives
    # 36 * 0.018238 = 0.6566 back. Worked with K = 36.
    rounds = [(SWISS, [played(ANA, BEN, 2, 0)]), (SWISS, [played(ANA, BEN, 1, 1)])]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, [standing(1, ANA), standing(2, BEN)])])

    assert rating(bundle, "ana") == 1517  # 1517.34, shown whole
    assert rating(bundle, "ben") == 1483  # 1482.66


def test_the_order_of_matches_inside_a_round_and_of_players_inside_a_match_changes_no_rating(tmp_path):
    first = [played(ANA, BEN, 2, 0), played(CAL, DEE, 2, 1)]
    second = [played(ANA, DEE, 2, 1), played(BEN, CAL, 1, 1)]  # 1518 v 1482 both times, so every Rating ends apart
    final = [standing(1, ANA), standing(2, CAL), standing(3, BEN), standing(4, DEE)]
    as_listed = run_build(tmp_path / "a", [(1, "Modern", [(SWISS, first), (SWISS, second)], final)])
    reordered = run_build(
        tmp_path / "b",
        [(1, "Modern", [(SWISS, first[::-1]), (SWISS, [played(CAL, BEN, 1, 1), played(DEE, ANA, 1, 2)])], final)],
    )

    slugs = ("ana", "ben", "cal", "dee")
    assert [rating(as_listed, s) for s in slugs] == [rating(reordered, s) for s in slugs]
    assert len({rating(as_listed, s) for s in slugs}) == 4


def test_a_format_rating_moves_only_on_its_own_format_and_starts_at_1500(tmp_path):
    # Ana beats Ben at a Pioneer RC, then Ben beats Ana at a Modern RC. Globally Ana is the favourite in the second
    # Match (1518 v 1482, 0.518238), so Ben takes 36 * 0.518238 = 18.66 from her. Worked with K = 36.
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(BEN, ANA, 2, 1)])], [standing(1, BEN), standing(2, ANA)]),
        ],
    )

    assert rating(bundle, "ana", "Pioneer") == pytest.approx(1500 + K / 2)
    assert rating(bundle, "ana", "Modern") == pytest.approx(1500 - K / 2)
    assert rating(bundle, "ana") == 1499  # 1499.34, shown whole
    assert rating(bundle, "ben") == 1501  # 1500.66
    assert set(bundle.card("ana")["ratings"]) == {"Global", "Pioneer", "Modern"}
    assert bundle.card("ana")["ratings"]["Modern"]["rated_by"] == "Modern"


def test_a_format_whose_rating_does_not_ship_shows_the_global_rating(tmp_path, monkeypatch):
    monkeypatch.setattr(ratings, "FORMAT_RATINGS", {"Pioneer"})
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(BEN, ANA, 2, 1)])], [standing(1, BEN), standing(2, ANA)]),
        ],
    )

    ana = bundle.card("ana")["ratings"]
    assert ana["Modern"] == ana["Global"] | {"rated_by": "Global"}
    assert ana["Pioneer"]["rating"] == pytest.approx(1500 + K / 2)


def test_peak_rating_is_the_highest_after_any_rc_not_the_1500_start(tmp_path):
    # Ana: beats Ben (1518), sits out with a bye, then loses to Cal (still 1500 after a drawn Cycle 2). From 1518 v 1500
    # she was expected 1 / (1 + 10^(-18 / 1135.77)) = 0.509122, so she gives up 36 * 0.509122 = 18.33.
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Pioneer", [(SWISS, [bye(ANA), played(CAL, DEE, 1, 1)])], [standing(1, ANA), standing(2, CAL), standing(3, DEE)]),
            (3, "Modern", [(SWISS, [played(CAL, ANA, 2, 0)])], [standing(1, CAL), standing(2, ANA)]),
        ],
    )

    ana = bundle.card("ana")["ratings"]["Global"]
    assert ana["after_rc"] == [{"cycle": 1, "rating": 1518}, {"cycle": 2, "rating": 1518}, {"cycle": 3, "rating": 1500}]  # 1499.67
    assert ana["peak"] == 1518
    assert ana["rating"] == 1500
    assert bundle.card("ben")["ratings"]["Global"]["peak"] == 1482.0
    assert bundle.card("ana")["ratings"]["Modern"]["after_rc"] == [{"cycle": 3, "rating": 1482.0}]
    assert bundle.card("ana")["ratings"]["Pioneer"]["peak"] == 1518.0


def test_playoff_matches_count_and_a_rebuilt_final_moves_ratings_as_the_real_final_would(tmp_path):
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 9)}
    swiss = (SWISS, [played(p[1], p[2], 2, 0), played(p[3], p[4], 2, 0), played(p[5], p[6], 2, 0), played(p[7], p[8], 2, 0)])
    quarters = (PLAYOFFS, [played(p[1], p[8], 2, 0), played(p[4], p[5], 2, 1), played(p[2], p[7], 2, 0), played(p[3], p[6], 2, 0)])
    semis = (PLAYOFFS, [played(p[1], p[4], 0, 2), played(p[2], p[3], 1, 2)])
    final = [standing(rank, p[n]) for rank, n in enumerate([4, 3, 1, 2, 5, 6, 7, 8], start=1)]
    rebuilt = run_build(tmp_path / "rebuilt", [(1, "Modern", [swiss, quarters, semis, (PLAYOFFS, [])], final)])
    real = run_build(tmp_path / "real", [(1, "Modern", [swiss, quarters, semis, (PLAYOFFS, [played(p[4], p[3], 2, 1)])], final)])
    swiss_only = run_build(tmp_path / "swiss", [(1, "Modern", [swiss], final)])

    slugs = [f"p{n}" for n in range(1, 9)]
    assert [rating(rebuilt, s) for s in slugs] == [rating(real, s) for s in slugs]
    assert rating(rebuilt, "p4") != rating(swiss_only, "p4")


def test_the_match_history_shows_the_opponents_rating_at_the_start_of_the_round(tmp_path):
    # Ana and Cal both win round 1 (1518 each), then meet: each card shows the other at 1518, not at the Rating after.
    # Cycle 2 is Pioneer, so the Pioneer column is each Player's Pioneer Rating, new at 1500.
    bundle = run_build(
        tmp_path,
        [
            (1, "Modern", [(SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 2, 0)]), (SWISS, [played(ANA, CAL, 2, 0), bye(BEN)])],
             [standing(1, ANA), standing(2, CAL), standing(3, BEN), standing(4, DEE)]),
            (2, "Pioneer", [(SWISS, [played(CAL, ANA, 2, 0)])], [standing(1, CAL), standing(2, ANA)]),
        ],
    )

    assert [m["opponent_rating"] for m in bundle.card("ana")["matches"]] == [
        {"Global": 1500.0, "Modern": 1500.0},
        {"Global": 1518.0, "Modern": 1518.0},
        {"Global": 1500.0, "Pioneer": 1500.0},
    ]
    assert [m["opponent_rating"] for m in bundle.card("ben")["matches"]] == [{"Global": 1500.0, "Modern": 1500.0}, None]


def test_a_match_melee_left_unconfirmed_counts_by_its_game_score(tmp_path):
    # Cycle 13's one unconfirmed Match is 0-0-1: a drawn game, so a played draw, as Melee's own standings count it.
    rounds = [(SWISS, [played(ANA, BEN, 2, 0)]), (SWISS, [no_result(ANA, BEN)])]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, [standing(1, ANA), standing(2, BEN)])])

    ana = bundle.card("ana")
    assert [(m["result"], m["games"]) for m in ana["matches"]] == [("Win", "2-0-0"), ("Draw", "0-0-1")]
    assert ana["rcs"][0]["record"] == "1-0-1"
    assert rating(bundle, "ana") == 1517  # the draw from 1518 v 1482, as worked above: 1517.34


# Which 0-0-3 is an Intentional Draw (ADR 0001, following mtgeloproject): one in the last two Swiss rounds at tables 1 to
# 8, where Players still in the hunt for the Top 8 agree to draw, or one the curation file names. Any other is a played
# draw. Expected moves are the 1518 v 1482 draw worked above: 36 x (0.5 - 0.5182) = -0.66 for the higher-rated Player.


def four_rounds_of_0_0_3s():
    """Ana and Cal each beat their opponent, then draw them 0-0-3: early, late at table 9, and late at table 8."""
    return [
        (SWISS, [played(ANA, BEN, 2, 0, table=1), played(CAL, DEE, 2, 0, table=2)]),
        (SWISS, [played(ANA, BEN, 0, 0, draws=3, table=1)]),  # round 2 of 4: early
        (SWISS, [played(CAL, DEE, 0, 0, draws=3, table=9)]),  # round 3 of 4: late, but not a top table
        (SWISS, [played(ANA, BEN, 0, 0, draws=3, table=8)]),  # round 4 of 4: late, at a top table
    ]


FOUR = [standing(1, ANA), standing(2, CAL), standing(3, BEN), standing(4, DEE)]


def test_a_0_0_3_is_an_intentional_draw_only_in_the_last_two_swiss_rounds_at_tables_1_to_8(tmp_path):
    bundle = run_build(tmp_path, [(1, "Modern", four_rounds_of_0_0_3s(), FOUR)])

    assert [m["result"] for m in bundle.card("ana")["matches"]] == ["Win", "Draw", "Intentional Draw"]
    assert [m["result"] for m in bundle.card("cal")["matches"]] == ["Win", "Draw"]
    assert rating(bundle, "ana") == 1517  # 1517.34: the early draw moves, the late top-table one not
    assert rating(bundle, "cal") == 1517  # 1517.34: the late table-9 draw moves
    assert bundle.card("ana")["rcs"][0]["record"] == "1-0-2"


def test_a_0_0_3_the_curation_names_is_an_intentional_draw_wherever_it_falls(tmp_path):
    curation = 'intentional_draws = [{cycle = 1, round = 3, table = 9}]\n'

    bundle = run_build(tmp_path, [(1, "Modern", four_rounds_of_0_0_3s(), FOUR)], curation=curation)

    assert [m["result"] for m in bundle.card("cal")["matches"]] == ["Win", "Intentional Draw"]
    assert rating(bundle, "cal") == 1500 + K / 2


def test_a_curated_intentional_draw_that_names_no_0_0_3_fails_the_build(tmp_path):
    curation = 'intentional_draws = [{cycle = 1, round = 1, table = 1}]\n'  # a 2-0 win, not a 0-0-3

    with pytest.raises(ValueError, match="Cycle 1 Round 1 table 1"):
        run_build(tmp_path, [(1, "Modern", four_rounds_of_0_0_3s(), FOUR)], curation=curation)


def test_a_match_with_no_games_recorded_fails_the_build_and_asks_for_a_ruling(tmp_path):
    rounds = [(SWISS, [played(ANA, BEN, None, None, table=4) | {"HasResult": False}])]

    with pytest.raises(ValueError, match="Cycle 1 Round 1 table 4.*ruling"):
        run_build(tmp_path, [(1, "Modern", rounds, [standing(1, ANA), standing(2, BEN)])])


# The Player card's summary (issue #8): one entry per view the Player played in, none for a Format never played.


def field(cycle, size, placed):
    """Final standings of `size` Players: the placed ones at their ranks, made-up Players everywhere else."""
    return [standing(rank, placed.get(rank, (f"c{cycle}x{rank}", f"Filler {cycle} {rank}"))) for rank in range(1, size + 1)]


def three_rcs_for_ana():
    """Ana's Title in a Pioneer 10, Top 4 in a Modern 8 and 12th in a Pioneer 20, across every Match class."""
    return [
        (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)]), (SWISS, [played(ANA, CAL, 1, 1)])], field(1, 10, {1: ANA, 2: BEN, 3: CAL})),
        (2, "Modern", [(SWISS, [played(BEN, ANA, 2, 0)]), (SWISS, [bye(ANA)]), (SWISS, [played(ANA, DEE, 0, 0, draws=3, table=1)])],
         field(2, 8, {4: ANA, 1: BEN, 2: DEE})),
        (3, "Pioneer", [(SWISS, [played(ANA, CAL, 2, 1)])], field(3, 20, {12: ANA, 1: CAL})),
    ]


def test_the_summary_gives_each_view_its_record_win_rate_and_finishes(tmp_path):
    bundle = run_build(tmp_path, three_rcs_for_ana())

    summary = bundle.card("ana")["summary"]
    figures = ("record", "win_rate", "rcs", "top_8s", "finals", "best_finish", "typical_finish_above")
    # Global: wins over Ben and Cal, the loss to Ben, a played draw and an Intentional Draw; the bye is in no record.
    # Typical Finish: the median of 1/10, 3.5/8 (the Top 4 tier) and 12/20 is 43.8%, so above 56.2% of the field.
    assert {key: summary["Global"][key] for key in figures} == {
        "record": "2-1-2", "win_rate": {"rate": 66.7, "matches": 3}, "rcs": 3, "top_8s": 2, "finals": 1,
        "best_finish": "Winner", "typical_finish_above": 56.2,
    }
    assert {key: summary["Pioneer"][key] for key in figures} == {
        "record": "2-0-1", "win_rate": {"rate": 100.0, "matches": 2}, "rcs": 2, "top_8s": 1, "finals": 1,
        "best_finish": "Winner", "typical_finish_above": 65.0,  # median of 10% and 60%
    }
    assert {key: summary["Modern"][key] for key in figures} == {
        "record": "0-1-1", "win_rate": {"rate": 0.0, "matches": 1}, "rcs": 1, "top_8s": 1, "finals": 0,
        "best_finish": "Top 4", "typical_finish_above": 56.2,
    }
    assert "Standard" not in summary
    assert bundle.card("ben")["summary"]["Global"]["finals"] == 2  # Runner-up in Cycle 1, Winner in Cycle 2


def test_best_finish_is_the_lowest_place_with_any_top_8_first(tmp_path):
    # Ben: 9th of 10, 12th of 20 (a better share of the field, but a worse place), then 8th of 8, a Top 8.
    # Cal: the first two only. Dee: disqualified, so no Finish at all.
    rcs = [
        (1, "Pioneer", [(SWISS, [played(BEN, CAL, 2, 0)])], field(1, 10, {9: BEN, 10: CAL})),
        (2, "Pioneer", [(SWISS, [played(BEN, CAL, 2, 0), played(ANA, DEE, 2, 0)])], field(2, 20, {12: BEN, 13: CAL, 1: ANA})),
        (3, "Modern", [(SWISS, [played(BEN, ANA, 2, 0)])], field(3, 8, {8: BEN, 1: ANA})),
    ]

    bundle = run_build(tmp_path, rcs)

    assert bundle.card("ben")["summary"]["Global"]["best_finish"] == "Top 8"
    assert bundle.card("ben")["summary"]["Pioneer"]["best_finish"] == "9th"
    assert bundle.card("cal")["summary"]["Global"]["best_finish"] == "10th"  # 10th of 10 beats 13th of 20
    dee = bundle.card("dee")["summary"]["Global"]
    assert (dee["best_finish"], dee["typical_finish_above"], dee["rcs"]) == (None, None, 1)


def test_typical_finish_takes_the_median_of_exact_shares_and_rounds_once(tmp_path):
    # Ben: 9th of 9 (100%) and 9th of 14 (64.2857%). The median is 82.1429%, so above 17.857% of the field: 17.9. Rounding
    # each share first (100 and 64.3) would give a median of 82.15 and 17.8.
    rcs = [
        (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], field(1, 9, {1: ANA, 9: BEN})),
        (2, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], field(2, 14, {1: ANA, 9: BEN})),
    ]

    bundle = run_build(tmp_path, rcs)

    assert bundle.card("ben")["summary"]["Global"]["typical_finish_above"] == 17.9


def three_pioneer_rcs_and_a_modern_one():
    """Ana, Ben and Cal play three Pioneer RCs; Dee plays one and beats Eve four times, so Dee holds the top Rating
    (about 1565 against Ana's 1552) but is not eligible. Ana and Ben then meet at one Modern RC."""
    eve = ("eve", "Eve Moss")
    return [
        (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0), bye(CAL)])], field(1, 3, {1: ANA, 2: BEN, 3: CAL})),
        (2, "Pioneer", [(SWISS, [played(ANA, CAL, 2, 0), bye(BEN)])], field(2, 3, {1: ANA, 2: BEN, 3: CAL})),
        (3, "Pioneer", [(SWISS, [played(BEN, CAL, 2, 0)])] + [(SWISS, [played(DEE, eve, 2, 0)])] * 4,
         field(3, 5, {1: DEE, 2: BEN, 3: CAL, 4: ANA, 5: eve})),
        (4, "Modern", [(SWISS, [played(ANA, BEN, 2, 0)])], field(4, 2, {1: ANA, 2: BEN})),
    ]


def test_the_rank_counts_only_players_eligible_in_the_view(tmp_path):
    bundle = run_build(tmp_path, three_pioneer_rcs_and_a_modern_one())

    def standing_in(slug, view="Global"):
        return bundle.card(slug)["summary"][view]["rank"]

    assert bundle.card("dee")["ratings"]["Global"]["rating"] > bundle.card("ana")["ratings"]["Global"]["rating"]
    assert [standing_in(slug) for slug in ("ana", "ben", "cal")] == [1, 2, 3]
    assert standing_in("dee") is None
    assert standing_in("eve") is None
    assert standing_in("ana", "Pioneer") == 1
    assert standing_in("ana", "Modern") is None  # ranked in Global, two RCs short in Modern
    assert {"above", "rcs_needed", "top_8_rate"}.isdisjoint(bundle.card("ana")["summary"]["Global"])


# The RC table (issue #8): each RC's Rating at its start and end, and each Match's Rating change, per view.


def three_rcs_with_a_format_between():
    """Ana: a Modern RC, a Pioneer RC, then Modern again, so her Modern Ratings skip the Pioneer RC.

    Cycle 1: Ana beats Ben (+18), has a bye, then an Intentional Draw with Cal; Cal beats Dee. Cycle 2: Cal beats Ana,
    1518 v 1518 in Global (-18) and 1500 v 1500 in Pioneer (-18). Cycle 3: Ana beats Dee, 1500 v 1482 in Global
    (expected 0.509122, so +36 x 0.490878 = +17.67) and 1518 v 1482 in Modern (expected 0.518238, so +17.34).
    """
    return [
        (1, "Modern", [(SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 2, 0)]), (SWISS, [bye(ANA)]),
                       (SWISS, [played(ANA, CAL, 0, 0, draws=3, table=1)])], field(1, 4, {1: ANA, 2: CAL, 3: BEN, 4: DEE})),
        (2, "Pioneer", [(SWISS, [played(CAL, ANA, 2, 1)])], field(2, 2, {1: CAL, 2: ANA})),
        (3, "Modern", [(SWISS, [played(ANA, DEE, 2, 0)])], field(3, 2, {1: ANA, 2: DEE})),
    ]


def test_each_rc_gives_its_rating_at_start_and_end_in_global_and_its_format(tmp_path):
    bundle = run_build(tmp_path, three_rcs_with_a_format_between())

    ana = bundle.card("ana")
    assert [(rc["rating_start"], rc["rating_end"]) for rc in ana["rcs"]] == [
        ({"Global": 1500.0, "Modern": 1500.0}, {"Global": 1518.0, "Modern": 1518.0}),  # a first RC starts at 1500
        ({"Global": 1518.0, "Pioneer": 1500.0}, {"Global": 1500.0, "Pioneer": 1482.0}),
        ({"Global": 1500.0, "Modern": 1518.0}, {"Global": 1518, "Modern": 1535}),  # Modern picks up from Cycle 1: 1517.67, 1535.34
    ]
    assert [m["change"] for m in ana["matches"]] == [
        {"Global": 18.0, "Modern": 18.0},
        None,  # the bye
        None,  # the Intentional Draw
        {"Global": -18.0, "Pioneer": -18.0},
        {"Global": 18, "Modern": 17},  # the difference of the whole Ratings, so the card adds up (17.67 and 17.34 exactly)
    ]
    assert [m["rating_after"] for m in ana["matches"]] == [
        {"Global": 1518.0, "Modern": 1518.0},
        None,
        None,
        {"Global": 1500.0, "Pioneer": 1482.0},
        {"Global": 1518, "Modern": 1535},
    ]
    assert [rc["win_rate"] for rc in ana["rcs"]] == [{"rate": 100.0, "matches": 1}, {"rate": 0.0, "matches": 1}, {"rate": 100.0, "matches": 1}]


def test_each_rcs_start_plus_its_changes_is_its_end_and_the_next_rc_starts_there(tmp_path):
    bundle = run_build(tmp_path, three_rcs_with_a_format_between())

    for slug in ("ana", "ben", "cal", "dee"):
        card = bundle.card(slug)
        last_end = {}
        for rc in card["rcs"]:
            for view in rc["rating_start"]:
                changes = [m["change"][view] for m in card["matches"] if m["cycle"] == rc["cycle"] and m["change"]]
                assert rc["rating_start"][view] + sum(changes) == rc["rating_end"][view]
                assert rc["rating_start"][view] == last_end.get(view, 1500.0)
                last_end[view] = rc["rating_end"][view]
            assert rc["rating_end"]["Global"] == card["ratings"]["Global"]["after_rc"][card["rcs"].index(rc)]["rating"]


def test_each_rc_gives_the_ratings_of_its_typical_player_its_top_10_percent_and_its_highest(tmp_path):
    # After Cycle 1: Ana 1518 (beat Ben), Ben 1482, Cal and Dee 1500 (a played draw). Sorted 1482, 1500, 1500, 1518:
    # the median is 1500, the 90th percentile sits 0.9 x 3 = 2.7 places up, 1500 + 0.7 x 18 = 1512.6 (shown 1513), and Ana
    # is highest.
    rounds = [(SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 1, 1)])]
    bundle = run_build(tmp_path, [(1, "Modern", rounds, field(1, 4, {1: ANA, 2: CAL, 3: DEE, 4: BEN}))])

    assert bundle.rcs()[0]["field_rating"] == {"median": 1500, "top_10": 1513, "highest": 1518}


# The Leaderboard (issue #9): the top 50 eligible Players in Global and each shipped Format.


def test_the_leaderboard_ranks_only_players_eligible_in_the_view_by_rating(tmp_path):
    bundle = run_build(tmp_path, three_pioneer_rcs_and_a_modern_one())

    leaderboard = bundle.leaderboard()
    assert [(row["rank"], row["slug"]) for row in leaderboard["Global"]["players"]] == [(1, "ana"), (2, "ben"), (3, "cal")]
    assert [(row["rank"], row["slug"]) for row in leaderboard["Pioneer"]["players"]] == [(1, "ana"), (2, "ben"), (3, "cal")]
    assert leaderboard["Modern"]["players"] == []  # one Modern RC each, two short of the cutoff
    assert "Standard" not in leaderboard  # no Standard RC played
    ratings_in_order = [row["rating"] for row in leaderboard["Global"]["players"]]
    assert ratings_in_order == sorted(ratings_in_order, reverse=True)


def test_a_leaderboard_row_carries_the_players_rating_record_and_finishes_in_the_view(tmp_path):
    bundle = run_build(tmp_path, three_rcs_for_ana())

    (row,) = bundle.leaderboard()["Global"]["players"]  # only Ana has 3 RCs
    assert row == {
        "rank": 1,
        "slug": "ana",
        "name": "Ana Lopez",
        "rating": bundle.card("ana")["ratings"]["Global"]["rating"],
        "peak": 1518,  # 1517.67 after Cycle 1: +18 over Ben, then -0.33 for a played draw with Cal at 1500
        "record": "2-1-2",
        "win_rate": {"rate": 66.7, "matches": 3},
        "rcs": 3,
        "top_8s": 2,
        "finals": 1,
        "best_finish": "Winner",
        "last_rc": 3,
    }
    assert bundle.leaderboard()["Pioneer"]["players"] == []  # two Pioneer RCs


def test_the_leaderboard_shows_the_top_50_of_more_eligible_players(tmp_path):
    # 60 Players at three Modern RCs, each RC the even-numbered Player beating the next: 30 winners above 30 losers.
    field_ = [(f"p{n:02}", f"Player {n:02}") for n in range(60)]
    matches = [played(field_[n], field_[n + 1], 2, 0) for n in range(0, 60, 2)]
    standings = [standing(rank, who) for rank, who in enumerate(field_, start=1)]
    bundle = run_build(tmp_path, [(cycle, "Modern", [(SWISS, matches)], standings) for cycle in (1, 2, 3)])

    rows = bundle.leaderboard()["Global"]["players"]
    assert len(rows) == 50
    assert {row["slug"] for row in rows} >= {f"p{n:02}" for n in range(0, 60, 2)}
    assert [row["rank"] for row in rows] == [1] * 30 + [31] * 20  # tied Players share a rank


def test_each_leaderboard_view_counts_every_ranked_player_beyond_the_top_50(tmp_path):
    # Issue #12: the Leaderboard's note says how many Players are ranked in its view. 60 Players at three Modern RCs:
    # all 60 are ranked in Global and Modern though 50 are shown.
    field_ = [(f"p{n:02}", f"Player {n:02}") for n in range(60)]
    matches = [played(field_[n], field_[n + 1], 2, 0) for n in range(0, 60, 2)]
    standings = [standing(rank, who) for rank, who in enumerate(field_, start=1)]
    bundle = run_build(tmp_path, [(cycle, "Modern", [(SWISS, matches)], standings) for cycle in (1, 2, 3)])

    assert {view: board["ranked"] for view, board in bundle.leaderboard().items()} == {"Global": 60, "Modern": 60}


def test_a_view_nobody_is_ranked_in_counts_none(tmp_path):
    bundle = run_build(tmp_path, three_pioneer_rcs_and_a_modern_one())

    # Ana, Ben and Cal ranked; Dee and Eve one RC each; nobody has three Modern RCs.
    assert {view: board["ranked"] for view, board in bundle.leaderboard().items()} == {"Global": 3, "Pioneer": 3, "Modern": 0}


# Compare Players (issue #10): the card's Player against the Players compared with them.


def test_the_head_to_head_counts_every_match_two_players_played_across_every_format(tmp_path):
    # Cycle 1, Modern: Ana and Ben draw 1-1-1 (a played draw, not a 0-0-3), then Ana beats Cal.
    modern = [(SWISS, [played(ANA, BEN, 1, 1, draws=1, table=9)]), (SWISS, [played(ANA, CAL, 2, 0), played(BEN, DEE, 2, 0)])]
    # Cycle 2, Pioneer: an Intentional Draw at table 1 in the only Swiss round, then a bracket seeded Ben 1, Ana 2
    # whose final Melee lost, rebuilt as Ben beating Ana.
    p = {n: (f"p{n}", f"Player {n}") for n in range(3, 9)}
    pioneer = [
        (SWISS, [played(ANA, BEN, 0, 0, draws=3, table=1), played(p[3], p[4], 2, 0, table=2), played(p[5], p[6], 2, 0, table=3), played(p[7], p[8], 2, 0, table=4)]),
        (PLAYOFFS, [played(BEN, p[8], 2, 0), played(p[4], p[5], 2, 1), played(ANA, p[7], 2, 0), played(p[3], p[6], 2, 0)]),
        (PLAYOFFS, [played(BEN, p[4], 2, 0), played(ANA, p[3], 2, 1)]),
        (PLAYOFFS, []),
    ]
    bundle = run_build(tmp_path, [
        (1, "Modern", modern, field(1, 4, {1: ANA, 2: BEN, 3: CAL, 4: DEE})),
        (2, "Pioneer", pioneer, field(2, 8, {1: BEN, 2: ANA} | {n: p[n] for n in range(3, 9)})),
    ])

    ana, ben = bundle.card("ana"), bundle.card("ben")
    # Ana: the played draw in Modern, the Intentional Draw and the rebuilt final lost in Pioneer.
    assert ana["head_to_head"]["ben"] == "0-1-2"
    assert ben["head_to_head"]["ana"] == "1-0-2"
    assert ana["head_to_head"]["cal"] == "1-0-0"
    # Ana and Dee never met.
    assert "dee" not in ana["head_to_head"]
    assert "ana" not in bundle.card("dee")["head_to_head"]
