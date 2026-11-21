# Players are ranked by an Elo-style Rating built from pairings, not by Finish

7ph-graph ranks pilots on their normalised finish because its source publishes only final standings. The RCs publish every pairing and result, so the Leaderboard ranks on a plain Elo Rating instead, following the MTG Elo Project (mtgeloproject.net): everyone starts at 1500, every played Match moves both Ratings by its result alone, never its game score, and the community already knows and accepts this way of ranking. Each Match is a data point, which gives about ten observations per RC where a Finish gives one, and beating a strong Player counts for more than beating a weak one.

## Rules that hang off it

- K is not assumed. The value kept is the one that best predicts each later RC's Matches from the Ratings before it.
- Global is the default and the Rating that matters most. A Pioneer, Standard or Modern Rating, moved only by that Format's Matches, ships only if it predicts its own later Matches better than chance, because each Format has only 4 or 5 RCs.
- Intentional Draws and byes do not move a Rating, and played draws count as half a win. Top 8 Matches count like Swiss ones.
- No decay for inactivity.
- Finish is kept for what it is good at: Top 8s, Titles, Best Finish and Typical Finish describe a Player's results, never their rank.

## Measured (docs/measurements.md, 2026-11-21)

- **K = 36**, mtgeloproject's own. Predicting every Match from Cycle 2 on from the Ratings before its RC, K = 40 scores lowest (log loss 0.68686 against 0.68687), a difference of 0.00001 with a standard error of 0.00011: a tie, so 36 stays. K from 16 to 64 all lie within 0.0017 of each other.
- **All three Format Ratings ship.** The rule is beating the 50-50 baseline on its own later RCs, and each does so by more than two standard errors: Pioneer by 0.0047 (SE 0.0014), Standard by 0.0033 (SE 0.0013), Modern by 0.0050 (SE 0.0014). Read the same way on the same Matches, the Global Rating predicts slightly better (by 0.0014 to 0.0041: about one standard error for Pioneer and Standard, two for Modern), which the rule does not ask about.
- **No "Rank could be".** Across 1000 resamples only 5.1 of the observed Global top 10 stay in the top 10, which by the measurement's own rule would keep each Player's 90% rank interval (the leader's runs from 1 to about 25). The owner ruled it not needed on the rendered Leaderboard (2026-11-21), so the Leaderboard shows the rank alone.
- **The cutoff stays at 3 RCs.** Stability barely moves with it (5.14, 5.14 and 5.21 of 10 at 2, 3 and 4 RCs) while the Leaderboard holds 461, 301 and 220 Players, so nothing argues against 3.

## Faithful to mtgeloproject

mtgeloproject's public record of the same 13 RCs (16,378 Player-Match rows, fetched by `anzrc-fetch-mtgelo` into data/mtgeloproject) is the oracle, checked by tests/test_mtgelo_oracle.py:

- **The rule.** Given each row's two Ratings before the Match and its result, K = 36 on the 200-points-for-60% scale reproduces every one of their Ratings after it within their two-decimal rounding. A K of 35 or 37, or a scale of 1100 or 1150, misses.
- **The Matches.** Every Match they rate we rate with the same result, and every Match we rate they record, but for two listed in the test: Cycle 1 Matches where Melee's own result names the other winner. Ratings follow Melee there.
- **The Players.** Each mtgeloproject person is one Player here, but for three: two Melee accounts they split by a change of name, and one same-real-name join they do not make.

Owner rulings from this check (2026-11-21):

- A 0-0-3 is an Intentional Draw in the last two Swiss rounds at tables 1 to 8, where Players still in the hunt for the Top 8 agree to draw, and a played draw anywhere else. Melee records both as "0-0-3 Draw". This is where mtgeloproject draws the line, and where its curation calls one differently the curation file follows it (one so far, Cycle 5 round 9 table 37), so the two records name the same 49 Intentional Draws. It replaces an earlier ruling that every 0-0-3 is an Intentional Draw.
- A Match Melee left unconfirmed counts by its game score like any other: Cycle 13's 0-0-1 is a played draw, as Melee's standings count it. A Match with no games recorded at all (0-0-0) has no result to count, so the build stops and asks for a ruling.
- Where mtgeloproject holds two Melee accounts as one person, they are one Player here (14 joins in data/curation.toml), because its identities are well curated.

## Considered options

- **Finish-based score (7ph-graph's)**: rejected because it throws away the pairings and has one observation per RC, with 466 of 925 Players having played a single RC.
- **Glicko-style rating with an uncertainty term**: rejected because it is less familiar to the community. The uncertainty it would carry is measured separately, by resampling, and shown as a "Rank could be" column only if the top of the Leaderboard proves unstable.
