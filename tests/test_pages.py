"""The site's pages as a browser renders them from the shipped bundle (issue #12): headless Chrome loads each page from
a local server and the test reads the finished DOM. Skipped where Chrome is not installed."""

import functools
import html
import http.server
import json
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

SITE = Path(__file__).parent.parent / "site"
BUNDLE = json.loads((SITE / "data" / "leaderboard.json").read_text())
COMMUNITY = json.loads((SITE / "data" / "community.json").read_text())
RCS = json.loads((SITE / "data" / "rcs.json").read_text())
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or next(
    (path for path in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if Path(path).exists()), None
)
pytestmark = pytest.mark.skipif(CHROME is None, reason="needs Chrome to render the pages")

FOOTER = "Contact: alejandrofuentepinero@gmail.com · Discord: alejandrofp92 · Ratings follow the MTG Elo Project · Also by me: 7PH Graph"
WIN_RATE_NOTE = "Win rate is wins over wins plus losses, a Bye counted as a win; draws count in W-L-D but not in the rate."


@pytest.fixture(scope="module")
def rendered():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=SITE, **kwargs)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    @functools.cache
    def dom(page: str) -> str:
        url = f"http://127.0.0.1:{server.server_port}/{page}"
        args = [CHROME, "--headless=new", "--disable-gpu", "--window-size=1500,1000", "--virtual-time-budget=10000", "--dump-dom", url]
        return subprocess.run(args, capture_output=True, text=True, timeout=60, check=True).stdout

    yield dom
    server.shutdown()


