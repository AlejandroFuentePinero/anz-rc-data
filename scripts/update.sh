#!/bin/sh
# Bring the site up to date with data/rcs.csv (issue #13): run after adding a new RC's row.
#
# Usage: scripts/update.sh
#
# Fetches from Melee what is not stored yet (the RCs already in data/raw are read from disk, not
# fetched again), brings the MTG Elo Project's record up to the same RCs when it lacks one,
# rebuilds the whole bundle from Cycle 1, and runs the tests. It commits and deploys nothing:
# what it changed is listed at the end, to be read, committed, and deployed with
# scripts/deploy_space.sh.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "== Melee"
uv run anzrc-fetch

# The tests compare every Match the site rates with the MTG Elo Project's record of it, so that
# record has to hold every RC on the list. Its crawl skips anyone already stored, and a stored
# person's file predates the new RC, so it is fetched again whole, into a folder of its own, and
# put in place only once complete. About a thousand requests at 1.5 seconds: some 25 minutes.
missing() {
    uv run python -c '
import json
from anzrc import mtgelo, rcs
held = set(json.loads((mtgelo.ORACLE / "events.json").read_text()).values())
print(*sorted(rc["cycle"] for rc in rcs.load() if rc["melee_id"] not in held))
'
}
LACKING=$(missing)
if [ -n "$LACKING" ]; then
    echo "== MTG Elo Project: its stored record lacks Cycle(s) $LACKING, so it is fetched again whole"
    FRESH=$(mktemp -d)
    trap 'rm -rf "$FRESH"' EXIT
    FRESH="$FRESH" uv run python -c '
import os
from pathlib import Path
from anzrc import mtgelo, rcs
from anzrc.fetch import Melee
mtgelo.crawl({rc["melee_id"] for rc in rcs.load()}, Path(os.environ["FRESH"]), Melee())
'
    rm -rf data/mtgeloproject
    cp -R "$FRESH" data/mtgeloproject
    LACKING=$(missing)
    if [ -n "$LACKING" ]; then
        echo "The MTG Elo Project does not list Cycle(s) $LACKING yet. Its record is updated for the rest;" >&2
        echo "re-run once it lists them. Nothing has been built." >&2
        exit 1
    fi
fi

echo "== Build"
uv run anzrc-build

echo "== Tests"
TESTS=0
uv run pytest -q || TESTS=$?

echo "== Changed"
git status --short -- data site
if [ "$TESTS" -ne 0 ]; then
    echo "The tests failed, above. Nothing should be committed or deployed until each is accounted for." >&2
    exit 1
fi
