"""Reading Melee's response shapes, shared by the fetcher and the build."""

import re

# An RC's Melee page lists every round twice (over standings and over pairings), in play order.
ROUND_RE = re.compile(r'class="btn btn-gray round-selector" data-id="(\d+)"')


def round_ids(page: str) -> list[str]:
    """The RC's round IDs in play order, read from its Melee page."""
    return list(dict.fromkeys(ROUND_RE.findall(page)))
