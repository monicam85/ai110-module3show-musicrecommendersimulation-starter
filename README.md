# 🎵 Music Recommender Simulation

## Project Summary

VibeScorecard is a small, explainable content-based music recommender. It loads 18 songs from `data/songs.csv`, scores every song against a listener's stated taste (genre, mood, energy and acoustic feel, plus a few optional extras) with a weighted point recipe, and prints the top five with a plain-language list of the points each one earned. Related moods and genres earn partial credit, and a small penalty keeps one artist or one cluster of similar songs from filling the list.

I tested it on 14 profiles (three ordinary tastes and eleven adversarial or edge cases), ran four experiments that change one scoring rule at a time, and wrote up what I found: the weights mattered less than the tiny, lopsided catalog, and the system gives confident-looking lists even when no song fits a listener's taste. See the [model card](model_card.md) for the full evaluation, limitations and bias analysis.

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
- `likes_acoustic`: whether the user prefers acoustic sound (true/false, or "yes"/"no"), treated as a target acousticness of 0.8 or 0.2. Instead, `acousticness` can be given as a 0-1 number and is used directly as the target. Unrecognised values such as `"maybe"` raise a `ValueError`

The function-based version (`recommend_songs`) also accepts optional `valence`, `instrumentalness` and `speechiness` targets (0 to 1) and a `release_year` target.

### Scoring Rule and Ranking Rule

Scoring Rule (one song): each feature earns points, and `score = points earned / points available`, giving a value from 0 to 1.

| Feature | Max points | How it is earned |
|---|---|---|
| Energy | 3.5 | closeness to the target |
| Mood | 3.0 | +3.0 exact match; related mood earns a graded share from `MOOD_SIMILARITY` (0.9 for intense/aggressive and sad/melancholic, 0.6-0.7 for the rest), else 0 |
| Acousticness | 2.0 | closeness to the `acousticness` target, or to 0.8 / 0.2 from `likes_acoustic` |
| Genre | 1.5 | exact match = full, related genre (e.g. rock and metal) = half, otherwise 0 |
| Valence, instrumentalness, release year, speechiness | 1.0, 0.5, 0.5, 0.25 | optional; only counted if the user supplies a target |

- Closeness is linear and hits zero at a gap of 0.5: `max(0, 1 - |song_value - target| / 0.5)`
- `release_year` closeness is normalised by the span 1960 to 2025: `1 - |year gap| / 65`
- Mood outweighs genre because genre is a coarse label ("pop" vs "indie pop" counts as a total miss, and most genres have one song), while mood describes how a song feels
- Features the user did not specify are skipped, so points available shrinks to match

Ranking Rule (list of songs): score every song, sort from highest to lowest, and return the top `k` with an explanation of why each one matched.

### Algorithm Recipe (finalized)

For one song and one user profile:

1. **Energy (up to +3.5):** `max(0, 1 - |song.energy - target| / 0.5) × 3.5`
2. **Mood (up to +3.0):** +3.0 for an exact match; related moods earn a graded share of the points: intense/aggressive and sad/melancholic 0.9, chill/relaxed and relaxed/laid-back 0.7, chill/focused, chill/laid-back, happy/euphoric and moody/melancholic 0.6; otherwise 0
3. **Acousticness (up to +2.0):** closeness to the user's numeric `acousticness` target (or 0.8 / 0.2 from `likes_acoustic`), using the same closeness formula as energy
4. **Genre (up to +1.5):** +1.5 for an exact match, +0.75 for a related genre (`RELATED_GENRES`), otherwise 0
5. **Optional extras:** valence (1.0), instrumentalness (0.5), release year (0.5), speechiness (0.25), added only if the user supplied that target
6. **Normalize:** `score = points earned / points available`, where unsupplied preferences are left out of "available"
7. **Rank:** repeat for every song, sort descending, return the top `k`

Core features total 10 points (energy 35%, mood 30%, acousticness 20%, genre 15%).

**Example profile:** `{"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}`

| Rank | Song | Score | Why |
|---|---|---|---|
| 1 | Sunrise City | 0.98 | genre, mood and energy all match |
| 2 | Rooftop Lights | 0.84 | mood matches, genre "indie pop" is related to "pop" (half genre credit) |
| 3 | Laser Cathedral | 0.63 | "euphoric" is related to "happy" (0.6 mood credit) and "edm" to "pop" (half genre credit) |
| 4 | Gym Hero | 0.55 | genre matches, mood is "intense", but it is the 4th high-energy song so it is nudged down |

### Expected Biases and Limitations

