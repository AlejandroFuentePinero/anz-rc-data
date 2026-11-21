"""The Rating rule, mtgeloproject's plain Elo (ADR 0001): everyone starts at 1500 and a Match moves both Ratings."""

import math

START = 1500
# mtgeloproject's K. Measured (docs/measurements.md): K = 40 scores best but only by a tie, so 36 stays.
K = 36
# mtgeloproject's scale: the divisor that makes a 200 point gap a 60% expectation, 200 / log10(1.5) = 1135.77.
SCALE = 200 / math.log10(1.5)
# The Formats whose own Rating ships; any other Format shows the Global Rating. Measured: all three beat 50-50.
FORMAT_RATINGS = {"Pioneer", "Standard", "Modern"}
# Measured: about 5 of the top 10 stay in the top 10 across resamples, so the Leaderboard shows "Rank could be".
RANK_COULD_BE = True
# RCs a Player needs in a view to be ranked in it. Measured: stability barely moves between 2, 3 and 4.
CUTOFF = 3


def rated_by(format_: str) -> str:
    """The view whose Ratings a Format shows: its own if they ship, else Global."""
    return format_ if format_ in FORMAT_RATINGS else "Global"


def expected(rating: float, opponent: float) -> float:
    """The score a Player is expected to take from a Match against the opponent."""
    return 1 / (1 + 10 ** ((opponent - rating) / SCALE))


def move(rating: float, opponent: float, score: float, k: float = K) -> float:
    """What a Match with this score (1 win, 0.5 played draw, 0 loss) adds to the Player's Rating."""
    return k * (score - expected(rating, opponent))


def play_round(ratings: dict[str, float], matches: list[tuple[str, str, float]], k: float = K) -> None:
    """Move the Ratings by one round's Matches, each read at the Ratings as they stood at the round's start.

    A Match is (Player, opponent, the Player's score). A Player not yet in the Ratings starts at 1500.
    """
    moves: dict[str, float] = {}
    for player, opponent, score in matches:
        change = move(ratings.get(player, START), ratings.get(opponent, START), score, k)
        moves[player] = moves.get(player, 0) + change
        moves[opponent] = moves.get(opponent, 0) - change
    for player, change in moves.items():
        ratings[player] = ratings.get(player, START) + change
