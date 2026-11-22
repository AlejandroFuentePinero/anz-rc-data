---
title: ANZ RC Data
emoji: 🏆
colorFrom: yellow
colorTo: red
short_description: The Players of the ANZ Magic Regional Championships
sdk: gradio
sdk_version: 6.32.0
# Pinned exactly: the interpreter the suite runs on, rather than whatever 3.12.x the image
# would pick. No Gradio UI is built; app.py starts the site's own small server.
python_version: "3.12.12"
app_file: app.py
pinned: false
---

# ANZ RC Data

The Players of the ANZ Magic Regional Championships, from every RC's standings and pairings:
an Overview, a Leaderboard ranked by Rating, and a page per Player.

This Space serves the site as built in [the source repo](https://github.com/AlejandroFuentePinero/anz-rc-data)
and keeps a count of its own visits. It is rebuilt and redeployed by hand after each new RC.
