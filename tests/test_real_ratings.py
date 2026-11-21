"""The shipped bundle against the real RCs: it is what the build makes from the raw files today, and every Rating in it
is the independent replay's (tests/independent_replay.py), rounded once to a whole number."""

import json
import math
from functools import cache
from pathlib import Path

from independent_replay import replay

from anzrc import build, rcs

BUNDLE = Path("site/data")
PLAYOFF_ORDER = {"Quarterfinal": 1, "Semifinal": 2, "Final": 3}


def whole(rating: float) -> int:
    return math.floor(rating + 0.5)


@cache
def independent() -> dict:
    return replay(rcs.RAW, rcs.RC_LIST, build.CURATION)


def cards(bundle: Path) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text()) for path in (bundle / "players").glob("*.json")}


def test_the_shipped_bundle_is_what_the_build_makes_from_the_raw_files_today(tmp_path):
    build.build(rcs.RAW, rcs.RC_LIST, build.CURATION, tmp_path)

    built = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*.json")}
    shipped = {p.relative_to(BUNDLE): p.read_bytes() for p in BUNDLE.rglob("*.json")}
    assert sorted(built) == sorted(shipped)
    assert [path for path in built if built[path] != shipped[path]] == []


def check_players(bundle: Path) -> None:
    """The same Players, each the same set of Melee accounts."""
    assert sorted(map(sorted, independent()["players"])) == sorted(sorted(card["usernames"]) for card in cards(bundle).values())


def check_ratings(bundle: Path) -> int:
    """Every Rating after every RC, current and Peak, in every view. Returns how many values were compared."""
    ours, compared = independent(), 0
    for card in cards(bundle).values():
        pid = ours["players"][frozenset(card["usernames"])]
        for view, shown in card["ratings"].items():
            exact = ours["after_rc"][shown.get("rated_by", view)][pid]
            assert shown["after_rc"] == [{"cycle": c, "rating": whole(exact[c])} for c in sorted(exact)], (card["slug"], view)
            assert (shown["rating"], shown["peak"]) == (whole(exact[max(exact)]), whole(max(exact.values()))), (card["slug"], view)
            compared += len(exact) + 2
    return compared


def check_matches(bundle: Path) -> int:
    """Every Match row: opponent, the opponent's Rating, the Rating after it, and a change that is the difference of the
    two whole Ratings. Returns how many rows were compared."""
    ours, all_cards = independent(), cards(bundle)
    pid_of = {slug: ours["players"][frozenset(card["usernames"])] for slug, card in all_cards.items()}
    sides = {}
    for side in ours["sides"]:
        sides.setdefault(side["pid"], []).append(side)
    compared = 0
    for slug, card in all_cards.items():
        mine = sorted(sides[pid_of[slug]], key=lambda s: (s["cycle"], s["playoff"], s["round"]))
        assert len(mine) == len(card["matches"]), slug
        for side, match in zip(mine, card["matches"]):
            where = (slug, match["cycle"], match["round"])
            assert match["playoff"] == side["playoff"], where
            assert (pid_of[match["opponent"]["slug"]] if match["opponent"] else None) == side["opponent"], where
            if match["opponent"]:
                assert match["opponent_rating"] == {view: whole(side["opponent_before"][view]) for view in match["opponent_rating"]}, where
            if side["rated"]:
                assert match["rating_after"] == {view: whole(side["after"][view]) for view in match["rating_after"]}, where
                assert match["change"] == {view: whole(side["after"][view]) - whole(side["before"][view]) for view in match["change"]}, where
            else:
                assert (match["change"], match["rating_after"]) == (None, None), where
            compared += 1
    return compared


def check_rcs(bundle: Path) -> int:
    """Every RC row starts and ends on the replay's Ratings, and its start plus its changes is its end."""
    ours, compared = independent(), 0
    for card in cards(bundle).values():
        pid = ours["players"][frozenset(card["usernames"])]
        for rc in card["rcs"]:
            for view in rc["rating_start"]:
                assert rc["rating_start"][view] == whole(ours["start_rc"][view][pid][rc["cycle"]]), (card["slug"], rc["cycle"])
                assert rc["rating_end"][view] == whole(ours["after_rc"][view][pid][rc["cycle"]]), (card["slug"], rc["cycle"])
                changes = [m["change"][view] for m in card["matches"] if m["cycle"] == rc["cycle"] and m["change"]]
                assert rc["rating_start"][view] + sum(changes) == rc["rating_end"][view], (card["slug"], rc["cycle"])
                compared += 1
    return compared


def check_ranks(bundle: Path) -> int:
    """Every rank, by the replay's exact Ratings among the Players with 3 or more RCs in the view."""
    ours, all_cards, compared = independent(), cards(bundle), 0
    for view in ("Global", "Pioneer", "Standard", "Modern"):
        in_view = [card for card in all_cards.values() if view in card["summary"]]
        exact = {card["slug"]: ours["after_rc"][view][ours["players"][frozenset(card["usernames"])]] for card in in_view}
        current = {slug: points[max(points)] for slug, points in exact.items()}
        eligible = [current[card["slug"]] for card in in_view if card["summary"][view]["rcs"] >= 3]
        for card in in_view:
            expected = 1 + sum(other > current[card["slug"]] for other in eligible) if card["summary"][view]["rcs"] >= 3 else None
            assert card["summary"][view]["rank"] == expected, (card["slug"], view)
            compared += 1
    return compared


def test_every_player_is_the_same_set_of_melee_accounts_as_the_independent_replay_makes():
    check_players(BUNDLE)


def test_every_rating_after_every_rc_current_and_peak_is_the_independent_replays_rounded_once():
    assert check_ratings(BUNDLE) > 9000


def test_every_match_shows_the_independent_replays_ratings_and_a_change_that_adds_up():
    assert check_matches(BUNDLE) > 16000


def test_every_rc_starts_and_ends_on_the_independent_replays_ratings_and_its_changes_add_up():
    assert check_rcs(BUNDLE) > 4000


def test_every_rank_follows_the_independent_replays_exact_ratings():
    assert check_ranks(BUNDLE) > 2000
