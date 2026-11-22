# ANZ RC Data

The players and competitive scene of the Australian Magic: The Gathering Regional
Championships, with every RC's results, an Elo-style leaderboard and player
head-to-heads, built from Melee standings and pairings.

**[Open the live site →](https://www.anzrcdata.com)**

## What it does

- **Overview**: every RC's Winner, Runner-up and field size, what it takes to make
  Top 8, and how often players at each level of experience get there.
- **Leaderboard**: every Player ranked by Rating, across all formats or in one.
- **Player card**: one Player's RCs, finishes, Matches and Rating over the Cycles.
- **Compare Players**: up to three other Players beside the card's Player, with
  the head-to-head record and every Match between them.

## Updating and deploying

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). After a new RC, add
its row to `data/rcs.csv`, run `scripts/update.sh`, then `scripts/deploy_space.sh`.
[docs/deploy.md](docs/deploy.md) has the full procedure.

## Documentation

| | |
| --- | --- |
| [CONTEXT.md](CONTEXT.md) | Domain language: RC, Cycle, Player, Match, Rating |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [docs/deploy.md](docs/deploy.md) | Updating after a new RC, and deploying the site |

## Data

Standings, pairings and decklists come from [Melee](https://melee.gg), under the
organiser [ANZMTG Super Series](https://melee.gg/Hub/Organization/2834). The Rating
follows, and is checked against, the [MTG Elo Project](https://www.mtgeloproject.net).

This project is free, non-commercial and unofficial. It is not affiliated with
Melee, the MTG Elo Project, ANZMTG or Wizards of the Coast. If you run one of these
sources, or appear in the data and want something corrected or removed, open an
issue.

## License

[MIT](LICENSE). This covers the code in this repository; the data under `data/`
comes from the sources above and remains subject to their terms.
