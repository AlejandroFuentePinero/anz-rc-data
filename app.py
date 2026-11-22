"""Hugging Face Space entrypoint: the site as built, served with its own record of use (issue #14).

The Space is a Gradio Space only because that is the SDK the other apps run on and where the
usage bucket was measured mounted; no Gradio UI is built. The Space runs `python app.py`, and
this starts the server in `anzrc.serve` on the port the Space is reached on. The package sits
beside this file on the Space, so it needs no install.
"""

from anzrc.serve import main

if __name__ == "__main__":
    main()
