"""The build, driven through its public interface: raw folder, RC list and curation file in, bundle out.

Fixtures are small RCs in Melee's response shapes, cut down from real responses. A Player is written as
(username, display name); Melee shows the username as the display name when a Player hides their real name.
"""

import json

import pytest

from anzrc.build import build

SWISS, PLAYOFFS = "Swiss", "Playoffs/Top Cut"


def melee_player(who):
    username, display_name = who
    return {"DisplayName": display_name, "Username": username}


def competitor(who, game_wins):
    return {"GameWins": game_wins, "Team": {"Players": [melee_player(who)]}, "Decklists": []}


def played(a, b, a_wins, b_wins, draws=0):
    """A Match with a result between two Players. Melee leaves a loser's game wins null at times."""
    return {
        "Competitors": [competitor(a, a_wins), competitor(b, b_wins)],
        "GameDraws": draws,
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
    """Cycle 13's one Match without a result."""
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
         "reconstructed": False}
    ]
    assert bundle.card("ben")["matches"][0]["result"] == "Loss"
    assert bundle.card("ben")["matches"][0]["games"] == "1-2-0"


def test_the_rc_table_gives_each_rc_its_field_size_and_champion(tmp_path):
    bundle = run_build(
        tmp_path,
        [(1, "Pioneer", [(SWISS, [played(ANA, BEN, 2, 0)])], [standing(2, ANA), standing(1, BEN), standing(3, CAL)])],
    )

    assert bundle.rcs() == [
        {"cycle": 1, "date": "2023-01-01", "city": None, "format": "Pioneer", "field_size": 3, "champion": "Ben Hall"}
    ]


def test_every_match_class_shows_its_result_and_only_played_matches_and_intentional_draws_count_in_the_record(tmp_path):
    rounds = [
        (SWISS, [played(ANA, BEN, 1, 0), played(CAL, DEE, None, 2)]),  # 1-0-0, and a null loser read as 0
        (SWISS, [played(ANA, CAL, 1, 0, draws=1), played(BEN, DEE, 0, 3)]),  # 1-0-1 and 3-0-0
        (SWISS, [played(ANA, DEE, 1, 1), played(BEN, CAL, 1, 1, draws=1)]),  # played draws 1-1-0 and 1-1-1
        (SWISS, [played(ANA, BEN, 0, 0, draws=3), played(CAL, DEE, 0, 0, draws=3)]),  # Intentional Draws
        (SWISS, [bye(ANA), late_entry_forfeit(BEN), not_reported(CAL)]),
        (SWISS, [no_result(ANA, DEE)]),
    ]
    final = [standing(1, DEE), standing(2, ANA), standing(3, CAL), standing(4, BEN)]

    bundle = run_build(tmp_path, [(1, "Modern", rounds, final)])

    ana = bundle.card("ana")
    assert [(m["round"], m["opponent"] and m["opponent"]["slug"], m["result"], m["games"]) for m in ana["matches"]] == [
        ("Round 1", "ben", "Win", "1-0-0"),
        ("Round 2", "cal", "Win", "1-0-1"),
        ("Round 3", "dee", "Draw", "1-1-0"),
        ("Round 4", "ben", "Intentional Draw", "0-0-3"),
        ("Round 5", None, "Bye", None),
        ("Round 6", "dee", "No result", None),
    ]
    assert ana["rcs"][0]["record"] == "2-0-2"
    assert [(m["result"], m["games"]) for m in bundle.card("ben")["matches"]] == [
        ("Loss", "0-1-0"),
        ("Loss", "0-3-0"),
        ("Draw", "1-1-1"),
        ("Intentional Draw", "0-0-3"),
        ("Forfeit", None),
    ]
    assert bundle.card("ben")["rcs"][0]["record"] == "0-2-2"
    assert [m["result"] for m in bundle.card("cal")["matches"]][-1] == "Not reported"
    assert bundle.card("dee")["rcs"][0]["record"] == "2-0-2"


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
