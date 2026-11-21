"""The measurements that set the Rating rules (ADR 0001): K, which Format Ratings ship, top-10 stability and the cutoff.

Analysis over the build's own replay of the real RCs, written to docs/measurements.md. Its results are set by hand
as constants in anzrc.ratings, and recorded in ADR 0001.
"""

import math
import random
import statistics
from pathlib import Path

from anzrc import rcs, ratings
from anzrc.build import CURATION, replayed

REPORT = Path("docs/measurements.md")
K_CANDIDATES = list(range(16, 65, 4))
BASELINE = math.log(2)  # the log loss of calling every Match 50-50
RESAMPLES, SEED = 1000, 2026
CUTOFFS = (2, 3, 4)
TOP = 10


def _log_loss(rating: float, opponent: float, score: float) -> float:
    p = ratings.expected(rating, opponent)
    return -(score * math.log(p) + (1 - score) * math.log(1 - p))


def _replay(history: list[dict], k: float) -> dict[str, float]:
    current: dict[str, float] = {}
    for rc in history:
        for rated in rc["rounds"]:
            ratings.play_round(current, rated, k)
    return current


def predictions(history: list[dict], k: float) -> dict[int, list[float]]:
    """The log loss of each Match from the second RC on, by Cycle, predicted from the Ratings at the RC's start,
    which only earlier RCs moved."""
    current: dict[str, float] = {}
    losses: dict[int, list[float]] = {}
    for index, rc in enumerate(history):
        if index:
            losses[rc["cycle"]] = [
                _log_loss(current.get(a, ratings.START), current.get(b, ratings.START), score)
                for rated in rc["rounds"]
                for a, b, score in rated
            ]
        for rated in rc["rounds"]:
            ratings.play_round(current, rated, k)
    return losses


def _flat(losses: dict[int, list[float]]) -> list[float]:
    return [loss for cycle_losses in losses.values() for loss in cycle_losses]


def _paired(differences: list[float]) -> tuple[float, float]:
    """Mean and standard error of per-Match differences."""
    return statistics.fmean(differences), statistics.stdev(differences) / math.sqrt(len(differences))


def measure_k(history: list[dict]) -> tuple[int, list[dict]]:
    """The K with the lowest mean log loss, kept only if it beats mtgeloproject's K by more than two standard errors
    of the paired per-Match difference; anything closer is a tie, and a tie keeps mtgeloproject's K."""
    losses = {k: _flat(predictions(history, k)) for k in K_CANDIDATES}
    rows = []
    for k, loss in losses.items():
        mean_diff, se = _paired([a - b for a, b in zip(loss, losses[ratings.K])])
        rows.append({"k": k, "log_loss": statistics.fmean(loss), "vs_default": mean_diff, "se": se, "matches": len(loss)})
    best = min(rows, key=lambda row: row["log_loss"])
    chosen = best["k"] if best["vs_default"] < -2 * best["se"] else ratings.K
    return chosen, rows


def measure_formats(history: list[dict], k: float) -> list[dict]:
    """Each Format's own Rating scored on its RCs after its first, against the 50-50 baseline, and beside it the
    Global Rating on the same Matches, both read at each RC's start."""
    global_losses = predictions(history, k)
    rows = []
    for format_ in ("Pioneer", "Standard", "Modern"):
        own = [rc for rc in history if rc["format"] == format_]
        own_losses = predictions(own, k)
        loss = _flat(own_losses)
        global_loss = [value for cycle in own_losses for value in global_losses[cycle]]
        vs_baseline, se = _paired([value - BASELINE for value in loss])
        vs_global, se_global = _paired([a - b for a, b in zip(loss, global_loss, strict=True)])
        rows.append(
            {
                "format": format_,
                "rcs": [rc["cycle"] for rc in own],
                "scored": list(own_losses),
                "matches": len(loss),
                "log_loss": statistics.fmean(loss),
                "vs_baseline": vs_baseline,
                "se": se,
                "global_log_loss": statistics.fmean(global_loss),
                "vs_global": vs_global,
                "se_global": se_global,
                "ships": statistics.fmean(loss) < BASELINE,
            }
        )
    return rows


