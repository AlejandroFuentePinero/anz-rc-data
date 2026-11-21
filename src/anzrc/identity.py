"""Player identity: which Melee accounts are one Player, and the Display Name the site shows for them."""

import re
import tomllib
from collections import defaultdict
from pathlib import Path


def load_curation(path: Path) -> dict:
    """The owner's rulings: account joins beyond the rule, Display Name overrides by username, and 0-0-3s that are
    Intentional Draws beyond the build's rule."""
    curation = tomllib.loads(Path(path).read_text())
    return {
        "joins": curation.get("joins", []),
        "display_names": curation.get("display_names", {}),
        "intentional_draws": curation.get("intentional_draws", []),
    }


def _normalised(name: str) -> str:
    return " ".join(name.casefold().split())


def _twice(group: list[str], accounts: dict[str, dict]) -> list[int]:
    """The Cycles in which more than one of these accounts played."""
    cycles = [cycle for username in group for cycle in accounts[username]["cycles"]]
    return sorted({cycle for cycle in cycles if cycles.count(cycle) > 1})


def players(accounts: dict[str, dict], curation: dict) -> dict[str, dict]:
    """Every username's Player, from accounts as username to {"display_name", "cycles" (in order)}.

    Accounts showing the same normalised real name that never share an RC are one Player; any other join comes
    from the curation file. A Player can never appear twice in one RC, so a join that would make one is refused.
    """
    named = {username for group in curation["joins"] for username in group} | set(curation["display_names"])
    unknown = sorted(named - set(accounts))
    if unknown:
        raise ValueError(f"The curation file names usernames no RC has: {', '.join(unknown)}")

    parent = {username: username for username in accounts}

    def root(username: str) -> str:
        while parent[username] != username:
            username = parent[username]
        return username

    def join(group: list[str]) -> None:
        for username in group[1:]:
            parent[root(username)] = root(group[0])

    by_real_name = defaultdict(list)
    for username, account in accounts.items():
        if account["display_name"] != username:  # Melee shows the username when a Player hides their real name
            by_real_name[_normalised(account["display_name"])].append(username)
    for group in by_real_name.values():
        if len(group) > 1 and not _twice(group, accounts):
            join(group)
    for group in curation["joins"]:
        join(group)

    groups = defaultdict(list)
    for username in accounts:
        groups[root(username)].append(username)

    resolved, slugs = {}, set()
    for group in groups.values():
        group.sort(key=lambda username: accounts[username]["cycles"][0])
        twice = _twice(group, accounts)
        if twice:
            raise ValueError(
                f"Joining {', '.join(group)} would put one Player twice in Cycle {', '.join(map(str, twice))}: "
                "remove that join from the curation file"
            )
        overrides = [curation["display_names"][username] for username in group if username in curation["display_names"]]
        latest = max(group, key=lambda username: accounts[username]["cycles"][-1])
        player = {
            # The earliest account names the Player's URL, so a later account never moves it.
            "slug": re.sub(r"[^a-z0-9_]+", "-", group[0].lower()).strip("-"),
            # Override, else the latest account's real name, else its username (Melee shows it when the name is hidden).
            "name": overrides[0] if overrides else accounts[latest]["display_name"],
            "usernames": group,
        }
        if player["slug"] in slugs:
            raise ValueError(f"Two Players share the slug {player['slug']}")
        slugs.add(player["slug"])
        for username in group:
            resolved[username] = player
    return resolved
