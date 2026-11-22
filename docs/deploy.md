# Deploy

How the site reaches its Hugging Face Space, and what lives on the Space outside the repo.
The update after each new RC is #13's, and is added here with it.

## Deploying

```sh
scripts/deploy_space.sh
```

It refuses a checkout whose shipped files (`app.py`, `src/anzrc`, `site`, `deploy`, the
project and lock files) no commit holds, and a lock the Space could not install. Then it
uploads them as one commit, so the Space restarts once, waits for the Space to run it, and
ends on `scripts/check_live.py`: each page rendered in headless Chrome at the published
address and from `site/` must show the same text. A failure after the upload is printed
under `THE UPLOAD WENT UP AND THE SITE IS NOT RIGHT`. Each check is three visits in the
usage record.

## The Space

A Gradio Space (`sdk: gradio`, `cpu-basic`), as the owner's other apps are, but with no Gradio
UI: `app.py` starts the small server in `anzrc.serve`, which serves `site/` exactly as built,
on port 7860. The Space card, with the SDK and the Python version pinned, is
`deploy/README.md`, which becomes the Space's README.

Every file is served with `Cache-Control: no-cache`, so a browser checks back on every load
and is answered `304` when its copy is current. That keeps a deploy from leaving visitors on
stale data, and keeps a load from going uncounted.

## The address

The site is published at **https://www.anzrcdata.com**. The Space is `Alejandrofupi/anz-rc-data`,
protected, so the running site is public and the Space's files are not. Its own address,
https://alejandrofupi-anz-rc-data.hf.space, keeps answering too, with no setting to turn it off.

All of this is set by hand in Cloudflare (where anzrcdata.com is registered and its DNS served)
and in the Space's settings, none of it in the repo:

- **`www`**: a CNAME to `hf.space`, **DNS only** (grey cloud), and `www.anzrcdata.com` entered
  under the Space's Settings, "Custom domain". The Hub confirms the domain by that CNAME, so it
  must stay unproxied, and it must be a subdomain, since an apex cannot carry a CNAME.
- **The bare domain**: an A record `@` to `192.0.2.1`, **proxied** (orange cloud), which only
  gives Cloudflare a record to act on, and a Redirect Rule "Bare domain to www" from
  `https://anzrcdata.com/*` to `https://www.anzrcdata.com/${1}`, 301, query string kept.
- **Always Use HTTPS**, on (SSL/TLS, Edge Certificates). Without it `http://anzrcdata.com`
  answers Cloudflare's 522, because the redirect rule matches `https` only.

Checked 2026-11-22: `http://` and `https://`, bare and `www`, with a path and a query string,
all end on the same page at `https://www.anzrcdata.com`.

## The usage record

The Space records its own use (issue #14). Nothing else counts visits to it: the Hub's
Analytics panel has no dates and no API, and a DNS-only CNAME means Cloudflare sees nothing.
Nothing a visitor downloads is different for it: no script, no outside request, no cookie.

Two things on the Space make it record, both set by hand and neither in the repo:

- **A private Storage Bucket attached as a volume.** `Alejandrofupi/anz-rc-data-usage`,
  mounted read-write at `/usage`. A Space's own disk is wiped at every restart; the bucket is
  not part of the Space and outlives it. Attached with
  `hf spaces volumes set Alejandrofupi/anz-rc-data -v hf://buckets/Alejandrofupi/anz-rc-data-usage:/usage`
  (or in the new-space form, as it first was), which replaces any volumes already set, and listed with `hf spaces volumes ls Alejandrofupi/anz-rc-data`.
- **A variable naming the folder.** `ANZRC_USAGE_DIR=/usage`, a variable and not a secret,
  set with `hf spaces variables add Alejandrofupi/anz-rc-data -e ANZRC_USAGE_DIR=/usage` (or
  under the Space's Settings, "Variables and secrets"). With it unset, or naming a folder
  that is not there, the site records nothing and behaves exactly as it does otherwise: that
  is every local run and the suite.

The Space holds no credential for this. It writes files to a folder.

### What a line holds

One JSON object per line, in the same version-1 format as 7ph-graph's, mtgo-insights' and
arena-insights' records, so control-room reads it with the same reader. Every line has `v`,
`run` (which start of the server wrote it), `t` (UTC) and `kind`:

- `start`: one per start of the server, written at its first save whether or not anyone
  visits. A restart shows as a new `run`.
- `page`: a page served (`/`, `/index.html`, `/leaderboard.html`, `/player.html`). It holds
  which page, the address used (`host`: the custom domain or the Space's own), the site a
  visitor came from (`ref`, the host only, never the path or query) where the browser said,
  and what the browser fetched it as (`dest`, from `sec-fetch-dest`). The first `page` of each
  run also lists the names (never the values) of the headers that reached the server, since
  what the Hub's proxy passes on cannot be seen from outside.
- `browser`: a request for `data/players.json`, which every page's script asks for once it
  runs and a fetcher that runs no script never does. This is the page load control-room counts.
- `read`: a Player's data loaded (`view`, the Player's slug), by opening a Player or comparing
  against one, and only for a slug that is one of the site's own Players.
- `dropped`: how many notes were lost to a full queue, if any were.

What a line never holds: a visitor's address, a cookie, a browser string, what was typed in
search (that runs in the browser), or anything else that tells one visitor from another. The
record counts visits, not people.

### When it is written

Notes are saved every five minutes as one new file under `/usage/<year>/<month>/<day>/`, and
once more when the server stops. A file is never appended to. A restart that gives no warning
loses at most the last five minutes.

### In the run log

Neither of these stops the site:

- `*** USAGE RECORD OFF`: `ANZRC_USAGE_DIR` names a folder that is not there, most likely the
  volume is not attached. Nothing is recorded.
- `*** USAGE RECORD NOT WRITTEN`: the folder refused a write. Said once; notes are held for
  the next attempt.

### Reading it

Download a copy of the bucket and report on it:

```sh
hf buckets sync hf://buckets/Alejandrofupi/anz-rc-data-usage ./usage-copy
uv run anzrc-usage ./usage-copy --by day    # or --by week
```

The report gives Pages, Browser loads and Player loads per day or week, then which pages,
which sites visitors came from, and the Players loaded by Display Name. Control-room shows the
daily Browser loads only.