- **Mood and energy dominate (65% of the points).** A song with the right vibe but a different genre can beat a same-genre song with the wrong vibe. That is intended, but it can bury a song a genre-loyal user would love.
- **Genre similarity is hand-written.** Related genres (rock/metal, pop/indie pop, ...) get half credit, but only for the pairs listed in `RELATED_GENRES`; every other pair is still a complete miss, and 14 of 16 genres have only one song.
- **The mood similarity list is hand-written.** Only a few mood pairs earn partial credit, and it reflects my judgment of which moods are "close". Moods outside the list (romantic, nostalgic, confident) can only match exactly.
- **Tiny, uneven catalog.** With 18 songs, lofi has 3 entries and most genres have 1, so lofi, pop and high-energy users get more varied results than users who like classical or reggae.
- **Diversity is a soft penalty, not a guarantee.** After scoring, the list is re-picked greedily: each already-chosen song by the same artist costs a candidate 0.20, and each from the same sonic cluster (high-energy / mellow-acoustic / mid-tempo) costs 0.05. A clearly better song is never blocked, but with 18 songs a user whose taste fills one cluster still sees mostly that cluster, and reported scores can be slightly out of order after a repeat is pushed down. (An earlier hard cap of 3 per cluster forced low-scoring fillers like "Island Breeze" into many lists, so I replaced it.)
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

## Scoring Modes

The same song list can be ranked in four ways. Each mode changes how many points each feature is worth. The scoring code is the same for all of them (a simple Strategy pattern).

| Mode | Idea | Core weights (energy / mood / acoustic / genre) |
|---|---|---|
| `balanced` (default) | the original recipe | 3.5 / 3.0 / 2.0 / 1.5 |
| `genre-first` | genre counts most | 2.5 / 2.0 / 1.5 / 5.0 |
| `mood-first` | mood counts most | 2.5 / 5.0 / 1.5 / 1.0 |
| `energy-focused` | energy counts most | 6.0 / 2.0 / 1.5 / 0.5 |

Run a single mode, or compare all of them:

```
python -m src.main --mode mood-first
python -m src.main --compare
```

The default run (`python -m src.main`) is unchanged and uses `balanced`.

**What the comparison shows** (top song for four profiles, from `--compare`):

| Profile | balanced | genre-first | mood-first | energy-focused |
|---|---|---|---|---|
| High-Energy Pop (2nd song) | Rooftop Lights | **Gym Hero** | Rooftop Lights | Rooftop Lights |
| Deep Intense Rock (2nd song) | Iron Tide | Iron Tide | **Gym Hero** | **Gym Hero** |
| Sad but high-energy folk (1st song) | Hollow Lantern | Hollow Lantern | Hollow Lantern | **Storm Runner** |
| Metal fan who wants chill (1st song) | Iron Tide | Iron Tide | **Midnight Coding** | Iron Tide |

- **Mode changes matter more than my weight experiments suggested.** Each mode flips at least one result.
- **`genre-first` brings "Gym Hero" up to second place for Happy Pop fans.** A heavy genre weight rewards any song in the listener's genre, even with the wrong mood.
- **`mood-first` puts a quiet lofi song first for a loud metal fan.** The mood "chill" outweighs the energy and genre.
- **`energy-focused` makes the sad folk fan's top song a rock song,** which ignores the mood they asked for.
- No mode fixes the underlying problem. The catalog is tiny, and the same few loud songs appear in most lists.

---

## Sample Recommendation Output

Output of `python -m src.main` for the default pop / happy profile:

```
Loaded songs: 18

================================================================
         TOP RECOMMENDATIONS: High-Energy Pop (sample)          
================================================================
Profile: genre=pop, mood=happy, energy=0.8, likes_acoustic=False

1. Sunrise City by Neon Echo
   Score: 0.98 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.80 (+3.36)
     - mood matches (happy) (+3.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre matches (pop) (+1.50)

2. Rooftop Lights by Indigo Parade
   Score: 0.84 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.80 (+3.22)
     - mood matches (happy) (+3.00)
     - acousticness 0.35 vs target 0.20 (+1.40)
     - genre is close (indie pop) (+0.75)

3. Laser Cathedral by Pulse Theory
   Score: 0.63 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.80 (+2.45)
     - mood is close (euphoric) (+1.80)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre is close (edm) (+0.75)

4. Gym Hero by Max Pulse
   Score: 0.55 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.80 (+2.59)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre matches (pop) (+1.50)

5. Velvet Hours by Amara Vale
   Score: 0.31 / 1.00   [r&b | romantic]
   Why:
     - energy 0.52 vs target 0.80 (+1.54)
     - mood differs (romantic) (+0.00)
     - acousticness 0.30 vs target 0.20 (+1.60)
     - genre differs (r&b) (+0.00)

----------------------------------------------------------------
```

---

## Profile Evaluation Output (top 5 per profile)

Raw terminal output of `python -m src.main` (18 songs, `k=5`) with the genre similarity map, graded mood similarity, numeric acousticness and the diversity penalty. The first three profiles are normal tastes; the rest are adversarial or edge-case profiles meant to trick the scoring logic.

### High-Energy Pop

