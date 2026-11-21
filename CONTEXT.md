# ANZ RC data

The players and the competitive scene of the Australian Magic Regional Championships, told from every RC's standings and pairings: who plays, how they finish, how they fare against each other.

## Language

### Events

**Regional Championship (RC)**:
One of the ANZ Regional Championships run under the ANZMTG Super Series organiser on Melee, one per Cycle, each played in a single Format.
_Avoid_: Event (too wide), tournament, regional

**Cycle**:
The ordinal of an RC in the series (Cycle 1 in November 2022 to Cycle 13 in October 2026), the order every time axis follows.
_Avoid_: Season, edition

**Format**:
The constructed format an RC was played in: Pioneer, Standard or Modern. **Global** is every format together, the default view.
_Avoid_: Mode, type

**Field Size**:
The number of players in an RC's final standings, the count a Finish is read against.
_Avoid_: Attendance, event size

### People

**Player**:
One person across every RC they entered, recognised by their Melee account. Two accounts of one person (the same real name, never entered in the same RC, or joined on the owner's ruling) are one Player. The only word for a person, in the site and in the code.
_Avoid_: Pilot, competitor, entrant, account

**Display Name**:
The name the site shows for a Player: the real name their Melee account shows, else their username, unless the owner names one. A Player with several accounts shows the latest real name any of them shows, so a newer account that hides it does not hide it.
_Avoid_: Username (one of its sources), handle

**New Player**:
A Player at their first RC.
_Avoid_: Debutant, first-timer

**Experience**:
How many RCs an RC is for a Player (their 1st, their 9th), counted across every Format. Read in four levels: 1st, 2nd-3rd, 4th-7th and 8th+.
_Avoid_: Seniority, maturity

### Results

**Match**:
One pairing between two Players in one round of an RC, with its result.
_Avoid_: Game (a Match is played over games), pairing

**Intentional Draw**:
A Match both Players agreed to draw without playing: a 0-0-3 in the last two Swiss rounds at tables 1 to 8, where Players still in the hunt for the Top 8 agree to one, or a 0-0-3 the curation file names. A 0-0-3 anywhere else is a played draw. Counted in a record, never in a Rating or a win rate.
_Avoid_: ID, agreed draw

**Finish**:
A Player's rank in an RC's final standings, read against the Field Size (12th of 233). Inside the Top 8 it reads as a tier: Winner, Runner-up, Top 4 or Top 8.
_Avoid_: Placement, position, result

**Top 8**:
Reaching an RC's playoff, the result the scene counts most after winning it.
_Avoid_: Cut, day 2

**Win rate**:
Match wins over wins plus losses (66-31-3 is 68%): every draw, played or intentional, is in neither, though the record counts both.
_Avoid_: Match win percentage, MWP

**Top 8 rate**:
Top 8s over RCs played: a Player's own (3 of 7), or every Entry's at one level of Experience (15 of 192).

**Entry**:
One Player at one RC. A Player at two RCs is two Entries.
_Avoid_: Seat, registration

**Title**:
First place at an RC: the Winner Finish. "Win" alone always means a Match win.
_Avoid_: Win, trophy, first place

**Final**:
Reaching an RC's final: a Winner or Runner-up Finish. The Player card and the Leaderboard count Finals rather than Titles.
_Avoid_: Final appearance, top 2

**Best Finish**:
A Player's lowest-placed Finish, so any Winner, Runner-up, Top 4 or Top 8 comes first, in that order. Read as the place alone (12th), never against the Field Size, so a 12th of 156 beats a 14th of 222.
_Avoid_: Best result, peak finish

**Typical Finish**:
A Player's median Finish as a share of the Field Size, read as the share of the field it finishes above ("above 78% of the field"), the consistency figure beside Best Finish. The Top 4 and Top 8 tiers count at ranks 3.5 and 6.5.
_Avoid_: Average finish, mean placement

**Head-to-head**:
The Matches two given Players played against each other, and the record they add up to.
_Avoid_: H2H, rivalry

**Rating**:
An Elo-style number for a Player's strength, moved by every Match result according to the opponent's own Rating. The Leaderboard ranks on it.
_Avoid_: Elo (the method, not the number), score, ranking points

**Peak Rating**:
The highest Rating a Player has held after any RC.
_Avoid_: Max Elo, best rating

### Surfaces

**Community page**:
The landing page: the scene as a whole across RCs (Field Sizes, each field by Experience, the Top 8 rate at each level of Experience, and every RC's Winner and Runner-up).

**Player card**:
One Player's page: their RCs, Finishes, Matches and Rating over the Cycles, and Compare Players.
_Avoid_: Profile, pilot page

**Compare Players**:
The Player card's section, headed "Compare <name> with other Players", setting up to three other Players beside the card's Player: the Head-to-head records (a matrix once three or more Players are in), every Match the card's Player played against each of them, a summary row per Player, and every Player's line on the card's plot. The card's Player is the focus: Matches are listed only between them and each other Player.
_Avoid_: Face to face, versus

**Leaderboard**:
The Players ranked by Rating, in Global or one Format.
_Avoid_: Ranking, best players
