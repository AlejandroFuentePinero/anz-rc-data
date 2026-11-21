# Measurements

Written by `anzrc-measure` from the build's own replay of every RC (13 RCs, 8140 rated Matches). The constants in `anzrc.ratings` are set from it, and ADR 0001 records the numbers. Log loss is the mean of -(s ln p + (1 - s) ln(1 - p)) over Matches, where p is the expected score and s the result (1, 0.5 or 0); calling every Match 50-50 scores ln 2 = 0.6931. Lower is better.

## K

Every Match from Cycle 2 on, predicted from the Ratings at the start of its RC (moved only by earlier RCs). A K other than 36 is kept only if it beats 36 by more than two standard errors of the paired per-Match difference; anything closer is a tie, and a tie keeps 36.

| K | Log loss | Against K = 36 | Standard error |
|---|---|---|---|
| 16 | 0.68860 | +0.00173 | 0.00062 |
| 20 | 0.68798 | +0.00111 | 0.00049 |
| 24 | 0.68751 | +0.00065 | 0.00036 |
| 28 | 0.68718 | +0.00031 | 0.00023 |
| 32 | 0.68697 | +0.00010 | 0.00012 |
| 36 | 0.68687 | +0.00000 | 0.00000 |
| 40 | 0.68686 | -0.00001 | 0.00011 |
| 44 | 0.68694 | +0.00008 | 0.00022 |
| 48 | 0.68711 | +0.00024 | 0.00033 |
| 52 | 0.68735 | +0.00048 | 0.00043 |
| 56 | 0.68766 | +0.00079 | 0.00053 |
| 60 | 0.68804 | +0.00117 | 0.00063 |
| 64 | 0.68848 | +0.00161 | 0.00073 |

Scored on 7622 Matches. Lowest log loss: K = 40. **K = 36.**

## Per-Format

Each Format's own Rating (K = 36, every Player new at 1500 in it) predicts that Format's RCs after its first, from the Ratings at each RC's start. It ships if its log loss beats the 50-50 baseline. The Global Rating's log loss on the same Matches, also read at each RC's start, is shown beside it.

| Format | RCs (Cycles) | Scored | Matches | Log loss | Against 50-50 (SE) | Global on the same Matches | Own against Global (SE) | Ships |
|---|---|---|---|---|---|---|---|---|
| Pioneer | 1, 3, 4, 7 | 3, 4, 7 | 1831 | 0.68850 | -0.00465 (0.00143) | 0.68706 | +0.00144 (0.00138) | yes |
| Standard | 2, 6, 9, 11, 12 | 6, 9, 11, 12 | 2560 | 0.68984 | -0.00331 (0.00134) | 0.68823 | +0.00160 (0.00183) | yes |
| Modern | 5, 8, 10, 13 | 8, 10, 13 | 2003 | 0.68813 | -0.00502 (0.00143) | 0.68407 | +0.00405 (0.00206) | yes |

## Stability

1000 resamples (seed 2026) of each RC's rated Matches with replacement, each keeping its round, replayed in order with K = 36. The figure is the mean number of the observed Global top 10 still in a resample's top 10. Eight or more drops "Rank could be"; fewer keeps it as each Player's 90% rank interval.

| RCs needed | Leaderboard size | Top 10 kept |
|---|---|---|
| 2 | 461 | 5.14 |
| 3 | 301 | 5.14 |
| 4 | 220 | 5.21 |

Top 10 at 2 RCs, with the 90% rank interval across resamples:

| Rank | Player | Rating | 90% rank interval |
|---|---|---|---|
| 1 | connor mcgillivray | 1883 | 1 to 24 |
| 2 | Ben Tudman | 1845 | 1 to 45 |
| 3 | James Drake | 1837 | 1 to 39 |
| 4 | Brennan Crawford | 1828 | 1 to 52 |
| 5 | Henry Sams | 1822 | 1 to 53 |
| 6 | Zen Miyaji-Thorne | 1810 | 1 to 55 |
| 7 | Christopher Tong | 1779 | 2 to 78 |
| 8 | Nathan Basser | 1775 | 2 to 88 |
| 9 | Alex Humbley | 1769 | 2 to 92 |
| 10 | Sebastian Vearncombe | 1759 | 3 to 99 |

Top 10 at 3 RCs, with the 90% rank interval across resamples:

| Rank | Player | Rating | 90% rank interval |
|---|---|---|---|
| 1 | connor mcgillivray | 1883 | 1 to 24 |
| 2 | Ben Tudman | 1845 | 1 to 43 |
| 3 | James Drake | 1837 | 1 to 38 |
| 4 | Brennan Crawford | 1828 | 1 to 50 |
| 5 | Henry Sams | 1822 | 1 to 50 |
| 6 | Zen Miyaji-Thorne | 1810 | 1 to 53 |
| 7 | Christopher Tong | 1779 | 2 to 73 |
| 8 | Nathan Basser | 1775 | 2 to 80 |
| 9 | Alex Humbley | 1769 | 2 to 83 |
| 10 | Sebastian Vearncombe | 1759 | 3 to 89 |

Top 10 at 4 RCs, with the 90% rank interval across resamples:

| Rank | Player | Rating | 90% rank interval |
|---|---|---|---|
| 1 | connor mcgillivray | 1883 | 1 to 23 |
| 2 | Ben Tudman | 1845 | 1 to 40 |
| 3 | James Drake | 1837 | 1 to 36 |
| 4 | Brennan Crawford | 1828 | 1 to 44 |
| 5 | Henry Sams | 1822 | 1 to 45 |
| 6 | Zen Miyaji-Thorne | 1810 | 1 to 48 |
| 7 | Christopher Tong | 1779 | 2 to 63 |
| 8 | Nathan Basser | 1775 | 2 to 68 |
| 9 | Alex Humbley | 1769 | 2 to 71 |
| 10 | Sebastian Vearncombe | 1759 | 2 to 76 |

## Cutoff

See the Stability table: Leaderboard size and top-10 stability at 2, 3 and 4 RCs.