def text(dom: str) -> str:
    """What a reader sees: the DOM without scripts and tags, its whitespace collapsed."""
    dom = re.sub(r"<(script|style)\b.*?</\1>", " ", dom, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", dom))).strip()


def section(dom: str, id_: str) -> str:
    """One of the page's sections, by its id."""
    return re.search(rf'<section[^>]*id="{id_}".*?</section>', dom, flags=re.S).group(0)


def headers(dom: str, table: str) -> list[str]:
    """The column headings of the table whose opening tag carries `table`."""
    head = re.search(rf"<table[^>]*{table}.*?</thead>", dom, flags=re.S).group(0)
    return [text(cell) for cell in re.findall(r"<th\b.*?</th>", head, flags=re.S)]


PAGES = {"index.html": "Overview", "leaderboard.html": "Leaderboard", "player.html#alejandrofp": None}


@pytest.mark.parametrize("page", PAGES)
def test_every_page_links_its_stylesheet_and_font_and_carries_the_header_and_footer(rendered, page):
    dom = rendered(page)

    assert 'href="site.css"' in dom
    assert "fonts.googleapis.com/css2?family=Inter" in dom
    assert "prototype" not in dom
    header = text(re.search(r"<header.*?</header>", dom, flags=re.S).group(0))
    assert header.startswith("ANZ Regional Championships Overview Leaderboard")
    current = re.findall(r'<a [^>]*aria-current="page"[^>]*>([^<]*)</a>', dom)
    assert current == ([PAGES[page]] if PAGES[page] else [])
    footer = re.search(r"<footer.*?</footer>", dom, flags=re.S).group(0)
    assert text(footer) == FOOTER
    assert 'href="mailto:alejandrofuentepinero@gmail.com"' in footer
    assert 'href="https://mtgeloproject.net/"' in footer
    assert 'href="https://www.7phgraph.com/"' in footer


def rows(dom: str, body: str) -> list[str]:
    """The text of each row of the table body with id `body`."""
    tbody = re.search(rf'<tbody id="{body}">.*?</tbody>', dom, flags=re.S).group(0)
    return [text(row) for row in re.findall(r"<tr\b.*?</tr>", tbody, flags=re.S)]


def test_the_overview_reads_its_four_tables_to_the_pick_with_no_plots(rendered):
    dom = rendered("index.html")
    seen = text(dom)

    assert re.findall(r"<h2>([^<]*)</h2>", dom) == ["RC history", "What it takes to make Top 8", "Top 8 rate by Experience", "Played every RC"]
    assert re.findall(r"<button[^>]*>([^<]*)</button>", dom) == ["All", "Pioneer", "Standard", "Modern"]
    assert "plotly" not in dom and 'class="plot"' not in dom
    assert "Global" not in seen
    assert "Cycle" not in seen.replace("RC Cycle", "")

    assert headers(dom, 'id="rc-history"') == ["RC Cycle", "City and year", "Format", "Winner", "Runner-up", "Field Size", "Field by Experience"]
    assert text(re.search(r'<p class="legend"[^>]*>.*?</p>', dom, flags=re.S).group(0)) == (
        "At their 1st RC At their 2nd-3rd RC At their 4th-7th RC At their 8th+ RC")
    history = rows(dom, "rcs")
    assert len(history) == len(RCS)
    assert history[0].startswith("1 Sydney 2022 Pioneer ")
    # Field Size: the number, its bar to scale with the largest RC's filling the column.
    biggest = max(rc["field_size"] for rc in RCS)
    assert re.search(rf'<span>{biggest}</span><i style="width: 100%;">', dom)
    # Each colour of a field's bar names itself under the pointer, from the bundle.
    last = COMMUNITY["field_by_experience"][-1]
    assert f'data-tip="At their 2nd-3rd RC: {last["players"][1]} Players ({last["shares"][1]:g}%)"' in dom

    assert headers(dom, 'id="top-8-records"') == ["RC Cycle", "Swiss rounds", "Best record", "Worst record in", "Made it on that record"]
    records = rows(dom, "records")
    assert len(records) == len(RCS)
    assert records[0] == "1 8 7-0-1 6-1-1 5 of 5"
    assert records[-1] == "13 9 7-0-2 7-2-0 1 of 12"
    assert ("Swiss records, a Bye counted as a win. Across the 8-round RCs, 6-1-1 made Top 8 48 times out of 69 and "
            "6-2-0 never did.") in seen

    assert headers(dom, 'id="experience-rates"') == ["RCs played", "Players", "Top 8s", "Top 8 rate", "Against a first RC"]
    rates = rows(dom, "top-8-rate")
    assert [row.split()[0] for row in rates] == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10+"]
    assert rates[0] == "1 755 14 1.9% ×1.0"
    assert "RC Cycle 1 left out: everyone there was at their first RC." in seen
    assert "The 10+ row counts a Player once for each RC from their 10th." in seen

    assert headers(dom, 'id="every-rc"') == ["Player", "ANZ Rank", "Rating", "W-L-D", "Win rate", "Top 8s", "Best Finish"]
    every = rows(dom, "every-rc-rows")
    assert len(every) == 10
    assert every[0] == "Brennan Crawford 4 1828 70-34-4 67.3% 4 Winner"
    assert '<span class="whole">70-34-4</span>' in dom


def test_every_table_row_on_the_site_tints_under_the_pointer_from_one_rule_in_the_stylesheet():
    css = (SITE / "site.css").read_text()

    # Any table's body rows, bar the row that holds a card row's open rounds (its own rows tint).
    assert re.search(r"^:where\(tbody tr:not\(\.rounds\)\):hover > td \{ background: var\(--hover\); \}", css, flags=re.M)
    assert "tr.rc:hover > td" not in css
    for page in SITE.glob("*.html"):
        assert "<style" not in page.read_text(), page.name


def test_the_leaderboard_says_how_many_players_are_ranked_in_its_view(rendered):
    everyone, standard = rendered("leaderboard.html"), rendered("leaderboard.html#Standard")

    ranked = f"{BUNDLE['Global']['ranked']} Players are ranked in All."
    assert f"You must have played at least 3 RCs to be ranked, and 3 in a Format to be ranked in it. {ranked}" in text(everyone)
    assert f"{BUNDLE['Standard']['ranked']} Players are ranked in Standard." in text(standard)
    assert re.findall(r'<div class="formats"[^>]*>(.*?)</div>', everyone, flags=re.S)[0].count("Global") == 0
    # The top row as the bundle holds it, its whole Ratings shown as they are.
    top = BUNDLE["Global"]["players"][0]
    first = text(re.search(r'<tbody id="rows">\s*<tr>.*?</tr>', everyone, flags=re.S).group(0))
    assert first.startswith(f"1 {top['name']} {top['rating']} {top['peak']} {top['record']} ")
    assert f'<span class="whole">{top["record"]}</span>' in everyone


def test_the_player_card_heads_its_name_with_the_anz_rank_and_reads_its_tables_to_the_pick(rendered):
    dom = rendered("player.html#alejandrofp")
    seen = text(dom)

    card = json.loads((SITE / "data" / "players" / "alejandrofp.json").read_text())
    every = card["summary"]["Global"]

    assert text(re.search(r'<h1 id="name">.*?</h1>', dom, flags=re.S).group(0)) == f"Alejandro de la Fuente (#{every['rank']})"
    assert headers(dom, 'id="card-summary"')[-1] == "Typically finishes top"
    summary = re.search(r'<tbody id="summary">.*?</tbody>', dom, flags=re.S).group(0)
    rows = [text(row) for row in re.findall(r"<tr\b.*?</tr>", summary, flags=re.S)]
    assert [row.split()[0] for row in rows] == ["All", "Pioneer", "Standard", "Modern"]
    # The Typical Finish read from the top: finishing above 85.2% of the field is finishing in its top 14.8%.
    top = f"{100 - every['typical_finish_above']:.1f}".removesuffix(".0")
    assert rows[0].startswith(f"All {every['rank']} {every['rcs']} ")
    assert rows[0].endswith(f"{every['record']} {every['win_rate']['rate']:g}% {every['top_8s']} {every['finals']} {every['best_finish']} {top}%")
    assert headers(dom, 'id="rc-history"') == ["RC Cycle", "City and year", "Format", "Finish", "Deck", "W-L-D", "Win rate", "Rating"]
    history = re.search(r'<tbody id="rcs">.*?</tbody>', dom, flags=re.S).group(0)
    assert re.search(r"<td[^>]*>1500 → \d+</td>", history)  # the first RC starts at 1500
    assert WIN_RATE_NOTE in text(section(dom, "summary-panel"))
    assert WIN_RATE_NOTE in text(section(dom, "history-panel"))
    assert f'<span class="whole">{every["record"]}</span>' in dom


def test_a_player_below_the_cutoff_reads_not_ranked(rendered):
    dom = rendered("player.html#nkt")

    assert text(re.search(r'<h1 id="name">.*?</h1>', dom, flags=re.S).group(0)) == "Logan Boyd (Not ranked)"


def test_compare_players_heads_each_match_table_against_its_player_with_the_record_or_never_met(rendered):
    # James Drake drew Christopher Tong intentionally in Round 8 of Cycle 10 and beat him in its Final; he never met
    # Logan Boyd.
    dom = rendered("player.html#jamesdrake/christong0203/nkt")
    compare = section(dom, "compare-panel")
    against = re.search(r'<div class="matches" id="against">.*', compare, flags=re.S).group(0)
    seen = text(against)

    assert [text(h) for h in re.findall(r"<h3\b.*?</h3>", against, flags=re.S)] == [
        "Against Christopher Tong 1-0-1", "Against Logan Boyd Never met"]
    assert headers(against, "") == ["RC Cycle", "Format", "Round", "James Drake's deck", "Christopher Tong's deck", "Result"]
    assert "10 Modern 8 Ruby Storm Esper Goryo's Vengeance ID (0-0-3)" in seen
    assert "10 Modern Final Ruby Storm Esper Goryo's Vengeance Won (reconstructed)" in seen
    assert "playoff" not in seen
    assert "Each row's W-L-D against each column" not in text(dom)  # no matrix
    assert headers(compare, 'id="compared-summary-table"')[0] == "Player"
    assert WIN_RATE_NOTE in text(compare)
