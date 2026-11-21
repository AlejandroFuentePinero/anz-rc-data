# How faithful the Rating is to mtgeloproject

**Verdict: the Rating is mtgeloproject's calculation, proven on their own numbers.** Given the same two Ratings before a Match and the same result, this site moves a Rating by exactly what mtgeloproject moves it, on every one of the 16,280 rated Matches they record for the 13 ANZ RCs. Where the two sites differ, it is never the maths: it is which Matches count (2 Matches, each listed below with its reason), and the fact that this site counts only the ANZ RCs.

A worked example. In Cycle 1, round 2, mtgeloproject has a Player at 1465.86 drawing an opponent at 1519.01. The expected score for the lower-rated Player is 1 / (1 + 10^(-(1465.86 - 1519.01) / 1135.77)) = 0.4731, so a draw (worth 0.5) moves them up by 36 x (0.5 - 0.4731) = 0.97, to 1466.83. mtgeloproject shows 1466.83.

## The calculation

- Every Player starts at 1500.
- A Match moves each Player's Rating by K x (result - expected score), with K = 36. A win is 1, a played draw 0.5, a loss 0. The two moves are equal and opposite.
- Expected score = 1 / (1 + 10^(-gap / 1135.77)), where gap is the Player's Rating minus the opponent's. 1135.77 is 200 / log10(1.5), the number that makes a 200 point gap a 60% expectation.
- Intentional Draws and Matches not played (byes, forfeits, "not reported") move nothing. An Intentional Draw is a 0-0-3 in the last two Swiss rounds at tables 1 to 8, where Players still in the hunt for the Top 8 agree to draw, or one the curation file names from mtgeloproject's record; a 0-0-3 anywhere else is a played draw. Game score never matters, only the result.
- RCs are replayed in Cycle order, then round order; every Match in a round reads the Ratings as the round started. A Player plays once per round, so this gives exactly what mtgeloproject's "after each match" gives.
- Playoff Matches count like Swiss ones, rebuilt ones included. No decay.
- Four views: Global from every Match, and Pioneer, Standard and Modern each from its own Matches, every Player starting at 1500 in each.
- Peak Rating is the highest Rating after any RC.

Every rule above is mtgeloproject's as its FAQ states it (mtgeloproject.net/faq, read 2026-11-21): the 1500 start, K = 36, the 200-points-for-60% scale, unintentional draws as half a win, Intentional Draws and byes moving nothing, game score ignored, every Match weighted the same.

## Why the numbers differ from a Player's mtgeloproject Rating