```
================================================================
              TOP RECOMMENDATIONS: High-Energy Pop              
================================================================
Profile: genre=pop, mood=happy, energy=0.85, likes_acoustic=False

1. Sunrise City by Neon Echo
   Score: 0.97 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.85 (+3.29)
     - mood matches (happy) (+3.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre matches (pop) (+1.50)

2. Rooftop Lights by Indigo Parade
   Score: 0.80 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.85 (+2.87)
     - mood matches (happy) (+3.00)
     - acousticness 0.35 vs target 0.20 (+1.40)
     - genre is close (indie pop) (+0.75)

3. Laser Cathedral by Pulse Theory
   Score: 0.67 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.85 (+2.80)
     - mood is close (euphoric) (+1.80)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre is close (edm) (+0.75)

4. Gym Hero by Max Pulse
   Score: 0.58 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.85 (+2.94)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre matches (pop) (+1.50)

5. Velvet Hours by Amara Vale
   Score: 0.28 / 1.00   [r&b | romantic]
   Why:
     - energy 0.52 vs target 0.85 (+1.19)
     - mood differs (romantic) (+0.00)
     - acousticness 0.30 vs target 0.20 (+1.60)
     - genre differs (r&b) (+0.00)

----------------------------------------------------------------
```

### Chill Lofi

```
================================================================
                TOP RECOMMENDATIONS: Chill Lofi                 
================================================================
Profile: genre=lofi, mood=chill, energy=0.35, likes_acoustic=True

1. Library Rain by Paper Lanterns
   Score: 0.98 / 1.00   [lofi | chill]
   Why:
     - energy 0.35 vs target 0.35 (+3.50)
     - mood matches (chill) (+3.00)
     - acousticness 0.86 vs target 0.80 (+1.76)
     - genre matches (lofi) (+1.50)

2. Midnight Coding by LoRoom
   Score: 0.91 / 1.00   [lofi | chill]
   Why:
     - energy 0.42 vs target 0.35 (+3.01)
     - mood matches (chill) (+3.00)
     - acousticness 0.71 vs target 0.80 (+1.64)
     - genre matches (lofi) (+1.50)

3. Spacewalk Thoughts by Orbit Bloom
   Score: 0.83 / 1.00   [ambient | chill]
   Why:
     - energy 0.28 vs target 0.35 (+3.01)
     - mood matches (chill) (+3.00)
     - acousticness 0.92 vs target 0.80 (+1.52)
     - genre is close (ambient) (+0.75)

4. Coffee Shop Stories by Slow Stereo
   Score: 0.78 / 1.00   [jazz | relaxed]
   Why:
     - energy 0.37 vs target 0.35 (+3.36)
     - mood is close (relaxed) (+2.10)
     - acousticness 0.89 vs target 0.80 (+1.64)
     - genre is close (jazz) (+0.75)

5. Focus Flow by LoRoom
   Score: 0.84 / 1.00   [lofi | focused]
   Why:
     - energy 0.40 vs target 0.35 (+3.15)
     - mood is close (focused) (+1.80)
     - acousticness 0.78 vs target 0.80 (+1.92)
     - genre matches (lofi) (+1.50)

----------------------------------------------------------------
```

### Deep Intense Rock

```
================================================================
             TOP RECOMMENDATIONS: Deep Intense Rock             
================================================================
Profile: genre=rock, mood=intense, energy=0.92, likes_acoustic=False

1. Storm Runner by Voltline
   Score: 0.95 / 1.00   [rock | intense]
   Why:
     - energy 0.91 vs target 0.92 (+3.43)
     - mood matches (intense) (+3.00)
     - acousticness 0.10 vs target 0.20 (+1.60)
     - genre matches (rock) (+1.50)

2. Iron Tide by Black Anvil
   Score: 0.80 / 1.00   [metal | aggressive]
   Why:
     - energy 0.97 vs target 0.92 (+3.15)
     - mood is close (aggressive) (+2.70)
     - acousticness 0.04 vs target 0.20 (+1.36)
     - genre is close (metal) (+0.75)

3. Gym Hero by Max Pulse
   Score: 0.78 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.92 (+3.43)
     - mood matches (intense) (+3.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre differs (pop) (+0.00)

4. Sunrise City by Neon Echo
   Score: 0.47 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.92 (+2.80)
     - mood differs (happy) (+0.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre differs (pop) (+0.00)

5. Laser Cathedral by Pulse Theory
   Score: 0.46 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.92 (+3.29)
     - mood differs (euphoric) (+0.00)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre differs (edm) (+0.00)

----------------------------------------------------------------
```

### Conflicted (sad but high-energy)

