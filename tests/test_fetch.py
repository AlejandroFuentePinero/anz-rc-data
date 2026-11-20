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


def melee(**overrides):
    responses = {
        "https://melee.gg/Tournament/View/12737": EVENT_PAGE,
        "https://melee.gg/Match/GetRoundMatches/501": grid([{"TableNumber": 1}, {"TableNumber": 2}]),
        "https://melee.gg/Match/GetRoundMatches/502": grid([{"TableNumber": 1}]),
        "https://melee.gg/Standing/GetRoundStandings?roundId=501": grid([{"Rank": 1}, {"Rank": 2}]),
        "https://melee.gg/Standing/GetRoundStandings?roundId=502": grid([{"Rank": 1}, {"Rank": 2}]),
    }
    return FakeMelee(responses | overrides)


def test_stores_event_page_and_every_rounds_matches_and_standings_unchanged(tmp_path):
    fake = melee()

    fetch_rc(12737, tmp_path, fake, delay=0)

    folder = tmp_path / "12737"
    assert (folder / "event.html").read_bytes() == EVENT_PAGE
    for round_id in ("501", "502"):
        assert (folder / f"matches-{round_id}.json").read_bytes() == fake.responses[
            f"https://melee.gg/Match/GetRoundMatches/{round_id}"
        ]
        assert (folder / f"standings-{round_id}.json").read_bytes() == fake.responses[
            f"https://melee.gg/Standing/GetRoundStandings?roundId={round_id}"
        ]
    assert len(fake.requests) == 5


def test_a_rerun_fetches_nothing_new(tmp_path):
    fetch_rc(12737, tmp_path, melee(), delay=0)
    rerun = melee()

    fetch_rc(12737, tmp_path, rerun, delay=0)

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
        fetch_rc(12737, tmp_path, fake, delay=0)

    assert not (tmp_path / "12737" / "standings-502.json").exists()
