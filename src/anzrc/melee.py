"""Reading Melee's response shapes, shared by the fetcher and the build."""

import html
import re

# An RC's Melee page lists every round twice (over standings and over pairings), in play order.
ROUND_RE = re.compile(r'class="btn btn-gray round-selector" data-id="(\d+)"')


def round_ids(page: str) -> list[str]:
    """The RC's round IDs in play order, read from its Melee page."""
    return list(dict.fromkeys(ROUND_RE.findall(page)))


# A decklist page carries the list as plain text, one "<quantity> <card>" per line under each section header.
DECKLIST_TEXT_RE = re.compile(r'<pre class="d-none" id="decklist-text">(.*?)</pre>', re.S)
SECTIONS = {"MainDeck", "Companion", "Sideboard"}


def decklist(page: str) -> dict:
    """A decklist page's main deck, sideboard and companion.

    The companion is a sideboard card. Older lists show it under Companion and again under Sideboard
    (the 76 cards of Cycles 4 and 7); newer ones under Companion only. Either way it counts once in the sideboard.
    """
    found = DECKLIST_TEXT_RE.search(page)
    if not found:
        raise ValueError("no decklist text on the page")
    sections: dict[str, list[dict]] = {}
    for line in html.unescape(found.group(1)).splitlines():
        if line in SECTIONS:
            cards = sections.setdefault(line, [])
        elif line:
            quantity, name = line.split(" ", 1)
            cards.append({"quantity": int(quantity), "name": name})
    if not sections.get("MainDeck"):
        raise ValueError("no main deck in the decklist text")
    sideboard = sections.get("Sideboard", [])
    companion = sections["Companion"][0]["name"] if "Companion" in sections else None
    if companion and companion not in {card["name"] for card in sideboard}:
        sideboard = sideboard + [{"quantity": 1, "name": companion}]
    return {"main": sections["MainDeck"], "sideboard": sideboard, "companion": companion}