```
================================================================
     TOP RECOMMENDATIONS: Conflicted (sad but high-energy)      
================================================================
Profile: genre=folk, mood=sad, energy=0.9, likes_acoustic=True

1. Hollow Lantern by Wren & Pine
   Score: 0.62 / 1.00   [folk | sad]
   Why:
     - energy 0.30 vs target 0.90 (+0.00)
     - mood matches (sad) (+3.00)
     - acousticness 0.88 vs target 0.80 (+1.68)
     - genre matches (folk) (+1.50)

2. Winter Nocturne by Elise Harmon
   Score: 0.40 / 1.00   [classical | melancholic]
   Why:
     - energy 0.18 vs target 0.90 (+0.00)
     - mood is close (melancholic) (+2.70)
     - acousticness 0.97 vs target 0.80 (+1.32)
     - genre differs (classical) (+0.00)

3. Rooftop Lights by Indigo Parade
   Score: 0.35 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.90 (+2.52)
     - mood differs (happy) (+0.00)
     - acousticness 0.35 vs target 0.80 (+0.20)
     - genre is close (indie pop) (+0.75)

4. Storm Runner by Voltline
   Score: 0.34 / 1.00   [rock | intense]
   Why:
     - energy 0.91 vs target 0.90 (+3.43)
     - mood differs (intense) (+0.00)
     - acousticness 0.10 vs target 0.80 (+0.00)
     - genre differs (rock) (+0.00)

5. Dust Road Home by Hollis Creek
   Score: 0.36 / 1.00   [country | nostalgic]
   Why:
     - energy 0.55 vs target 0.90 (+1.05)
     - mood differs (nostalgic) (+0.00)
     - acousticness 0.74 vs target 0.80 (+1.76)
     - genre is close (country) (+0.75)

----------------------------------------------------------------
```

### Adversarial: metal fan who wants chill

```
================================================================
  TOP RECOMMENDATIONS: Adversarial: metal fan who wants chill   
================================================================
Profile: genre=metal, mood=chill, energy=0.97, likes_acoustic=False

1. Iron Tide by Black Anvil
   Score: 0.64 / 1.00   [metal | aggressive]
   Why:
     - energy 0.97 vs target 0.97 (+3.50)
     - mood differs (aggressive) (+0.00)
     - acousticness 0.04 vs target 0.20 (+1.36)
     - genre matches (metal) (+1.50)

2. Storm Runner by Voltline
   Score: 0.54 / 1.00   [rock | intense]
   Why:
     - energy 0.91 vs target 0.97 (+3.08)
     - mood differs (intense) (+0.00)
     - acousticness 0.10 vs target 0.20 (+1.60)
     - genre is close (rock) (+0.75)

3. Laser Cathedral by Pulse Theory
   Score: 0.47 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.97 (+3.36)
     - mood differs (euphoric) (+0.00)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre differs (edm) (+0.00)

4. Island Breeze by Sun Rhythm
   Score: 0.36 / 1.00   [reggae | laid-back]
   Why:
     - energy 0.58 vs target 0.97 (+0.77)
     - mood is close (laid-back) (+1.80)
     - acousticness 0.45 vs target 0.20 (+1.00)
     - genre differs (reggae) (+0.00)

5. Gym Hero by Max Pulse
   Score: 0.46 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.97 (+3.22)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre differs (pop) (+0.00)

----------------------------------------------------------------
```

### Adversarial: acoustic-loving EDM fan

```
================================================================
   TOP RECOMMENDATIONS: Adversarial: acoustic-loving EDM fan    
================================================================
Profile: genre=edm, mood=euphoric, energy=0.95, likes_acoustic=True

1. Laser Cathedral by Pulse Theory
   Score: 0.80 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.95 (+3.50)
     - mood matches (euphoric) (+3.00)
     - acousticness 0.03 vs target 0.80 (+0.00)
     - genre matches (edm) (+1.50)

2. Sunrise City by Neon Echo
   Score: 0.51 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.95 (+2.59)
     - mood is close (happy) (+1.80)
     - acousticness 0.18 vs target 0.80 (+0.00)
     - genre is close (pop) (+0.75)

3. Rooftop Lights by Indigo Parade
   Score: 0.42 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.95 (+2.17)
     - mood is close (happy) (+1.80)
     - acousticness 0.35 vs target 0.80 (+0.20)
     - genre differs (indie pop) (+0.00)

4. Gym Hero by Max Pulse
   Score: 0.41 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.95 (+3.36)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 vs target 0.80 (+0.00)
     - genre is close (pop) (+0.75)

5. Dust Road Home by Hollis Creek
   Score: 0.25 / 1.00   [country | nostalgic]
   Why:
     - energy 0.55 vs target 0.95 (+0.70)
     - mood differs (nostalgic) (+0.00)
     - acousticness 0.74 vs target 0.80 (+1.76)
     - genre differs (country) (+0.00)

----------------------------------------------------------------
```

### Adversarial: empty profile

```
================================================================
        TOP RECOMMENDATIONS: Adversarial: empty profile         
================================================================
Profile: 

1. Sunrise City by Neon Echo
   Score: 0.00 / 1.00   [pop | happy]
   Why:
     - no preferences provided

2. Midnight Coding by LoRoom
   Score: 0.00 / 1.00   [lofi | chill]
   Why:
     - no preferences provided

3. Velvet Hours by Amara Vale
   Score: 0.00 / 1.00   [r&b | romantic]
   Why:
     - no preferences provided

4. Storm Runner by Voltline
   Score: 0.00 / 1.00   [rock | intense]
   Why:
     - no preferences provided

5. Library Rain by Paper Lanterns
   Score: 0.00 / 1.00   [lofi | chill]
   Why:
     - no preferences provided

----------------------------------------------------------------
```