On purpose. mtgeloproject rates every event it holds (Pro Tours, Grand Prix, other regions' RCs and more), so a Player arrives at an ANZ RC already carrying a Rating. This site is an Elo project for the ANZ RCs alone: everyone starts at 1500 at their first ANZ RC. Same calculation, different history, so a Player's number here is not their number there.

## How it was checked

Three independent checks, each run on the full data and kept as a test or a rerunnable command.

### 1. The rule, against mtgeloproject's own numbers

mtgeloproject's public API gives, for every Match, each Player's Rating before and after and the opponent's Rating before. `anzrc-fetch-mtgelo` fetched it for every person in the 13 ANZ RCs (910 people, 16,378 rows, kept in data/mtgeloproject).

| Check | Result |
|---|---|
| Rated Matches reproduced (wins, losses and 470 played draws) | 16,280 of 16,280 |
| Largest difference from their Rating after the Match | 0.0099 (their numbers are rounded to 0.01) |
| Their 98 Intentional Draws | all move nothing |
| The same rule with K = 35 or 37 | misses by up to 0.79 |
| The same rule with a scale of 1100 or 1150 | misses by up to 0.26 |
| Chess's 400-point scale | misses by up to 7.8 |

So K and the scale are pinned by the data, not assumed. Test: tests/test_mtgelo_oracle.py.

### 2. Which Matches count, and who is one Player

Each mtgeloproject row was found among Melee's Matches by RC, round and table, and compared with what the build rates.

- Every Match mtgeloproject rates, the build rates with the same result, and every Match the build rates (8,140), mtgeloproject records. The exceptions are the 2 below, listed in the test, so any new difference fails it.
- The 17 playoff Matches Melee lost and the build rebuilds (Cycles 3 and 4 entirely, the finals of Cycles 7, 8 and 10) have the same pairings and the same winners in mtgeloproject's record.
- Both records name the same 49 Matches as Intentional Draws. Melee records every 0-0-3 alike ("0-0-3 Draw"); the rule (last two Swiss rounds, tables 1 to 8) gives 48 of them, and the curation file names the 49th (Cycle 5 round 9 table 37, two Players on 12 points in the last round). Every other 0-0-3, five of them in rounds 1 to 3 and three later but off the top tables (tables 11, 57 and 58), is a played draw in both.
- Every mtgeloproject person is one Player here, and every Player one person there, but for three noted below.

| Where the two differ | Matches | Why the build does what it does |
|---|---|---|
| Cycle 1 round 3 table 65, round 5 table 60 | 2 | mtgeloproject has the same 2-1 score with the winner swapped. Melee names its winner in four places that agree: the game wins, the result text ("Lisa McGlaughlin won 2-1-0", "Ryan McCartney won 2-1-0"), the final standings points, and its own pairings for the next round, which put each winner among the Players on the points that win gives them (round 4 table 44 in the 3-point group, not table 68 in the 0-point group; round 6 table 51 in the 6-point group, not 54 to 56 in the 3-point group). The build follows Melee. |
| natebass, miketaylor | | One Melee account each, which mtgeloproject splits in two after a change of name. One account is one Player. |
| tylervisser | | Two accounts with the same real name, joined by the identity rule; mtgeloproject keeps a misspelt "Visserr" apart. |

Three of the owner's rulings came out of this check and are in ADR 0001: which 0-0-3 is an Intentional Draw, as above, following mtgeloproject; a Match Melee left unconfirmed counts by its game score (Cycle 13's 0-0-1 is a played draw, as Melee's standings and mtgeloproject both count it); and where mtgeloproject holds two accounts as one person they are one Player here (14 joins in data/curation.toml).

### 3. A blind reimplementation

A separate agent rebuilt every Rating from the raw Melee files and the written rules, without seeing this code. Its numbers and the build's agree for all 907 Players, every view, every Rating after every RC and every Peak (9,628 values), and for the opponent's Rating before each of the 16,280 rated Match sides. The largest difference is 0.005, the two-decimal rounding of the bundle. After the 0-0-3 ruling it was rerun with that one line of its rules changed, and still agrees everywhere.

## The measured settings

From docs/measurements.md, which `anzrc-measure` rewrites:

- **K = 36.** K = 40 predicts later RCs a hair better, by 0.00001 against a standard error of 0.00011: a tie, so mtgeloproject's 36 stays.
- **Pioneer, Standard and Modern Ratings ship.** Each beats a 50-50 guess on its own later RCs, by more than two standard errors. The Global Rating predicts each Format's Matches slightly better still, within noise for Pioneer and Standard and about two standard errors for Modern; the rule asks only for beating 50-50.
- **"Rank could be" stays.** Only about 5 of the top 10 stay in the top 10 when each RC's Matches are resampled, so the top of the Leaderboard is not settled and each rank shows its 90% interval.
- **3 RCs to be ranked.** The stability of the top 10 barely moves between 2, 3 and 4 RCs (5.14, 5.14, 5.21), so 3 stands, ranking 301 Players.

## Confidence and what is left

- **The calculation: certain.** It reproduces mtgeloproject's own Rating changes on all 16,280 rated Matches, and nearby rules do not.
- **The inputs: high.** Every rated Match agrees with mtgeloproject's record but 2, where Melee names the other winner; identity agrees but 3, each explained.
- **The code: high.** An implementation written blind from the raw data gives the same numbers.
- **Not checked here:** mtgeloproject's own record can be wrong (the two Cycle 1 results are the cases found), and the per-Player rank intervals the Leaderboard shows are built in issue #9, from the resampling already measured.
