#!/bin/sh
# Deploy the site and its small server to the Hugging Face Space (issue #13).
#
# Usage: scripts/deploy_space.sh [<user>/<space>]    (default Alejandrofupi/anz-rc-data)
#
# Modelled on 7ph-graph's scripts/deploy_space.sh. What ships is staged in a folder of its own
# and uploaded as one commit, so the Space restarts once and only the files copied below can go
# up. The upload is not the end: the script waits for the Space to run what it was sent, then
# loads every page in a browser and compares it with site/ (scripts/check_live.py).
#
# Creating the Space is not this script's job: the owner creates it in the Hub's new-space form
# (the Hub refuses to create a Gradio Space through its API). The usage bucket and variable live
# on the Space too; docs/deploy.md says what they are.
set -eu

SPACE="${1:-Alejandrofupi/anz-rc-data}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# What ships has to be what a commit holds, since several sessions can edit this checkout at
# once. Untracked files count: a new file under site/ or src/ would be copied up with the rest.
UNCOMMITTED=$(cd "$ROOT" && git status --porcelain -- app.py src/anzrc site deploy pyproject.toml uv.lock)
if [ -n "$UNCOMMITTED" ]; then
    echo "Refusing to deploy: what ships has changes no commit holds:" >&2
    printf '%s\n' "$UNCOMMITTED" | sed 's/^/  /' >&2
    exit 1
fi
COMMIT=$(cd "$ROOT" && git rev-parse HEAD)

# The Hub API, not the `hf upload` CLI, which tries to create the repo first.
hf_python() { uvx --from huggingface_hub python -c "$1"; }

STAGE=$(mktemp -d)
SPACE_INSTALL=$(mktemp)
trap 'rm -rf "$STAGE" "$SPACE_INSTALL"' EXIT

# The Space card becomes the Space's README; the repo's README stays a GitHub page.
cp "$ROOT/deploy/README.md" "$STAGE/README.md"
cp "$ROOT/app.py" "$STAGE/"
# The package sits beside app.py, not under src/: a Space installs requirements.txt before the
# repo exists, so it cannot install this project, and app.py's folder is on the import path.
cp -R "$ROOT/src/anzrc" "$STAGE/anzrc"
find "$STAGE/anzrc" -name __pycache__ -type d -exec rm -rf {} +
cp -R "$ROOT/site" "$STAGE/site"

# The runtime half of uv.lock, every package pinned, so the Space runs what the suite ran.
if ! (cd "$ROOT" && uv export --quiet --locked --no-dev --no-emit-project --no-hashes) > "$STAGE/requirements.txt"; then
    echo "Refusing to deploy: uv.lock does not match pyproject.toml. Run 'uv lock', test, commit." >&2
    exit 1
fi
# A Gradio Space installs that file together with its own line, and refuses the lot when they
# disagree, after the upload. Resolved here first for the card's Python on Linux, so the same
# disagreement stops the deploy with the Space as it was. The line is the one 7ph-graph's and
# mtgo-insights' deploys copy from a Gradio Space's build log.
CARD="$ROOT/deploy/README.md"
SDK=$(sed -n 's/^sdk_version: *//p' "$CARD")
PYTHON=$(sed -n 's/^python_version: *"\(.*\)"$/\1/p' "$CARD")
printf '%s\n' "gradio[oauth,mcp]==$SDK" "uvicorn>=0.14.0" "websockets>=10.4" spaces > "$SPACE_INSTALL"
if ! uv pip compile --quiet --python-version "$PYTHON" --python-platform x86_64-unknown-linux-gnu \
    "$STAGE/requirements.txt" "$SPACE_INSTALL" > /dev/null; then
    echo "Refusing to deploy: the Space could not install these packages, above. Nothing on it was touched." >&2
    exit 1
fi

if ! SPACE="$SPACE" hf_python '
import os, sys
from huggingface_hub import repo_exists
sys.exit(0 if repo_exists(os.environ["SPACE"], repo_type="space") else 1)
' 2>/dev/null; then
    echo "No Space at $SPACE. The owner creates it at https://huggingface.co/new-space (Gradio, CPU Basic)." >&2
    exit 1
fi

# One commit; `delete_patterns` clears what a previous deploy left behind.
STAGE="$STAGE" SPACE="$SPACE" COMMIT="$COMMIT" hf_python '
import os
from huggingface_hub import HfApi
print(HfApi().upload_folder(folder_path=os.environ["STAGE"], repo_id=os.environ["SPACE"], repo_type="space",
                            delete_patterns="*", commit_message="Deploy " + os.environ["COMMIT"]))
'

not_live() {
    {
        echo
        echo "################################################################"
        echo "#  THE UPLOAD WENT UP AND THE SITE IS NOT RIGHT"
        echo "################################################################"
        echo "$1"
        echo "Logs: https://huggingface.co/spaces/$SPACE?logs=container"
        echo "################################################################"
    } >&2
    exit 1
}

# Wait until the Space runs the commit just made, then read the addresses it answers at: the
# custom domain where there is one, since that is the address visitors use.
echo "Uploaded. Waiting for the Space to run it." >&2
if ! ADDRESSES=$(SPACE="$SPACE" hf_python '
import os, sys, time
from huggingface_hub import HfApi
deadline = time.monotonic() + 15 * 60
while True:
    space = HfApi().space_info(os.environ["SPACE"])
    runtime = space.runtime.raw
    if runtime["stage"] == "RUNNING" and runtime.get("sha") == space.sha:
        break
    if runtime["stage"].endswith("ERROR"):
        print("The Space stopped at " + runtime["stage"] + ".")
        sys.exit(1)
    if time.monotonic() > deadline:
        print("The Space was still at " + runtime["stage"] + " after 15 minutes.")
        sys.exit(1)
    print("  " + runtime["stage"], file=sys.stderr)
    time.sleep(15)
names = [domain["domain"] for domain in runtime["domains"]]
published = [name for name in names if not name.endswith(".hf.space")] or names
print(*("https://" + name + "/" for name in published))
'); then
    not_live "$ADDRESSES"
fi

# shellcheck disable=SC2086
if ! SEEN=$(cd "$ROOT" && uv run python scripts/check_live.py $ADDRESSES); then
    not_live "${SEEN:-The pages could not be checked, for the reason above.}"
fi
echo "$SEEN"
echo "Deployed $COMMIT to https://huggingface.co/spaces/$SPACE"
