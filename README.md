# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

In short: the system loads the 18 songs in `data/songs.csv`, scores each one against a user's taste profile using a weighted point recipe, sorts by score, and returns the top `k` with a reason for each pick.

```
INPUT: User Prefs            data/songs.csv (18 songs)
{genre, mood, energy,              │
 likes_acoustic, ...}       load_songs() → List[Dict]
        └──────────────┬───────────┘
                       ▼
PROCESS: for each song → score_song(prefs, song)
         points earned / points available → score (0-1) + reasons
                       ▼
OUTPUT: sort by score, descending → top k (song, score, explanation)
```

### Overview

Real-world recommenders such as Spotify or YouTube combine two kinds of signals. Collaborative filtering uses what millions of other listeners played, skipped, or saved. Content-based filtering uses the attributes of the songs themselves. They score each candidate song for each user, rank the scores, and show the top results, often adjusting for variety and freshness. My version is a small content-based recommender: it has no listening history or other users, so it can only compare a song's attributes to a stated taste profile. It prioritizes the overall "vibe" of a song (how energetic, how positive, how acoustic, and what mood it carries) over its genre label, and it rewards songs that are *close* to what the user wants rather than songs with simply higher or lower values.

### Song features

Each `Song` uses these attributes from `data/songs.csv`:

- **Used in scoring:** `energy`, `valence`, `acousticness`, `mood`, `genre`, plus the optional `instrumentalness` (share of the song with no vocals), `speechiness` (share that is spoken word) and `release_year`
- **Stored but not scored:** `id`, `title`, `artist`, `tempo_bpm`, `danceability` (tempo and danceability largely overlap with energy)

### UserProfile features

The `UserProfile` stores:

- `favorite_genre`: preferred genre (text)
- `favorite_mood`: preferred mood (text)
- `target_energy`: desired energy level, 0 to 1
- `likes_acoustic`: whether the user prefers acoustic sound (true/false), treated as a target acousticness of 0.8 or 0.2

The function-based version (`recommend_songs`) also accepts optional `valence`, `instrumentalness` and `speechiness` targets (0 to 1) and a `release_year` target.

### Scoring Rule and Ranking Rule

Scoring Rule (one song): each feature earns points, and `score = points earned / points available`, giving a value from 0 to 1.

| Feature | Max points | How it is earned |
|---|---|---|
| Energy | 3.5 | closeness to the target |
| Mood | 3.0 | +3.0 exact match, +1.5 related mood (e.g. chill / relaxed), else 0 |
| Acousticness | 2.0 | closeness to 0.8 (likes acoustic) or 0.2 (does not) |
| Genre | 1.5 | all-or-nothing exact match |
| Valence, instrumentalness, release year, speechiness | 1.0, 0.5, 0.5, 0.25 | optional; only counted if the user supplies a target |

- Closeness is linear and hits zero at a gap of 0.5: `max(0, 1 - |song_value - target| / 0.5)`
- `release_year` closeness is normalised by the span 1960 to 2025: `1 - |year gap| / 65`
- Mood outweighs genre because genre is a coarse label ("pop" vs "indie pop" counts as a total miss, and most genres have one song), while mood describes how a song feels
- Features the user did not specify are skipped, so points available shrinks to match

Ranking Rule (list of songs): score every song, sort from highest to lowest, and return the top `k` with an explanation of why each one matched.

### Algorithm Recipe (finalized)

For one song and one user profile:

1. **Energy (up to +3.5):** `max(0, 1 - |song.energy - target| / 0.5) × 3.5`
2. **Mood (up to +3.0):** +3.0 for an exact match, +1.5 if the moods are related (chill/relaxed/focused/laid-back, intense/aggressive, happy/euphoric, sad/melancholic/moody), otherwise 0
3. **Acousticness (up to +2.0):** closeness to 0.8 if the user likes acoustic, 0.2 if not, using the same closeness formula as energy
4. **Genre (up to +1.5):** +1.5 for an exact match, otherwise 0
5. **Optional extras:** valence (1.0), instrumentalness (0.5), release year (0.5), speechiness (0.25), added only if the user supplied that target
6. **Normalize:** `score = points earned / points available`, where unsupplied preferences are left out of "available"
7. **Rank:** repeat for every song, sort descending, return the top `k`

Core features total 10 points (energy 35%, mood 30%, acousticness 20%, genre 15%).

**Example profile:** `{"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}`

| Rank | Song | Score | Why |
|---|---|---|---|
| 1 | Sunrise City | 0.98 | genre, mood and energy all match |
| 2 | Rooftop Lights | 0.76 | mood matches, genre is "indie pop" so it earns 0 genre points |
| 3 | Gym Hero | 0.55 | genre matches, mood is "intense" |
| 4 | Laser Cathedral | 0.53 | "euphoric" is related to "happy" (half mood credit) |

### Expected Biases and Limitations

- **Mood and energy dominate (65% of the points).** A song with the right vibe but a different genre can beat a same-genre song with the wrong vibe. That is intended, but it can bury a song a genre-loyal user would love.
- **Genre is all-or-nothing.** "pop" vs "indie pop" scores as a complete miss, and 14 of 16 genres have only one song, so genre barely separates songs and the near-misses get no credit.
- **The mood similarity list is hand-written.** Only a few mood pairs earn partial credit, and it reflects my judgment of which moods are "close". Moods outside the list (romantic, nostalgic, confident) can only match exactly.
- **Tiny, uneven catalog.** With 18 songs, lofi has 3 entries and most genres have 1, so lofi, pop and high-energy users get more varied results than users who like classical or reggae.
- **Acoustic preference is a yes/no switch.** It maps to a fixed 0.8 or 0.2 target, so "somewhat acoustic" users are not represented.
- **No history or diversity.** Nothing penalizes recommending near-identical songs (e.g. three lofi tracks in a row), and nothing learns from skips or replays.
- **Ignored features.** `tempo_bpm` and `danceability` are not scored, so a user who cares mainly about danceability is not served well.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python -m src.main` for the default pop / happy profile:

```
Loaded songs: 18

================================================================
                      TOP RECOMMENDATIONS                       
================================================================
Profile: genre=pop, mood=happy, energy=0.8, likes_acoustic=False

1. Sunrise City by Neon Echo
   Score: 0.98 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.80 (+3.36)
     - mood matches (happy) (+3.00)
     - acousticness 0.18 fits non-acoustic taste (+1.92)
     - genre matches (pop) (+1.50)

2. Rooftop Lights by Indigo Parade
   Score: 0.76 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.80 (+3.22)
     - mood matches (happy) (+3.00)
     - acousticness 0.35 fits non-acoustic taste (+1.40)
     - genre differs (indie pop) (+0.00)

3. Gym Hero by Max Pulse
   Score: 0.55 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.80 (+2.59)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 fits non-acoustic taste (+1.40)
     - genre matches (pop) (+1.50)

4. Laser Cathedral by Pulse Theory
   Score: 0.53 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.80 (+2.45)
     - mood is close (euphoric) (+1.50)
     - acousticness 0.03 fits non-acoustic taste (+1.32)
     - genre differs (edm) (+0.00)

5. Night Drive Loop by Neon Echo
   Score: 0.51 / 1.00   [synthwave | moody]
   Why:
     - energy 0.75 vs target 0.80 (+3.15)
     - mood differs (moody) (+0.00)
     - acousticness 0.22 fits non-acoustic taste (+1.92)
     - genre differs (synthwave) (+0.00)

----------------------------------------------------------------
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



