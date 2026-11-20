"""The RC list: one row per RC, in data/rcs.csv. Adding an RC is one row."""

import csv
from pathlib import Path

RC_LIST = Path("data/rcs.csv")
RAW = Path("data/raw")


def load(path: Path = RC_LIST) -> list[dict]:
    with open(path, newline="") as f:
        return [row | {"cycle": int(row["cycle"]), "melee_id": int(row["melee_id"])} for row in csv.DictReader(f)]
