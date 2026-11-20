"""The build, driven through its public interface: raw folder and RC list in, bundle out."""

import json

from anzrc.build import build

EVENT_PAGE = """<html>
<button class="btn btn-gray round-selector" data-id="501" data-name="Round 1" data-is-completed="True">
<button class="btn btn-gray round-selector" data-id="502" data-name="Finals" data-is-completed="True">
<button class="btn btn-gray round-selector" data-id="501" data-name="Round 1" data-is-started="True">
<button class="btn btn-gray round-selector" data-id="502" data-name="Finals" data-is-started="True">
</html>"""


def standing(rank, display_name, username):
    """A final standings row cut down from Melee's shape."""
    player = {"DisplayName": display_name, "Username": username}
    return {"Team": {"Players": [player]}, "Rank": rank, "MatchingMethodDescription": "Playoffs/Top Cut"}


def write_rc(raw, melee_id, round_1, final):
    folder = raw / str(melee_id)
    folder.mkdir(parents=True)
    (folder / "event.html").write_text(EVENT_PAGE)
    for round_id, rows in (("501", round_1), ("502", final)):
        (folder / f"standings-{round_id}.json").write_text(json.dumps({"recordsTotal": len(rows), "data": rows}))


def test_writes_each_rc_with_its_field_size_and_champion(tmp_path):
    raw = tmp_path / "raw"
    write_rc(
        raw,
        12737,
        round_1=[standing(1, "Steven Hitchcock", "exsuit"), standing(2, "Jane Roe", "janer")],
        final=[
            standing(2, "Steven Hitchcock", "exsuit"),
            standing(1, "Jane Roe", "janer"),
            standing(3, "kim", "kim"),
        ],
    )
    rc_list = tmp_path / "rcs.csv"
    rc_list.write_text("cycle,melee_id,format,city,start_date\n1,12737,Pioneer,,2022-11-25\n")

    build(raw, rc_list, tmp_path / "bundle")

    assert json.loads((tmp_path / "bundle" / "rcs.json").read_text()) == [
        {"cycle": 1, "date": "2022-11-25", "city": None, "format": "Pioneer", "field_size": 3, "champion": "Jane Roe"}
    ]
