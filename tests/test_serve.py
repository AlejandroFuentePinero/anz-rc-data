"""The server the Space runs (issue #14): the site as built, and the site's own record of its use."""

import json
import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from anzrc.serve import create_app
from anzrc.usage import report

SITE = Path(__file__).parent.parent / "site"
A_PLAYER = json.loads((SITE / "data" / "players.json").read_text())[0]


def lines(folder: Path) -> list[dict]:
    return [json.loads(line) for path in sorted(folder.rglob("*.jsonl")) for line in path.read_text().splitlines()]


def visit(usage, *requests):
    """Run the app as the Space does, make the requests, and stop it, which writes the record."""
    with TestClient(create_app(SITE, usage)) as client:
        return [client.get(path, headers=headers) for path, headers in requests]


def test_serves_the_site_as_built(tmp_path):
    overview, leaderboard, player, bundle = visit(
        tmp_path, ("/", {}), ("/leaderboard.html", {}), ("/player.html", {}), ("/data/leaderboard.json", {})
    )
    assert overview.text == (SITE / "index.html").read_text()
    assert leaderboard.text == (SITE / "leaderboard.html").read_text()
    assert player.text == (SITE / "player.html").read_text()
    assert bundle.json() == json.loads((SITE / "data" / "leaderboard.json").read_text())


def test_a_visitor_gets_the_same_bytes_whether_or_not_visits_are_recorded(tmp_path):
    requests = [(path, {"referer": "https://discord.com/x", "sec-fetch-dest": "document"}) for path in
                ("/", "/leaderboard.html", "/player.html", "/data/players.json", f"/data/players/{A_PLAYER['slug']}.json",
                 "/site.css", "/no-such-file")]
    recorded, unrecorded = visit(tmp_path, *requests), visit(None, *requests)
    assert any(line["kind"] == "read" for line in lines(tmp_path))
    for on, off in zip(recorded, unrecorded):
        assert (on.status_code, on.content) == (off.status_code, off.content)
        assert {k: v for k, v in on.headers.items() if k != "date"} == {k: v for k, v in off.headers.items() if k != "date"}


def test_browsers_check_back_on_every_load(tmp_path):
    """A copy kept without asking is a load the record never sees, and stale data after a deploy."""
    for response in visit(tmp_path, ("/", {}), (f"/data/players/{A_PLAYER['slug']}.json", {})):
        assert response.headers["cache-control"] == "no-cache"


def test_notes_a_page_with_the_site_it_came_from(tmp_path):
    visit(tmp_path, ("/player.html", {"referer": "https://discord.com/channels/1/2?x=y"}), ("/leaderboard.html", {}))
    pages = [line for line in lines(tmp_path) if line["kind"] == "page"]
    assert [(p["page"], p["ref"]) for p in pages] == [("player", "discord.com"), ("leaderboard", None)]


def test_a_page_says_what_the_browser_fetched_it_as_and_the_first_names_the_headers_that_arrived(tmp_path):
    """What the Hub's proxy passes on cannot be seen from outside, so the first page of each run lists it."""
    visit(tmp_path, ("/", {"sec-fetch-dest": "document", "x-forwarded-proto": "https"}),
          ("/leaderboard.html", {"sec-fetch-dest": "iframe"}))
    first, second = [line for line in lines(tmp_path) if line["kind"] == "page"]
    assert (first["dest"], second["dest"]) == ("document", "iframe")
    assert {"sec-fetch-dest", "x-forwarded-proto", "host"} <= set(first["names"])
    assert "names" not in second


def test_notes_a_browser_load_by_the_player_list_every_page_asks_for(tmp_path):
    visit(tmp_path, ("/data/players.json", {}), ("/site.css", {}))
    assert [line["kind"] for line in lines(tmp_path) if line["kind"] != "start"] == ["browser"]


