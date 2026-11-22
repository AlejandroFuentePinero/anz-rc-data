"""The site's own record of its use (issue #14, ported from mtgo-insights' recorder, itself 7ph-graph's).

Nothing else counts visits to the site: the Hub's visit count has no API and no dates, the
domain's DNS record is not proxied, and the Space's run log holds no requests. So the server
notes its own. It sees three things: a page served, a page load whose script ran (every page's
script asks for the Player list, `data/players.json`, and nothing else does), and a Player's
data loaded. The Player a page shows is in its address after `#`, which never reaches a server,
so a Player is known only by the page asking for its file: opening a Player and comparing
against one both load it.

Three rules decide the shape of everything here, the same three as the other apps'.

**A visitor is never affected.** The listener reads requests and touches no response. A note
is put on a queue and the request goes on; a full queue drops the note. Writing happens on
another thread, and a folder that cannot be written costs notes, never a request.

**Nothing that tells one visitor from another is kept.** No address, no cookie, no browser
string. A Player is kept only when the slug is one of the site's own Players (the owner's
ruling: Players' results are public, and nothing ties a load to a visitor). So the record
counts visits, not people.

**Each batch is a new file.** The folder is a Storage Bucket mounted into the Space, which is
object storage: a file written once and closed is what it is built for. A batch not yet
written when the Space stops is lost, at most ``FLUSH_SECONDS`` of notes.

The lines are the other apps' lines, field for field (version 1), so control-room's reader
reads this bucket as it reads theirs. The record is off unless ``ANZRC_USAGE_DIR`` names a
folder that exists, which is true on the Space and nowhere else.
"""

import argparse
import json
import queue
import re
import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

FOLDER_VARIABLE = "ANZRC_USAGE_DIR"

# What a redeploy can cost: the notes of the last five minutes.
FLUSH_SECONDS = 300

QUEUE_SIZE = 10_000

