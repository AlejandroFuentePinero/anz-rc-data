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
            "finish": "Title",
            "field_size": 4,
            "record": "1-0-0",
            "deck": "Rakdos Midrange",
            "decklist": "https://melee.gg/Decklist/View/d-ana",
        }
    ]
    assert card["matches"] == [
        {"cycle": 1, "round": "Round 1", "opponent": {"slug": "ben", "name": "Ben Hall"}, "result": "Win", "games": "2-1-0",
         "reconstructed": False, "opponent_rating": {"Global": 1500.0, "Pioneer": 1500.0}}
    ]
    assert bundle.card("ben")["matches"][0]["result"] == "Loss"
    assert bundle.card("ben")["matches"][0]["games"] == "1-2-0"


def test_the_rc_table_gives_each_rc_its_field_size_and_champion_as_the_player_their_card_names(tmp_path):
    owner = ("alejandrofp", "alejandrofp")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(2, ANA), standing(1, BEN), standing(3, CAL)]),
            (2, "Modern", [(SWISS, [played(owner, ANA, 2, 0)])], [standing(1, owner), standing(2, ANA)]),
        ],
        curation='[display_names]\nalejandrofp = "Alejandro de la Fuente"\n',
    )

    assert [{key: rc[key] for key in ("cycle", "date", "city", "format", "field_size", "champion")} for rc in bundle.rcs()] == [
        {"cycle": 1, "date": "2023-01-01", "city": None, "format": "Pioneer", "field_size": 3,
         "champion": {"slug": "ben", "name": "Ben Hall"}},
        {"cycle": 2, "date": "2023-02-01", "city": None, "format": "Modern", "field_size": 2,
         "champion": {"slug": "alejandrofp", "name": "Alejandro de la Fuente"}},
    ]


def test_the_rc_table_gives_each_rc_its_top_8_by_tier_in_melees_order_as_players(tmp_path):
    p = {n: (f"p{n}", f"Player {n}") for n in range(1, 11)}
    p[6] = ("Ana_L", "Ana Lopez")  # Ana's second account, one Player with "ana" by the real-name rule
    # Melee's rows out of rank order, so the table follows the Rank, not the row order.
    ranks = {3: 1, 7: 2, 1: 3, 9: 4, 6: 5, 2: 6, 10: 7, 4: 8, 5: 9, 8: 10}
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(p[n], p[n + 1], 2, 0) for n in range(1, 11, 2)])],
             [standing(ranks[n], p[n]) for n in range(1, 11)]),
        ],
    )

    player = lambda slug, name: {"slug": slug, "name": name}
    rc = bundle.rcs()[1]
    assert {key: rc[key] for key in ("champion", "finalist", "places_3_4", "places_5_8")} == {
        "champion": player("p3", "Player 3"),
        "finalist": player("p7", "Player 7"),
        "places_3_4": [player("p1", "Player 1"), player("p9", "Player 9")],
        "places_5_8": [player("ana", "Ana Lopez"), player("p2", "Player 2"), player("p10", "Player 10"), player("p4", "Player 4")],
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

    assert bundle.community()["top_8_rate_by_experience"] == [
        {"level": "1st", "top_8s": 1, "seats": 2, "rate": 50.0},  # n1 of n1, n2
        {"level": "2nd-3rd", "top_8s": 7, "seats": 8, "rate": 87.5},  # p2 to p8 of p1 to p8
        {"level": "4th-7th", "top_8s": 0, "seats": 0, "rate": None},
        {"level": "8th+", "top_8s": 0, "seats": 0, "rate": None},
    ]


def test_the_community_captions_give_the_typical_first_rc_share_and_how_many_players_reached_a_title_and_a_top_8(tmp_path):
    eve = ("eve", "Eve Moss")
    bundle = run_build(
        tmp_path,
        [
            (1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(1, ANA), standing(2, BEN)]),
            (2, "Modern", [(SWISS, [played(CAL, ANA, 2, 0)])], [standing(1, CAL), standing(2, ANA)]),  # cal new: 50%
            (3, "Modern", [(SWISS, [played(ANA, BEN, 2, 0), played(CAL, DEE, 2, 0)])],
             [standing(1, ANA), standing(2, BEN), standing(3, CAL), standing(4, DEE)]),  # dee new: 25%
            (4, "Pioneer", [(SWISS, [played(BEN, ANA, 2, 0)])], [standing(1, BEN), standing(2, ANA)]),  # 0%
            (5, "Pioneer", [(SWISS, [played(eve, ANA, 2, 0)])], [standing(1, eve), standing(2, ANA)]),  # eve new: 50%
        ],
    )

    community = bundle.community()
    # The median of 50, 25, 0 and 50, the first RC aside: the middle two are 25 and 50.
    assert community["typical_first_rc_share"] == 37.5
    assert (community["champions"], community["top_8_players"], community["top_8_places"]) == (4, 5, 12)


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

    champion, finalist = bundle.card("p4"), bundle.card("p3")
    for card in (champion, finalist):  # the opponent's Rating is tested on its own
        del card["matches"][-1]["opponent_rating"]
    assert champion["matches"][-1] == {
        "cycle": 1, "round": "Final", "opponent": {"slug": "p3", "name": "Player 3"}, "result": "Win", "games": None, "reconstructed": True
    }
    assert finalist["matches"][-1] == {
        "cycle": 1, "round": "Final", "opponent": {"slug": "p4", "name": "Player 4"}, "result": "Loss", "games": None, "reconstructed": True
    }
    assert [m["reconstructed"] for m in champion["matches"][:-1]] == [False, False, False]
    # Swiss loss, then the quarterfinal, the semifinal and the rebuilt final won.
    assert champion["rcs"][0]["record"] == "3-1-0"
    assert finalist["rcs"][0]["record"] == "3-1-0"
    assert (champion["rcs"][0]["finish"], finalist["rcs"][0]["finish"]) == ("Title", "Finalist")


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


