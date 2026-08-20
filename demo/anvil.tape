# VHS tape for the anvil README demo.
# Regenerate with:  vhs demo/anvil.tape   (run from the repo root)
# Produces demo/anvil.gif — the CLI teaching an agent to improve itself, live.

Output demo/anvil.gif

Set Shell zsh
Set FontSize 16
Set Width 1200
Set Height 300
Set Padding 24
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms

# Activate the project venv off-camera so `anvil` is on PATH.
Hide
Type "source .venv/bin/activate && clear"
Enter
Sleep 800ms
Show

Sleep 600ms
Type "anvil demo"
Sleep 700ms
Enter

# Let the curve reveal one iteration at a time (0.7s per row) and settle.
Sleep 6s