### Adversarial: wrong-case genre and mood

```
================================================================
  TOP RECOMMENDATIONS: Adversarial: wrong-case genre and mood   
================================================================
Profile: genre=Pop, mood=Happy, energy=0.8, likes_acoustic=False

1. Sunrise City by Neon Echo
   Score: 0.53 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.80 (+3.36)
     - mood differs (happy) (+0.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre differs (pop) (+0.00)

2. Concrete Verses by Kid Meridian
   Score: 0.50 / 1.00   [hip-hop | confident]
   Why:
     - energy 0.78 vs target 0.80 (+3.36)
     - mood differs (confident) (+0.00)
     - acousticness 0.12 vs target 0.20 (+1.68)
     - genre differs (hip-hop) (+0.00)

3. Rooftop Lights by Indigo Parade
   Score: 0.46 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 0.80 (+3.22)
     - mood differs (happy) (+0.00)
     - acousticness 0.35 vs target 0.20 (+1.40)
     - genre differs (indie pop) (+0.00)

4. Velvet Hours by Amara Vale
   Score: 0.31 / 1.00   [r&b | romantic]
   Why:
     - energy 0.52 vs target 0.80 (+1.54)
     - mood differs (romantic) (+0.00)
     - acousticness 0.30 vs target 0.20 (+1.60)
     - genre differs (r&b) (+0.00)

5. Storm Runner by Voltline
   Score: 0.43 / 1.00   [rock | intense]
   Why:
     - energy 0.91 vs target 0.80 (+2.73)
     - mood differs (intense) (+0.00)
     - acousticness 0.10 vs target 0.20 (+1.60)
     - genre differs (rock) (+0.00)

----------------------------------------------------------------
```

### Adversarial: likes_acoustic='no'

```
================================================================
     TOP RECOMMENDATIONS: Adversarial: likes_acoustic='no'      
================================================================
Profile: genre=rock, mood=intense, energy=0.9, likes_acoustic=no

1. Storm Runner by Voltline
   Score: 0.95 / 1.00   [rock | intense]
   Why:
     - energy 0.91 vs target 0.90 (+3.43)
     - mood matches (intense) (+3.00)
     - acousticness 0.10 vs target 0.20 (+1.60)
     - genre matches (rock) (+1.50)

2. Iron Tide by Black Anvil
   Score: 0.78 / 1.00   [metal | aggressive]
   Why:
     - energy 0.97 vs target 0.90 (+3.01)
     - mood is close (aggressive) (+2.70)
     - acousticness 0.04 vs target 0.20 (+1.36)
     - genre is close (metal) (+0.75)

3. Gym Hero by Max Pulse
   Score: 0.77 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 0.90 (+3.29)
     - mood matches (intense) (+3.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre differs (pop) (+0.00)

4. Sunrise City by Neon Echo
   Score: 0.49 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 0.90 (+2.94)
     - mood differs (happy) (+0.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre differs (pop) (+0.00)

5. Laser Cathedral by Pulse Theory
   Score: 0.45 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 0.90 (+3.15)
     - mood differs (euphoric) (+0.00)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre differs (edm) (+0.00)

----------------------------------------------------------------
```

### Numeric acousticness=0.5

```
================================================================
         TOP RECOMMENDATIONS: Numeric acousticness=0.5          
================================================================
Profile: genre=jazz, mood=relaxed, energy=0.5, acousticness=0.5

1. Coffee Shop Stories by Slow Stereo
   Score: 0.75 / 1.00   [jazz | relaxed]
   Why:
     - energy 0.37 vs target 0.50 (+2.59)
     - mood matches (relaxed) (+3.00)
     - acousticness 0.89 vs target 0.50 (+0.44)
     - genre matches (jazz) (+1.50)

2. Island Breeze by Sun Rhythm
   Score: 0.68 / 1.00   [reggae | laid-back]
   Why:
     - energy 0.58 vs target 0.50 (+2.94)
     - mood is close (laid-back) (+2.10)
     - acousticness 0.45 vs target 0.50 (+1.80)
     - genre differs (reggae) (+0.00)

3. Midnight Coding by LoRoom
   Score: 0.69 / 1.00   [lofi | chill]
   Why:
     - energy 0.42 vs target 0.50 (+2.94)
     - mood is close (chill) (+2.10)
     - acousticness 0.71 vs target 0.50 (+1.16)
     - genre is close (lofi) (+0.75)

4. Library Rain by Paper Lanterns
   Score: 0.59 / 1.00   [lofi | chill]
   Why:
     - energy 0.35 vs target 0.50 (+2.45)
     - mood is close (chill) (+2.10)
     - acousticness 0.86 vs target 0.50 (+0.56)
     - genre is close (lofi) (+0.75)

5. Velvet Hours by Amara Vale
   Score: 0.46 / 1.00   [r&b | romantic]
   Why:
     - energy 0.52 vs target 0.50 (+3.36)
     - mood differs (romantic) (+0.00)
     - acousticness 0.30 vs target 0.50 (+1.20)
     - genre differs (r&b) (+0.00)

----------------------------------------------------------------
```