def test_a_fetcher_that_runs_no_script_is_a_page_and_never_a_browser_load(tmp_path):
    """What `curl https://.../` does: one request for the page, nothing it asks for after."""
    visit(tmp_path, ("/", {"user-agent": "curl/8.7.1", "accept": "*/*"}))
    assert [(line["kind"], line.get("dest")) for line in lines(tmp_path) if line["kind"] != "start"] == [("page", None)]


def test_notes_a_player_loaded(tmp_path):
    visit(tmp_path, (f"/data/players/{A_PLAYER['slug']}.json", {}))
    reads = [line for line in lines(tmp_path) if line["kind"] == "read"]
    assert [read["view"] for read in reads] == [A_PLAYER["slug"]]


def test_a_player_loaded_again_from_the_browsers_copy_still_counts(tmp_path):
    path = f"/data/players/{A_PLAYER['slug']}.json"
    with TestClient(create_app(SITE, tmp_path)) as client:
        first = client.get(path)
        again = client.get(path, headers={"if-none-match": first.headers["etag"]})
    assert again.status_code == 304
    assert [line["view"] for line in lines(tmp_path) if line["kind"] == "read"] == [A_PLAYER["slug"]] * 2


def test_keeps_no_slug_that_is_not_a_player(tmp_path):
    visit(tmp_path, ("/data/players/someone-made-up.json", {}))
    assert [line for line in lines(tmp_path) if line["kind"] == "read"] == []


def test_keeps_nothing_that_tells_one_visitor_from_another(tmp_path):
    visit(tmp_path, ("/", {"referer": "https://discord.com/x", "user-agent": "Mozilla/5.0", "cookie": "a=b"}),
          ("/data/players.json", {}), (f"/data/players/{A_PLAYER['slug']}.json", {}))
    for line in lines(tmp_path):
        assert set(line) <= {"v", "run", "t", "kind", "host", "page", "ref", "dest", "names", "view"}


def test_writes_a_start_line_in_the_record_format_control_room_reads(tmp_path):
    visit(tmp_path)
    (start,) = lines(tmp_path)
    assert start["kind"] == "start" and start["v"] == 1
    (path,) = tmp_path.rglob("*.jsonl")
    assert path.relative_to(tmp_path).parts[:3] == tuple(start["t"][:10].split("-"))


def test_no_folder_named_means_no_record_and_the_site_still_serves():
    (overview,) = visit(None, ("/", {}))
    assert overview.status_code == 200


def test_a_folder_that_is_not_there_is_said_loudly_and_the_site_still_serves(tmp_path, capsys):
    (overview,) = visit(tmp_path / "not-mounted", ("/", {}))
    assert overview.status_code == 200
    assert "*** USAGE RECORD OFF" in capsys.readouterr().out


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes to a read-only folder")
def test_a_record_that_cannot_be_written_is_said_loudly_and_the_site_still_serves(tmp_path, capsys):
    tmp_path.chmod(0o500)
    try:
        (overview,) = visit(tmp_path, ("/", {}))
    finally:
        tmp_path.chmod(0o700)
    assert overview.status_code == 200
    assert "*** USAGE RECORD NOT WRITTEN" in capsys.readouterr().out


def test_reports_visits_and_players_loaded_by_day(tmp_path):
    slug = A_PLAYER["slug"]
    visit(tmp_path, ("/player.html", {"referer": "https://discord.com/x"}), ("/data/players.json", {}),
          (f"/data/players/{slug}.json", {}), (f"/data/players/{slug}.json", {}))
    text = report(tmp_path, SITE, by="day")
    day = next(line for line in text.splitlines() if line[:4].isdigit())
    assert day.split()[1:] == ["1", "1", "2"]
    assert "discord.com" in text
    assert any(A_PLAYER["name"] in line and line.split()[-1] == "2" for line in text.splitlines())


def test_reports_an_empty_record_plainly(tmp_path):
    assert report(tmp_path, SITE, by="week") == f"No usage recorded under {tmp_path}.\n"