def _rcs_played(history: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rc in history:
        for slug in rc["players"]:
            counts[slug] = counts.get(slug, 0) + 1
    return counts


def _ranked(current: dict[str, float], eligible: set[str]) -> list[str]:
    return sorted(eligible, key=lambda slug: -current.get(slug, ratings.START))


def measure_stability(history: list[dict], k: float) -> dict:
    """Resample each RC's rated Matches with replacement (each keeps its round), replay in order, and see how much of
    the observed top 10 stays in the top 10, at each cutoff; plus each top Player's 90% rank interval at each cutoff."""
    played = _rcs_played(history)
    observed = _replay(history, k)
    eligible = {cutoff: {slug for slug, n in played.items() if n >= cutoff} for cutoff in CUTOFFS}
    top = {cutoff: _ranked(observed, eligible[cutoff])[:TOP] for cutoff in CUTOFFS}
    kept = {cutoff: [] for cutoff in CUTOFFS}
    ranks = {cutoff: {slug: [] for slug in top[cutoff]} for cutoff in CUTOFFS}
    rng = random.Random(SEED)
    for _ in range(RESAMPLES):
        current: dict[str, float] = {}
        for rc in history:
            tagged = [(index, match) for index, rated in enumerate(rc["rounds"]) for match in rated]
            drawn = [rng.choice(tagged) for _ in tagged]
            by_round: list[list] = [[] for _ in rc["rounds"]]
            for index, match in drawn:
                by_round[index].append(match)
            for rated in by_round:
                ratings.play_round(current, rated, k)
        for cutoff in CUTOFFS:
            order = _ranked(current, eligible[cutoff])
            kept[cutoff].append(len(set(order[:TOP]) & set(top[cutoff])))
            position = {slug: rank for rank, slug in enumerate(order, start=1)}
            for slug in top[cutoff]:
                ranks[cutoff][slug].append(position[slug])

    def interval(values):
        values = sorted(values)
        return values[int(0.05 * len(values))], values[math.ceil(0.95 * len(values)) - 1]

    return {
        cutoff: {
            "leaderboard": len(eligible[cutoff]),
            "kept": statistics.fmean(kept[cutoff]),
            "top": [(slug, observed.get(slug, ratings.START), interval(ranks[cutoff][slug])) for slug in top[cutoff]],
        }
        for cutoff in CUTOFFS
    }


def report(history: list[dict], names: dict[str, str]) -> str:
    k, k_rows = measure_k(history)
    formats = measure_formats(history, k)
    stability = measure_stability(history, k)
    matches = sum(len(rated) for rc in history for rated in rc["rounds"])
    lines = [
        "# Measurements",
        "",
        "Written by `anzrc-measure` from the build's own replay of every RC "
        f"({len(history)} RCs, {matches} rated Matches). The constants in `anzrc.ratings` are set from it, "
        "and ADR 0001 records the numbers. Log loss is the mean of -(s ln p + (1 - s) ln(1 - p)) over Matches, where p is the "
        f"expected score and s the result (1, 0.5 or 0); calling every Match 50-50 scores ln 2 = {BASELINE:.4f}. Lower is better.",
        "",
        "## K",
        "",
        "Every Match from Cycle 2 on, predicted from the Ratings at the start of its RC (moved only by earlier RCs). "
        "A K other than 36 is kept only if it beats 36 by more than two standard errors of the paired per-Match difference; "
        "anything closer is a tie, and a tie keeps 36.",
        "",
        "| K | Log loss | Against K = 36 | Standard error |",
        "|---|---|---|---|",
    ]
    for row in k_rows:
        lines.append(f"| {row['k']} | {row['log_loss']:.5f} | {row['vs_default']:+.5f} | {row['se']:.5f} |")
    best = min(k_rows, key=lambda row: row["log_loss"])
    lines += [
        "",
        f"Scored on {k_rows[0]['matches']} Matches. Lowest log loss: K = {best['k']}. **K = {k}.**",
        "",
        "## Per-Format",
        "",
        f"Each Format's own Rating (K = {k}, every Player new at 1500 in it) predicts that Format's RCs after its first, "
        "from the Ratings at each RC's start. It ships if its log loss beats the 50-50 baseline. The Global Rating's log loss "
        "on the same Matches, also read at each RC's start, is shown beside it.",
        "",
        "| Format | RCs (Cycles) | Scored | Matches | Log loss | Against 50-50 (SE) | Global on the same Matches | Own against Global (SE) | Ships |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in formats:
        lines.append(
            f"| {row['format']} | {', '.join(map(str, row['rcs']))} | {', '.join(map(str, row['scored']))} | {row['matches']} | "
            f"{row['log_loss']:.5f} | {row['vs_baseline']:+.5f} ({row['se']:.5f}) | {row['global_log_loss']:.5f} | "
            f"{row['vs_global']:+.5f} ({row['se_global']:.5f}) | {'yes' if row['ships'] else 'no'} |"
        )
    lines += [
        "",
        "## Stability",
        "",
        f"{RESAMPLES} resamples (seed {SEED}) of each RC's rated Matches with replacement, each keeping its round, replayed in "
        f"order with K = {k}. The figure is the mean number of the observed Global top {TOP} still in a resample's top {TOP}. "
        "Eight or more drops \"Rank could be\"; fewer keeps it as each Player's 90% rank interval.",
        "",
        "| RCs needed | Leaderboard size | Top 10 kept |",
        "|---|---|---|",
    ]
    for cutoff, row in stability.items():
        lines.append(f"| {cutoff} | {row['leaderboard']} | {row['kept']:.2f} |")
    for cutoff, row in stability.items():
        lines += ["", f"Top {TOP} at {cutoff} RCs, with the 90% rank interval across resamples:", "", "| Rank | Player | Rating | 90% rank interval |", "|---|---|---|---|"]
        for rank, (slug, value, (low, high)) in enumerate(row["top"], start=1):
            lines.append(f"| {rank} | {names[slug]} | {value:.0f} | {low} to {high} |")
    lines += ["", "## Cutoff", "", "See the Stability table: Leaderboard size and top-10 stability at 2, 3 and 4 RCs.", ""]
    return "\n".join(lines)


def main() -> None:
    _, cards, history = replayed(rcs.RAW, rcs.RC_LIST, CURATION)
    names = {slug: card["name"] for slug, card in cards.items()}
    REPORT.write_text(report(history, names))
    print(REPORT.read_text())