### Adversarial: genre-only (lofi)

```
================================================================
      TOP RECOMMENDATIONS: Adversarial: genre-only (lofi)       
================================================================
Profile: genre=lofi

1. Midnight Coding by LoRoom
   Score: 1.00 / 1.00   [lofi | chill]
   Why:
     - genre matches (lofi) (+1.50)

2. Library Rain by Paper Lanterns
   Score: 1.00 / 1.00   [lofi | chill]
   Why:
     - genre matches (lofi) (+1.50)

3. Focus Flow by LoRoom
   Score: 1.00 / 1.00   [lofi | focused]
   Why:
     - genre matches (lofi) (+1.50)

4. Spacewalk Thoughts by Orbit Bloom
   Score: 0.50 / 1.00   [ambient | chill]
   Why:
     - genre is close (ambient) (+0.75)

5. Coffee Shop Stories by Slow Stereo
   Score: 0.50 / 1.00   [jazz | relaxed]
   Why:
     - genre is close (jazz) (+0.75)

----------------------------------------------------------------
```

### Adversarial: energy out of range (1.5)

```
================================================================
  TOP RECOMMENDATIONS: Adversarial: energy out of range (1.5)   
================================================================
Profile: genre=pop, mood=happy, energy=1.5, likes_acoustic=False

1. Sunrise City by Neon Echo
   Score: 0.64 / 1.00   [pop | happy]
   Why:
     - energy 0.82 vs target 1.50 (+0.00)
     - mood matches (happy) (+3.00)
     - acousticness 0.18 vs target 0.20 (+1.92)
     - genre matches (pop) (+1.50)

2. Rooftop Lights by Indigo Parade
   Score: 0.52 / 1.00   [indie pop | happy]
   Why:
     - energy 0.76 vs target 1.50 (+0.00)
     - mood matches (happy) (+3.00)
     - acousticness 0.35 vs target 0.20 (+1.40)
     - genre is close (indie pop) (+0.75)

3. Laser Cathedral by Pulse Theory
   Score: 0.39 / 1.00   [edm | euphoric]
   Why:
     - energy 0.95 vs target 1.50 (+0.00)
     - mood is close (euphoric) (+1.80)
     - acousticness 0.03 vs target 0.20 (+1.32)
     - genre is close (edm) (+0.75)

4. Velvet Hours by Amara Vale
   Score: 0.16 / 1.00   [r&b | romantic]
   Why:
     - energy 0.52 vs target 1.50 (+0.00)
     - mood differs (romantic) (+0.00)
     - acousticness 0.30 vs target 0.20 (+1.60)
     - genre differs (r&b) (+0.00)

5. Gym Hero by Max Pulse
   Score: 0.29 / 1.00   [pop | intense]
   Why:
     - energy 0.93 vs target 1.50 (+0.00)
     - mood differs (intense) (+0.00)
     - acousticness 0.05 vs target 0.20 (+1.40)
     - genre matches (pop) (+1.50)

----------------------------------------------------------------
```

### Profiles rejected with an error

```
Adversarial: likes_acoustic='maybe': CRASHED with ValueError: likes_acoustic must be a bool or yes/no, got 'maybe'
Adversarial: energy='high' (wrong type): CRASHED with TypeError: unsupported operand type(s) for -: 'float' and 'str'
```

---

## Experiments You Tried

### Experiment 1: lower the mood weight from 3.0 to 2.5

**Question:** mood (3.0 points) beat genre in the rock profile, so "Gym Hero" (pop, intense) outranked "Iron Tide" (metal, aggressive). Does a smaller mood weight fix that?

**Method:** one change, `POINTS["mood"] = 2.5` (core total 9.5, so scores are rescaled), all other weights unchanged. I compared the top 5 for the 12 profiles that run without error (14 total, 2 of which are rejected by design) against the baseline. The comparison ran in a scratch script and the project code was not edited.

**Results:** the lists barely moved.

| Profile | Change at mood = 2.5 |
|---|---|
| Chill Lofi, Deep Intense Rock, Conflicted, EDM, empty, wrong-case, `likes_acoustic='no'`, genre-only, energy 1.5 | identical top-5 order |
| High-Energy Pop | slot 5 changes from "Velvet Hours" (0.28) to "Concrete Verses" (0.49); "Gym Hero" rises 0.58 to 0.61 |
| Metal fan who wants chill | slots 4-5 swap ("Gym Hero" 0.49 now above "Island Breeze" 0.32) |
| Numeric acousticness=0.5 | slots 4-5 swap ("Velvet Hours" now above "Library Rain") |

