"""The fetcher, driven against a fake Melee at the network boundary."""

import json

import pytest

from anzrc.fetch import fetch_rc

EVENT_PAGE = b"""<html><title>Cycle 1</title>
<div id="standings-round-selector-container" class="round-selector-container">
<button class="btn btn-gray round-selector" data-id="501" data-name="Round 1" data-is-completed="True">
<button class="btn btn-gray round-selector" data-id="502" data-name="Finals" data-is-completed="True">
</div>
<div id="pairings-round-selector-container" class="round-selector-container">
<button class="btn btn-gray round-selector" data-id="501" data-name="Round 1" data-is-started="True">
<button class="btn btn-gray round-selector" data-id="502" data-name="Finals" data-is-started="True">
</div></html>"""


def grid(rows):
    # Spacing kept odd on purpose: a stored file must be the bytes Melee sent, not a re-serialisation.
    return json.dumps({"draw": 1, "recordsTotal": len(rows), "data": rows}, indent=1).encode()


class FakeMelee:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def get(self, url):
        self.requests.append(url)
        return self.responses[url]

    def post(self, url, data):
        key = f"{url}?roundId={data['roundId']}" if "roundId" in data else url
        self.requests.append(key)
        return self.responses[key]


def decklist_page(text):
    """A Melee decklist page cut down to the block the fetcher reads; the text is HTML-escaped as Melee sends it."""
    return f"""<html><div class="decklist-container">...</div>
<pre class="d-none" id="decklist-text">{text}</pre>
<pre class="d-none" id="decklist-mtgo-text">ignored</pre></html>""".encode()


# Cycles 4 and 7: the companion is listed on its own and again in the sideboard.
COMPANION_TWICE = decklist_page("""MainDeck
4 Llanowar Elves
56 Forest

Companion
1 Jegantha, the Wellspring

Sideboard
14 Plains
1 Jegantha, the Wellspring

""")

# Cycle 13: the companion is listed on its own, and the sideboard holds the other 14.
COMPANION_ONCE = decklist_page("""MainDeck
4 Orim&#39;s Chant
1 Razorgrass Ambush // Razorgrass Field
55 Plains

Companion
1 Kaheera, the Orphanguard

Sideboard
14 Island

""")


def final_standing(rank, decklist_id):
    return {"Rank": rank, "Decklists": [{"DecklistId": decklist_id, "DecklistName": "Deck"}]}


def melee(**overrides):
    responses = {
        "https://melee.gg/Tournament/View/12737": EVENT_PAGE,
        "https://melee.gg/Match/GetRoundMatches/501": grid([{"TableNumber": 1}, {"TableNumber": 2}]),
        "https://melee.gg/Match/GetRoundMatches/502": grid([{"TableNumber": 1}]),
        "https://melee.gg/Standing/GetRoundStandings?roundId=501": grid([{"Rank": 1}, {"Rank": 2}]),
        "https://melee.gg/Standing/GetRoundStandings?roundId=502": grid([final_standing(1, "d-one"), final_standing(2, "d-two")]),
        "https://melee.gg/Decklist/View/d-one": COMPANION_TWICE,
        "https://melee.gg/Decklist/View/d-two": COMPANION_ONCE,
    }
    return FakeMelee(responses | overrides)


def test_stores_event_page_and_every_rounds_matches_and_standings_unchanged(tmp_path):
    fake = melee()

    fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", fake, delay=0)

    folder = tmp_path / "raw" / "12737"
    assert (folder / "event.html").read_bytes() == EVENT_PAGE
    for round_id in ("501", "502"):
        assert (folder / f"matches-{round_id}.json").read_bytes() == fake.responses[
            f"https://melee.gg/Match/GetRoundMatches/{round_id}"
        ]
        assert (folder / f"standings-{round_id}.json").read_bytes() == fake.responses[
            f"https://melee.gg/Standing/GetRoundStandings?roundId={round_id}"
        ]
    assert len(fake.requests) == 7


def test_a_rerun_fetches_nothing_new(tmp_path):
    fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", melee(), delay=0)
    rerun = melee()

    fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", rerun, delay=0)

    assert rerun.requests == []


@pytest.mark.parametrize(
    "response",
    [
        json.dumps({"Error": True, "Message": "Something went wrong"}).encode(),
        json.dumps({"draw": 1, "recordsTotal": 3, "data": [{"Rank": 1}]}).encode(),
    ],
    ids=["error", "truncated"],
)
def test_an_unusable_response_is_refused_and_not_stored(tmp_path, response):
    fake = melee(**{"https://melee.gg/Standing/GetRoundStandings?roundId=502": response})

    with pytest.raises(RuntimeError):
        fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", fake, delay=0)

    assert not (tmp_path / "raw" / "12737" / "standings-502.json").exists()


def stored_decklist(tmp_path, decklist_id):
    return json.loads((tmp_path / "decklists" / "12737" / f"{decklist_id}.json").read_text())


def test_stores_every_final_standings_decklist_with_main_deck_and_sideboard_apart(tmp_path):
    fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", melee(), delay=0)

    assert stored_decklist(tmp_path, "d-two") == {
        "decklist_id": "d-two",
        "main": [
            {"quantity": 4, "name": "Orim's Chant"},
            {"quantity": 1, "name": "Razorgrass Ambush // Razorgrass Field"},
            {"quantity": 55, "name": "Plains"},
        ],
        "sideboard": [{"quantity": 14, "name": "Island"}, {"quantity": 1, "name": "Kaheera, the Orphanguard"}],
        "companion": "Kaheera, the Orphanguard",
    }


def test_a_companion_listed_twice_counts_once_in_the_sideboard(tmp_path):
    fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", melee(), delay=0)

    deck = stored_decklist(tmp_path, "d-one")
    assert sum(card["quantity"] for card in deck["main"]) == 60
    assert sum(card["quantity"] for card in deck["sideboard"]) == 15
    assert deck["companion"] == "Jegantha, the Wellspring"


def test_an_unreadable_decklist_page_is_refused_and_not_stored(tmp_path):
    fake = melee(**{"https://melee.gg/Decklist/View/d-two": b"<html>Something went wrong</html>"})

    with pytest.raises(RuntimeError, match="d-two"):
        fetch_rc(12737, tmp_path / "raw", tmp_path / "decklists", fake, delay=0)

    assert not (tmp_path / "decklists" / "12737" / "d-two.json").exists()
