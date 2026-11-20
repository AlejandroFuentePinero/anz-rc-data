# ANZ Regional Championships: Melee sources

All 13 ANZ Magic Regional Championships (RC1–RC13) are on Melee under the organiser
[ANZMTG Super Series](https://melee.gg/Hub/Organization/2834) (organiser ID `2834`).

Checked 2026-11-20: each event below returns standings, pairings with results, and full decklists.

## Events

| Cycle | City | Start date (UTC) | Format | Players | Event page | Pairings | Standings |
|---|---|---|---|---|---|---|---|
| 1 | Sydney | 2022-11-25 | Pioneer | 152 | [12737](https://melee.gg/Tournament/View/12737) | [pairings](https://melee.gg/Tournament/View/12737#pairings) | [standings](https://melee.gg/Tournament/View/12737#standings) |
| 2 | - | 2023-03-03 | Standard | 132 | [13123](https://melee.gg/Tournament/View/13123) | [pairings](https://melee.gg/Tournament/View/13123#pairings) | [standings](https://melee.gg/Tournament/View/13123#standings) |
| 3 | - | 2023-06-24 | Pioneer | 180 | [13419](https://melee.gg/Tournament/View/13419) | [pairings](https://melee.gg/Tournament/View/13419#pairings) | [standings](https://melee.gg/Tournament/View/13419#standings) |
| 4 | Sydney | 2023-10-27 | Pioneer | 156 | [14959](https://melee.gg/Tournament/View/14959) | [pairings](https://melee.gg/Tournament/View/14959#pairings) | [standings](https://melee.gg/Tournament/View/14959#standings) |
| 5 | Melbourne | 2024-03-08 | Modern | 228 | [17545](https://melee.gg/Tournament/View/17545) | [pairings](https://melee.gg/Tournament/View/17545#pairings) | [standings](https://melee.gg/Tournament/View/17545#standings) |
| 6 | Melbourne | 2024-05-25 | Standard | 168 | [44116](https://melee.gg/Tournament/View/44116) | [pairings](https://melee.gg/Tournament/View/44116#pairings) | [standings](https://melee.gg/Tournament/View/44116#standings) |
| 7 | Sydney | 2024-11-08 | Pioneer | 221 | [73431](https://melee.gg/Tournament/View/73431) | [pairings](https://melee.gg/Tournament/View/73431#pairings) | [standings](https://melee.gg/Tournament/View/73431#standings) |
| 8 | Sydney | 2025-03-07 | Modern | 154 | [123662](https://melee.gg/Tournament/View/123662) | [pairings](https://melee.gg/Tournament/View/123662#pairings) | [standings](https://melee.gg/Tournament/View/123662#standings) |
| 9 | Melbourne | 2025-05-09 | Standard | 222 | [179718](https://melee.gg/Tournament/View/179718) | [pairings](https://melee.gg/Tournament/View/179718#pairings) | [standings](https://melee.gg/Tournament/View/179718#standings) |
| 10 | Melbourne | 2025-10-24 | Modern | 212 | [241092](https://melee.gg/Tournament/View/241092) | [pairings](https://melee.gg/Tournament/View/241092#pairings) | [standings](https://melee.gg/Tournament/View/241092#standings) |
| 11 | Sydney | 2026-03-13 | Standard | 209 | [341156](https://melee.gg/Tournament/View/341156) | [pairings](https://melee.gg/Tournament/View/341156#pairings) | [standings](https://melee.gg/Tournament/View/341156#standings) |
| 12 | Adelaide | 2026-05-22 | Standard | 188 | [379086](https://melee.gg/Tournament/View/379086) | [pairings](https://melee.gg/Tournament/View/379086#pairings) | [standings](https://melee.gg/Tournament/View/379086#standings) |
| 13 | Sydney | 2026-10-23 | Modern | 233 | [414849](https://melee.gg/Tournament/View/414849) | [pairings](https://melee.gg/Tournament/View/414849#pairings) | [standings](https://melee.gg/Tournament/View/414849#standings) |

The Melee event titles give the city only from Cycle 6 onwards. Cities for Cycles 4 and 5 come from the MTG Wiki season page. The city for Cycle 1 comes from its own Melee event description ("journey to Sydney"); Cycles 2 and 3 have no known city. "Players" is the number of players in the final standings.

## Machine-readable list

```yaml
organiser_id: 2834
events:
  - {cycle: 1,  melee_id: 12737,  format: Pioneer}
  - {cycle: 2,  melee_id: 13123,  format: Standard}
  - {cycle: 3,  melee_id: 13419,  format: Pioneer}
  - {cycle: 4,  melee_id: 14959,  format: Pioneer}
  - {cycle: 5,  melee_id: 17545,  format: Modern}
  - {cycle: 6,  melee_id: 44116,  format: Standard}
  - {cycle: 7,  melee_id: 73431,  format: Pioneer}
  - {cycle: 8,  melee_id: 123662, format: Modern}
  - {cycle: 9,  melee_id: 179718, format: Standard}
  - {cycle: 10, melee_id: 241092, format: Modern}
  - {cycle: 11, melee_id: 341156, format: Standard}
  - {cycle: 12, melee_id: 379086, format: Standard}
  - {cycle: 13, melee_id: 414849, format: Modern}
```

## How to extract the data

1. **Round IDs.** Fetch `https://melee.gg/Tournament/View/{melee_id}`. Each round button
   (`.round-selector`) has `data-id` (round ID), `data-name` and `data-is-completed`.
2. **Pairings and results.** Send `POST https://melee.gg/Match/GetRoundMatches/{roundId}` with
   DataTables form params (`draw`, `start=0`, `length=1000`, `columns[0][data]=TableNumber`,
   `order[0][column]=0`, `order[0][dir]=asc`). The response is JSON with `recordsTotal` and `data[]`
   (`Competitors`, `ResultString`, `HasResult`, `RoundNumber`, `TableNumber`, ...).
3. **Standings.** Send `POST https://melee.gg/Standing/GetRoundStandings` with the same params plus
   `roundId`, using the last round for final standings. Each row has `Rank`, `Points`, match and game
   records, tiebreakers (`OpponentMatchWinPercentage`, ...) and `Decklists[]` (`DecklistId`, `DecklistName`).
4. **Decklists.** Fetch `https://melee.gg/Decklist/View/{DecklistId}` and parse the card links and
   `.decklist-record-quantity`.

## Known quirks

- Round names differ between events. Some playoff rounds are named "Quarterfinals/Semifinals/Finals"
  and others continue as "Round 9…". Tell Swiss and playoff rounds apart by phase, not by name.
- Cycle 13 has 1 match out of 812 with no result. It is probably a bye or a drop.
- In Cycles 4 and 7, summing every quantity on the deck page gives 76. This is probably a companion
  or an extra counter, so parse the main deck and sideboard separately.
- Requests time out if all 13 events are fetched at once. Fetch them one at a time with a short delay.
