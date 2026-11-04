# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

<!-- Describe the goal you asked the agent to accomplish -->

**Prompts used:**

<!-- Paste the key prompts you gave the agent -->

**What did the agent generate or change?**

<!-- List the files edited, code generated, or commands run -->

**What did you verify or fix manually?**

<!-- Describe anything the agent got wrong or that required human review -->

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

The **Strategy pattern**. Each ranking style ("balanced", "genre-first", "mood-first", "energy-focused") is a small `ScoringMode` object. The scoring code stays the same and takes the mode as an input.

**How did AI help you brainstorm or implement it?**

I asked my AI coding assistant (Claude Code) which optional challenge was worth trying. It recommended Challenge 2, and I chose to go ahead with it. The assistant then brainstormed the design and wrote the code, and the result was tested and compared against the earlier output.

**Design reasoning:**

All the scoring weights already lived in one `POINTS` dictionary, and the four modes differ only in how many points each feature is worth. Three designs were possible:

1. **Copy `score_song` once per mode.** This repeats the same logic, so any later fix would have to be made four times.
2. **One class per mode, each with its own scoring method.** This is too much code, because the modes do not score differently. They only weight things differently.
3. **A mode is data: a name plus the weights it changes.** This is a lightweight Strategy pattern. Adding a mode means adding one entry to `MODES`, and the scoring code stays the same.

Option 3 was built. Two details came with it:

- A mode lists only the weights it changes. The rest come from the base `POINTS`. The weights are looked up when a song is scored, so the earlier scratch experiments that patch `POINTS` still work.
- Unknown modes fail with a clear error, and the command line only accepts valid names.

The work was done on a separate branch (`experiment/scoring-modes`), following the challenge's advice, so the working version on main stays safe.

**How does the pattern appear in your final code?**

- `ScoringMode` (a frozen dataclass), `MODES` and `get_mode()` in [src/recommender.py](src/recommender.py).
- `score_song(..., mode="balanced")` and `recommend_songs(..., mode="balanced")` take the mode. `Recommender(songs, mode=...)` stores it.
- [src/main.py](src/main.py) has `--mode NAME` to run one mode and `--compare` to show the top 3 of every mode side by side.
- Tests are at the end of [tests/test_recommender.py](tests/test_recommender.py).

**What I verified or fixed manually:**

- The default run (`balanced`) is byte-for-byte identical to the run before the change.
- Perfect matches score 1.0 and worst matches score 0.0 in every mode, so scores stay between 0 and 1 whatever the weights add up to.
- I checked that the modes really differ: for the same profile, `genre-first` and `mood-first` pick different top songs. Before, I had guessed that weight changes would barely matter. That was only partly right.
- The assistant made a mistake while editing `main.py`. Some `\n` escapes in the code it wrote were broken, which caused a syntax error. I caught it when the program failed to start. The assistant then rewrote the block, and I re-ran the program, the comparison and all 18 tests.