**What I learned:**
- **It did not fix "Gym Hero" over "Iron Tide".** For the rock profile "Gym Hero" earns 3.43 (energy) + 1.40 (acoustic) + the full mood weight, while "Iron Tide" earns 3.15 + 1.36 + 0.75 (half genre) + half the mood weight. The order only flips when mood is worth less than about 0.86 points, at which point mood would hardly matter at all. The real gap is that an exact mood match counts for much more than a *related* one, not that mood is too heavy.
- **Energy and acousticness decide most rankings.** Together they are 5.5 of 10 points and continuous, so they do most of the sorting. Mood changes the order mainly when two songs are otherwise close.
- **The one meaningful gain** was in slot 5 for the pop profile, where a weaker mood weight let a better energy fit replace a filler song.
- **Conclusion:** I kept mood at 3.0. A better fix for the rock case would be to raise the half credit for related moods (for example intense and aggressive) from 0.5 to about 0.75, or to add more songs so near-matches exist.

---

### Experiment 2: weight shift (energy x2, genre /2)

**Change:** in `POINTS`, energy 3.5 to 7.0 and genre 1.5 to 0.75. Core total becomes 12.75 (energy 55%, mood 24%, acousticness 16%, genre 6%). I ran `python -m src.main` and compared against the baseline run, then reverted the weights.

**Is the math still valid?** Yes. Scores are points earned divided by points available, so they stay in 0-1 whatever the weights add up to. I checked 216 profile/song scores (min 0.000, max 1.000), that a perfect match scores exactly 1.0 and the worst possible match 0.0, and that the points listed in each "Why" add up to the score (the only differences were display rounding, e.g. 0.375 shown as 0.38). All 11 tests passed.

**What changed:** 9 of 12 profiles got a different top 5 (2 were identical, the empty profile tied as before); the #1 song changed for only one.

| Profile | Baseline | Energy x2, genre /2 |
|---|---|---|
| Conflicted (folk, sad, 0.9) | "Hollow Lantern" 0.62 first | "Storm Runner" 0.54 first; "Hollow Lantern" falls to 3rd (0.43) |
| Deep Intense Rock | "Gym Hero" 0.78 vs "Iron Tide" 0.68 | gap widens: 0.88 vs 0.75 |
| Chill Lofi | "Focus Flow" stays in the top 5 | "Focus Flow" drops out for "Island Breeze" (0.46) |
| Energy out of range (1.5) | "Sunrise City" 0.64 | 0.44 (energy is now worth more, and nothing can satisfy it) |
| Repetition | the 5 high-energy songs fill 29 of 60 slots | 34 of 60 |

**Verdict: different, not more accurate.**
- Energy now behaves almost like a sort key, so every high-energy user sees the same few songs more often.
- The sad folk fan asked for acoustic, sad music and now gets rock first. Their request is contradictory, but ignoring three of four stated preferences is not better.
- The genre-similarity work is nearly wasted at 6% weight: rock and metal now differ by 0.375 points.
- The experiment made the "Gym Hero" over "Iron Tide" problem worse, which confirms that energy and mood weights are not the cause. The lever that matters is how much credit a *related* mood or genre earns.
- Only the pop and rock lists look slightly better, because the more precise energy fit pushed weaker fillers down.

I kept the baseline weights.

---

### Experiment 3: raise related-mood credit from 0.5 to 0.75

**Change:** `PARTIAL_MOOD_CREDIT = 0.75` (was 0.5), all weights unchanged, so a related mood such as intense/aggressive earns 2.25 of the 3.0 mood points instead of 1.5. Run in a scratch script; project code not edited. I also swept 0.85, 0.9 and 1.0 on the rock profile.

**Hypothesis:** this would put "Iron Tide" (metal, aggressive) above "Gym Hero" (pop, intense) for the rock fan.

**Result: the hypothesis was wrong at 0.75.**

| Profile | Change at 0.75 |
|---|---|
| High-Energy Pop, Chill Lofi, Deep Intense Rock, `likes_acoustic='no'`, acousticness=0.5, energy 1.5 | same order, scores shift slightly |
| Rock: "Iron Tide" | 0.68 to 0.75, but "Gym Hero" stays at 0.78, so it is still second |
| Conflicted, metal-wants-chill, acoustic EDM | slots 3-5 reorder (e.g. "Rooftop Lights" 0.46 moves above "Gym Hero" 0.41 for the EDM fan) |
| #1 song | unchanged for every profile |

**Rock profile as the credit rises (top 3):**

| Related-mood credit | Storm Runner | Gym Hero | Iron Tide |
|---|---|---|---|
| 0.50 | 0.95 | 0.78 | 0.68 |
| 0.75 | 0.95 | 0.78 | 0.75 |
| 0.85 | 0.95 | 0.78 | 0.78 (tie, "Gym Hero" wins on order) |
| 0.90 | 0.95 | 0.78 | 0.80 (flips) |
| 1.00 | 0.95 | 0.78 | 0.83 |