PAGES = {"/": "overview", "/index.html": "overview", "/leaderboard.html": "leaderboard", "/player.html": "player"}
BROWSER = "/data/players.json"
PLAYER = re.compile(r"/data/players/([^/]+)\.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Recorder:
    """Takes notes from the listener and writes them out, a batch at a time."""

    def __init__(self, folder: Path, *, players: frozenset[str]) -> None:
        self.folder = Path(folder)
        self.players = players
        # Which start of the server wrote a line: the gaps between runs are restarts.
        self.run = uuid.uuid4().hex[:8]
        self._notes: queue.Queue[dict] = queue.Queue(maxsize=QUEUE_SIZE)
        self._dropped = 0
        self._counting = threading.Lock()
        self._unwritten: list[str] = []
        self._files = 0
        self._failing = False
        self._flushing = threading.Lock()
        self._stop = threading.Event()
        self._writer = threading.Thread(target=self._write_on_time, daemon=True)
        self._writer.start()

    def note(self, event: dict) -> None:
        """On the request's own path, so it neither waits nor raises."""
        try:
            self._notes.put_nowait(event)
        except queue.Full:
            with self._counting:
                self._dropped += 1

    def flush(self) -> None:
        """Write what has been noted as one new file.

        Never raises. It runs on the writer's thread, where an error would end the record with
        nothing said, so a failure of any kind is said once, loudly, in the run log. Lines
        already made are kept for the next attempt.
        """
        with self._flushing:
            try:
                self._take_notes()
                if not self._unwritten:
                    return
                now = datetime.now(timezone.utc)
                path = self.folder / f"{now:%Y/%m/%d}" / f"{now:%H%M%S}-{self.run}-{self._files:06d}.jsonl"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("".join(line + "\n" for line in self._unwritten))
            except Exception as error:  # noqa: BLE001
                if not self._failing:
                    print(f"\n*** USAGE RECORD NOT WRITTEN to {self.folder}: {error!r}. "
                          "The site is unaffected; visits are not being recorded. ***\n", flush=True)
                self._failing = True
                # Held for the next attempt, up to twice what the queue holds.
                del self._unwritten[: -2 * QUEUE_SIZE]
                return
            self._failing = False
            self._files += 1
            self._unwritten = []

    def close(self) -> None:
        self._stop.set()
        self.flush()

    def _write_on_time(self) -> None:
        while not self._stop.wait(FLUSH_SECONDS):
            self.flush()

    def _take_notes(self) -> None:
        while True:
            try:
                note = self._notes.get_nowait()
            except queue.Empty:
                break
            self._unwritten.append(json.dumps({"v": 1, "run": self.run, **note}))
        with self._counting:
            dropped, self._dropped = self._dropped, 0
        if dropped:
            self._unwritten.append(json.dumps({"v": 1, "run": self.run, "t": _now(), "kind": "dropped", "n": dropped}))


class RecordVisits:
    """Note each page served, each browser load and each Player loaded, and pass everything through."""

    def __init__(self, app: ASGIApp, recorder: Recorder) -> None:
        self.app = app
        self.recorder = recorder
        self._named = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return
        # Three kinds of request are read. Every other one, the stylesheet and scripts of a
        # page load among them, costs these comparisons and nothing more.
        path, headers = scope["path"], _headers(scope)
        if page := PAGES.get(path):
            note = {**_seen(headers), "kind": "page", "page": page, "ref": _site(headers.get("referer")),
                    "dest": headers.get("sec-fetch-dest")}
            if not self._named:
                # Once per run, the names of the headers that reached the app: what the Hub's
                # proxy passes on cannot be seen from outside.
                note["names"] = sorted(headers)
                self._named = True
            self.recorder.note(note)
        elif path == BROWSER:
            self.recorder.note({**_seen(headers), "kind": "browser"})
        elif (found := PLAYER.fullmatch(path)) and found[1] in self.recorder.players:
            await self._answered(scope, receive, send, {**_seen(headers), "kind": "read", "view": found[1]})
            return
        await self.app(scope, receive, send)

    async def _answered(self, scope: Scope, receive: Receive, send: Send, note: dict) -> None:
        """Note a Player's file only once it is served: whole (200), or confirmed to the
        browser's own copy (304), since the site tells browsers to check back each time."""
        answered: dict[str, int] = {}

        async def watching(message: Message) -> None:
            if message["type"] == "http.response.start":
                answered["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, watching)
        finally:
            if answered.get("status") in (200, 304):
                self.recorder.note(note)


def _headers(scope: Scope) -> dict[str, str]:
    return {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}


def _seen(headers: dict[str, str]) -> dict:
    return {"t": _now(), "host": headers.get("host")}


def _site(referer: str | None) -> str | None:
    """The site a visitor came from: never the page on it, nor a query string."""
    if not referer:
        return None
    try:
        return urlsplit(referer).netloc or None
    except ValueError:
        return None


_COLUMNS = ("Pages", "Browser loads", "Player loads")

_LEGEND = """\
Pages: every time a page was served. Browser loads: page loads whose script ran, the count
control-room shows. Player loads: Players' data loaded, by opening a Player or comparing
against one."""


def _listing(title: str, counts: Counter) -> str:
    wide = max(len(label) for label in counts)
    rows = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    return "\n".join([title, *(f"  {label:<{wide}}  {n:>5}" for label, n in rows)])


def report(folder: Path, site: Path, *, by: str) -> str:
    """What a copy of the recorded folder says, counted by day or by week. Players are named by
    their Display Name in the site at ``site``."""
    lines = sorted(
        (json.loads(line) for path in Path(folder).rglob("*.jsonl") for line in path.read_text().splitlines()),
        key=lambda line: line["t"],
    )
    events = [line for line in lines if line["kind"] in ("page", "browser", "read")]
    if not events:
        return f"No usage recorded under {folder}.\n"

    def period(line: dict) -> str:
        day = datetime.fromisoformat(line["t"]).date()
        return str(day - timedelta(days=day.weekday()) if by == "week" else day)

    head = "Week of" if by == "week" else "Day"
    table = [f"{head:<10}  " + "  ".join(_COLUMNS)]
    counted = Counter((period(line), line["kind"]) for line in events)
    for when in sorted({period(line) for line in events}):
        figures = (counted[when, "page"], counted[when, "browser"], counted[when, "read"])
        table.append(f"{when}  " + "  ".join(f"{n:>{len(column)}}" for n, column in zip(figures, _COLUMNS)))

    names = {p["slug"]: p["name"] for p in json.loads((Path(site) / "data" / "players.json").read_text())}
    pages = [line for line in events if line["kind"] == "page"]
    listings = [
        ("Page", Counter(line["page"] for line in pages)),
        ("Came from", Counter(line["ref"] or "(not said)" for line in pages)),
        ("Player", Counter(names.get(line["view"], line["view"]) for line in events if line["kind"] == "read")),
    ]
    first, final = (datetime.fromisoformat(events[i]["t"]).date() for i in (0, -1))
    parts = [f"Usage by {by} (UTC), {first} to {final}", "\n".join(table), _LEGEND,
             *(_listing(title, counts) for title, counts in listings if counts)]
    dropped = sum(line["n"] for line in lines if line["kind"] == "dropped")
    if dropped:
        parts.append(f"RECORDER DROPPED {dropped} NOTES: the queue was full, so these counts are short.")
    return "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Report on a local copy of the folder the site records its use in.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--by", choices=("day", "week"), default="week")
    args = parser.parse_args(argv)
    print(report(args.folder, Path("site"), by=args.by), end="")
