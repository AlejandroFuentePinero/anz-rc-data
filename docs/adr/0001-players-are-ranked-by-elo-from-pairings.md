# Players are ranked by an Elo-style Rating built from pairings, not by Finish

7ph-graph ranks pilots on their normalised finish because its source publishes only final standings. The RCs publish every pairing and result, so the Leaderboard ranks on a plain Elo Rating instead, following the MTG Elo Project (mtgeloproject.net): everyone starts at 1500, every played Match moves both Ratings by its result alone, never its game score, and the community already knows and accepts this way of ranking. Each Match is a data point, which gives about ten observations per RC where a Finish gives one, and beating a strong Player counts for more than beating a weak one.

## Rules that hang off it

- K is not assumed. The value kept is the one that best predicts each later RC's Matches from the Ratings before it.
- Global is the default and the Rating that matters most. A Pioneer, Standard or Modern Rating, moved only by that Format's Matches, ships only if it predicts its own later Matches better than chance, because each Format has only 4 or 5 RCs.
- Intentional draws (recorded 0-0-3) and byes do not move a Rating, and played draws count as half a win. Top 8 Matches count like Swiss ones.
- No decay for inactivity.
- Finish is kept for what it is good at: Top 8s, Titles, Best Finish and Typical Finish describe a Player's results, never their rank.

## Considered options

- **Finish-based score (7ph-graph's)**: rejected because it throws away the pairings and has one observation per RC, with 466 of 925 Players having played a single RC.
- **Glicko-style rating with an uncertainty term**: rejected because it is less familiar to the community. The uncertainty it would carry is measured separately, by resampling, and shown as a "Rank could be" column only if the top of the Leaderboard proves unstable.
