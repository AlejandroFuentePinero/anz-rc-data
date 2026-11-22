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
The constructed format an RC was played in: Pioneer, Standard or Modern. **All** is every format together, the default view (Global in the data and the URLs, never in the interface).
_Avoid_: Mode, type

**Field Size**:
The number of players in an RC's final standings, the count a Finish is read against. The Overview's RC history shows it with a bar to scale beside it, the largest RC filling the column.
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
How many RCs an RC is for a Player (their 1st, their 9th), counted across every Format. The Field by Experience bars read it in four levels: 1st, 2nd-3rd, 4th-7th and 8th+. The Top 8 rate by Experience table reads it RC by RC from 1 to 9, then 10+.
_Avoid_: Seniority, maturity

### Results

**Match**:
One pairing between two Players in one round of an RC, with its result.
_Avoid_: Game (a Match is played over games), pairing

**Intentional Draw**:
A Match both Players agreed to draw without playing: a 0-0-3 in the last two Swiss rounds at tables 1 to 8, where Players still in the hunt for the Top 8 agree to one, or a 0-0-3 the curation file names. A 0-0-3 anywhere else is a played draw. Counted in a record, never in a Rating or a win rate. Its Result cell reads ID with the games, ID (0-0-3).
_Avoid_: agreed draw

**Bye**:
A round a Player is given without an opponent: assigned (an odd field) or awarded, both as Melee records them. A Bye is a win in every record (every W-L-D on the site, the Top 8 table) and in Win rate. It moves no Rating, because nothing was played, as with an Intentional Draw. Head-to-head never holds one, since a Bye has no opponent.
_Avoid_: Free win

**Finish**:
A Player's rank in an RC's final standings, read against the Field Size (12th of 233). Inside the Top 8 it reads as a tier: Winner, Runner-up, Top 4 or Top 8.
_Avoid_: Placement, position, result

**Top 8**:
Reaching an RC's playoff, the result the scene counts most after winning it.
_Avoid_: Cut, day 2

**Win rate**:
Match wins over wins plus losses (66-31-3 is 68%), a Bye counted as a win: every draw, played or intentional, is in neither, though the record counts both.
_Avoid_: Match win percentage, MWP

**Top 8 rate**:
Top 8s over RCs played: a Player's own (3 of 7), or every Entry's at one RC played (14 of 755 at a first RC). Top 8 rate by Experience heads that count **Players**: a Player counts once for each RC they played, so the 10+ row counts a Player once for each RC from their 10th. It counts every Player who played an RC, not only those in its final standings, so an RC whose final standings miss a Player counts one more than its Field Size.

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
A Player's median Finish as a share of the Field Size, read as the share of the field it finishes above ("above 78% of the field"), the consistency figure beside Best Finish. The Top 4 and Top 8 tiers count at ranks 3.5 and 6.5. The Player card reads it from the top, as **Typically finishes top**: above 85.2% of the field is the top 14.8%.
_Avoid_: Average finish, mean placement

**Worst record in**:
The worst Swiss record in an RC's Top 8, ordered by points (3 a win, 1 a draw, a Bye a win), then by wins, beside the **Best record**, the best. The Overview's What it takes to make Top 8 table names it so, since Cut is avoided for the Top 8.

**Made it on that record**:
How many of the Players who finished an RC's Swiss on the Worst record in's points made Top 8 ("5 of 8").

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

**Overview**:
The landing page, in tables with no plots, two columns stacked under 1100px: RC history (each RC's Winner and Runner-up, its Field Size and its field by Experience as bars in its row) beside What it takes to make Top 8, both under the Format buttons; then Top 8 rate by Experience beside Played every RC, both across every RC.
_Avoid_: Community page

**Played every RC**:
The Overview's table of the Players who played every RC, by Rating, with their ANZ Rank, W-L-D, Win rate, Top 8s and Best Finish.

**Player card**:
One Player's page: their RCs, Finishes, Matches and Rating over the Cycles, and Compare Players.
_Avoid_: Profile, pilot page

**Compare Players**:
The Player card's section, headed "Compare <name> with other Players", setting up to three other Players beside the card's Player: a summary row per Player, then for each of them a Match table headed "Against <name>" with the card's Player's W-L-D against them (or "Never met") and every Match they played, and every Player's line on the card's plot. The card's Player is the focus: Matches are listed only between them and each other Player.
_Avoid_: Face to face, versus

**Leaderboard**:
The Players ranked by Rating, in All or one Format.
_Avoid_: Ranking, best players
