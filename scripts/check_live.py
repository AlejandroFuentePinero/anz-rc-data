"""Load the deployed site in a headless browser and say whether every page is drawn as it is from site/.

Usage: check_live.py <address> [<address> ...]

What scripts/deploy_space.sh ends on (issues #13 and #14). A 200 is not the test: 7ph-graph's
custom domain once answered 200 with a page that could not fetch its data. So each page is
rendered by Chrome twice, once from the local site/ and once at the address, and the text a
reader sees has to be the same. A page that drew nothing, or drew it from other data, differs.

Each check is a visit to the site, so it lands in the usage record like any other.

Exits 0 when every address matches, 1 when one does not (saying where), and 2 when there is
no Chrome to look with.
"""

import functools
import html
import http.server
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

SITE = Path(__file__).parent.parent / "site"
# A Player's page reads its Player from the address, so it is checked on one Player.
PAGES = ("", "leaderboard.html", "player.html#alejandrofp", "stories.html")
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or next(
    (path for path in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if Path(path).exists()), None
)


def seen(url: str) -> str:
    """The text a reader sees at ``url`` once its scripts have run, whitespace collapsed."""
    # Long enough for a Space that has only just started to answer.
    args = [CHROME, "--headless=new", "--disable-gpu", "--window-size=1500,1000",
            "--virtual-time-budget=30000", "--dump-dom", url]
    dom = subprocess.run(args, capture_output=True, text=True, timeout=120, check=True).stdout
    dom = re.sub(r"<(script|style)\b.*?</\1>", " ", dom, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", dom))).strip()


def main(addresses: list[str]) -> int:
    if not addresses:
        print(__doc__, file=sys.stderr)
        return 2
    if CHROME is None:
        print("No Chrome to load the site with, so it is not checked.", file=sys.stderr)
        return 2

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=SITE, **kwargs)

        def log_message(self, *args):
            pass

    local = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=local.serve_forever, daemon=True).start()
    expected = functools.cache(lambda page: seen(f"http://127.0.0.1:{local.server_port}/{page}"))

    wrong = []
    for address in addresses:
        for page in PAGES:
            url = address.rstrip("/") + "/" + page
            try:
                live = seen(url)
            except subprocess.SubprocessError as error:
                wrong.append(f"{url} could not be loaded: {error}")
                continue
            if live != expected(page):
                wrong.append(f"{url} is not drawn as site/ draws it. It shows: {live[:300] or '(nothing)'}")
    local.shutdown()

    for line in wrong:
        print(line)
    if not wrong:
        print("Drawn as site/ draws it: " + ", ".join(address.rstrip("/") + "/" + p for address in addresses for p in PAGES))
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