**What I learned:**
- "Gym Hero" earns a full 3.0 mood points; "Iron Tide" earns 3.15 + 1.36 + 0.75 (half genre) + 3.0 x credit. Working it out, the order only flips above about 0.85 credit.
- At 0.9 or more, "related" mood is nearly as good as "exact", so happy/euphoric or sad/melancholic would also be treated as almost identical. At 1.0 the pop profile ranks "Laser Cathedral" (euphoric) at 0.79, almost level with an exact-mood match, which is too generous.
- So one global credit value cannot fix a single pair without loosening all the others. I kept 0.5.
- **Better fix:** a graded similarity (e.g. intense/aggressive = 0.9, happy/euphoric = 0.6) instead of one number for every related pair, or more songs so closer matches exist.

---

### Experiment 4: graded mood similarity (kept)

**Change:** replaced the single "related mood = half credit" value with `MOOD_SIMILARITY`, a per-pair table: intense/aggressive 0.9, sad/melancholic 0.9, chill/relaxed 0.7, relaxed/laid-back 0.7, chill/focused 0.6, chill/laid-back 0.6, happy/euphoric 0.6, moody/melancholic 0.6. Weights unchanged. I added a test for it (12 tests pass) and compared `python -m src.main` against a fresh baseline run.

**Result: more accurate on the target case, with little collateral change.**

| Profile | Before | After |
|---|---|---|
| Deep Intense Rock | "Gym Hero" 0.78 second, "Iron Tide" 0.68 third | "Iron Tide" 0.80 now second, "Gym Hero" 0.78 third |
| Rock fan with `likes_acoustic='no'` | "Gym Hero" 0.77 above "Iron Tide" 0.66 | "Iron Tide" 0.78 above "Gym Hero" 0.77 |
| Acoustic-loving EDM fan | "Gym Hero" 0.41 third | "Rooftop Lights" (happy, 0.6 credit) 0.42 moves above it |
| Conflicted (folk, sad, 0.9) | "Hollow Lantern" first, "Rooftop Lights" second | "Hollow Lantern" still first; "Winter Nocturne" (melancholic, 0.9 credit) now second at 0.40 |
| High-Energy Pop, Chill Lofi, metal-wants-chill, acousticness=0.5, energy 1.5 | same order, scores shift by a few hundredths | |
| Empty, wrong-case, genre-only | identical | |

No #1 song changed for any profile, and the pop and lofi orderings did not move, which is what the single global 0.9 credit in Experiment 3 could not do.

**Caveats:**
- The 0.9 for intense/aggressive was picked knowing it had to exceed about 0.85 to fix the rock case, so this result is partly tuned to the test. I have no second dataset to check it against.
- All similarity values are my own judgements, not measured from listening data.
- Only moods that appear in the catalog are covered; any other pair still earns 0.

---

## Limitations and Risks

- **Tiny, lopsided catalog.** 18 invented songs; 13 of 15 genres and 11 of 14 moods have a single song, and the same five loud songs ("Sunrise City", "Gym Hero", "Laser Cathedral", "Storm Runner", "Iron Tide") fill 28 of the 60 top-5 slots across my 12 test profiles.
- **Energy and mood move together in the data.** Every sad, chill, relaxed or focused song is low energy, and every happy, intense, aggressive or euphoric song is high energy. A "sad but high-energy" listener gets a slow song first, with no warning that nothing fits both halves of their taste.
- **The energy rule treats extremes unevenly.** A gap of 0.5 earns nothing and the catalog spans only 0.18 to 0.97, so a listener who asks for energy 0.1 gets credit from 10 of 18 songs and a lower best score than a mid-range listener.
- **Exact-text matching.** "Pop" and "pop" are different to the system, so a capital letter silently drops the top score from 0.97 to 0.53.
- **Confident-looking scores on thin input.** A profile that only names a genre gives three songs a perfect 1.00, and an impossible energy such as 1.5 returns a normal-looking list.
- **It cannot tell songs apart beyond labels and numbers.** It does not understand lyrics, language, artist popularity or listening history, and it does not use tempo or danceability, so a workout pop song and a happy pop song look alike to it.
- **Hand-picked rules.** The weights and the similarity credits for related moods and genres are my own judgements, and one of them (intense and aggressive at 0.9) was tuned to a single test case.

The model card goes deeper on these in sections 4, 6 and 7.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

I learned that a recommender turns data into predictions through a chain of small choices that look like math but are really judgement calls: which song attributes count, how many points each is worth, how close is "close enough", and which moods and genres count as neighbors. Running experiments showed that changing the weights was usually the wrong lever; lowering the mood weight and doubling the energy weight left most top songs unchanged or made them worse, while giving each related mood pair its own credit fixed the rock list and a bigger catalog would help most. The "why" list behind every score was what made these problems visible, because I could see that "Gym Hero" kept appearing for happy pop fans by collecting energy, acoustic and genre points while earning zero for mood.

Bias and unfairness can show up in quiet ways in systems like this. A small catalog serves the tastes it happens to contain: listeners who want something the data lacks, such as sad high-energy songs or a genre with one track, get weak matches presented with the same confidence as strong ones. Features that move together in the data (mood and energy here) act like hidden rules, exact text matching penalises people for a capital letter, and a few loud songs end up in everyone's list. At a real app's scale, the same patterns could push everyone toward the most popular songs and leave out the people the data covers least.