def test_finishes_show_title_finalist_and_top_4_and_top_8_tiers_never_melees_order_inside_a_tier(tmp_path):
    field = [(f"p{n}", f"Player {n}") for n in range(1, 11)]
    rounds = [(SWISS, [played(field[n], field[n + 1], 2, 0) for n in range(0, 10, 2)])]
    final = [standing(n, who) for n, who in enumerate(field, start=1)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    finishes = [(bundle.card(f"p{n}")["rcs"][0]["finish"], bundle.card(f"p{n}")["rcs"][0]["field_size"]) for n in range(1, 11)]
    assert finishes == [
        ("Title", 10),
        ("Finalist", 10),
        ("Top 4", 10),
        ("Top 4", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("Top 8", 10),
        ("9th", 10),
        ("10th", 10),
    ]


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
        {"cycle": 1, "date": "2023-01-01", "format": "Modern", "finish": None, "field_size": 3, "record": "0-1-0", "deck": "Boros Energy",
         "decklist": "https://melee.gg/Decklist/View/d-dee"}
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
    assert [(rc["cycle"], rc["finish"]) for rc in ana["rcs"]] == [(1, "Title"), (2, "Finalist")]
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

    assert rating(bundle, "ana") == pytest.approx(1518 - 0.66, abs=0.01)
    assert rating(bundle, "ben") == pytest.approx(1482 + 0.66, abs=0.01)


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
    assert rating(bundle, "ana") == pytest.approx(1518 - 18.66, abs=0.01)
    assert rating(bundle, "ben") == pytest.approx(1482 + 18.66, abs=0.01)
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
    assert ana["after_rc"] == [{"cycle": 1, "rating": 1518.0}, {"cycle": 2, "rating": 1518.0}, {"cycle": 3, "rating": 1499.67}]
    assert ana["peak"] == 1518.0
    assert ana["rating"] == 1499.67
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
    assert rating(bundle, "ana") == pytest.approx(1518 - 0.66, abs=0.01)  # the draw from 1518 v 1482, as worked above


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
    assert rating(bundle, "ana") == pytest.approx(1518 - 0.66, abs=0.01)  # the early draw moves, the late top-table one not
    assert rating(bundle, "cal") == pytest.approx(1518 - 0.66, abs=0.01)  # the late table-9 draw moves
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
