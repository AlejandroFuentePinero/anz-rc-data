"""The server the Space runs (issue #13): the site exactly as built, with its own record of use in front."""

import contextlib
import json
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from anzrc import usage

SITE = Path("site")
PORT = 7860  # the port a Docker Space is reached on unless its README says otherwise


class CheckBack:
    """Tell browsers to check every file with the server before using a copy they kept. A copy
    used without asking is a load the record never sees, and data left stale after a deploy;
    checking costs a 304 with no body."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def marked(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((b"cache-control", b"no-cache"))
            await send(message)

        await self.app(scope, receive, marked if scope["type"] == "http" else send)


def create_app(site: Path, usage_dir: str | os.PathLike | None) -> Starlette:
    """The site at ``site``, recording its use into ``usage_dir`` when that names a folder."""
    middleware = [Middleware(CheckBack)]
    recorder = None
    if usage_dir:
        if Path(usage_dir).is_dir():
            players = frozenset(p["slug"] for p in json.loads((Path(site) / "data" / "players.json").read_text()))
            recorder = usage.Recorder(Path(usage_dir), players=players)
            # Written at the first flush whether or not anyone visits: proof the folder takes a
            # file, and a mark of each restart.
            recorder.note({"t": usage._now(), "kind": "start"})
            middleware.insert(0, Middleware(usage.RecordVisits, recorder=recorder))
        else:
            print(f"\n*** USAGE RECORD OFF: {usage.FOLDER_VARIABLE} names {usage_dir}, which is not a folder here. "
                  "The site is unaffected; visits are not being recorded. ***\n", flush=True)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        yield
        # The Space stopping writes what was noted since the last batch.
        if recorder:
            recorder.close()

    app = Starlette(middleware=middleware, lifespan=lifespan)
    app.mount("/", StaticFiles(directory=site, html=True))
    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(SITE, os.environ.get(usage.FOLDER_VARIABLE)), host="0.0.0.0", port=PORT)
