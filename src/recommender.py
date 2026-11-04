from typing import List, Dict, Tuple, Optional
import csv
from dataclasses import asdict, dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    instrumentalness: Optional[float] = None
    speechiness: Optional[float] = None
    release_year: Optional[int] = None

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_acousticness: Optional[float] = None  # 0-1; overrides likes_acoustic

# Scoring recipe, in points. Core features total 10 points:
#   energy +3.5 max, mood +3.0, acousticness +2.0, genre +1.5.
# Mood outweighs genre on purpose: in this catalog most genres have a single
# song, so a heavy genre weight would just pin the result to that one track.
# Optional extras only count when the user supplies that preference. Preferences
# the user did not supply (or features a song lacks) are skipped, and the final
# score is points earned / points available, a 0-1 value. Because of that
# division, the total does not need to be 10: any weights keep scores in 0-1.
POINTS = {
    "energy": 3.5,
    "mood": 3.0,
    "acousticness": 2.0,
    "genre": 1.5,
    "valence": 1.0,
    "instrumentalness": 0.5,
    "release_year": 0.5,
    "speechiness": 0.25,
}


@dataclass(frozen=True)
class ScoringMode:
    """
    One ranking strategy (Strategy pattern): a name plus the weights it changes.

    score_song asks the chosen mode for its weights and otherwise runs the same
    code, so adding a new strategy means adding one entry to MODES, not new logic.
    Weights a mode does not mention fall back to POINTS, which is looked up at
    call time so the balanced mode always follows the base recipe.
    """
    name: str
    description: str
    overrides: Dict[str, float]

    def weights(self) -> Dict[str, float]:
        """Returns the full weight table for this mode."""
        return {**POINTS, **self.overrides}


MODES: Dict[str, ScoringMode] = {
    mode.name: mode for mode in [
        ScoringMode("balanced", "the default recipe: energy, mood, acoustic feel, then genre", {}),
        ScoringMode("genre-first", "genre counts most; the rest only breaks ties",
                    {"genre": 5.0, "energy": 2.5, "mood": 2.0, "acousticness": 1.5}),
        ScoringMode("mood-first", "mood counts most; energy comes second",
                    {"mood": 5.0, "energy": 2.5, "acousticness": 1.5, "genre": 1.0}),
        ScoringMode("energy-focused", "energy counts most; mood and genre matter little",
                    {"energy": 6.0, "mood": 2.0, "acousticness": 1.5, "genre": 0.5}),
    ]
}


def get_mode(mode) -> ScoringMode:
    """Accepts a mode name or a ScoringMode; raises ValueError for an unknown name."""
    if isinstance(mode, ScoringMode):
        return mode
    if mode not in MODES:
        raise ValueError(f"unknown scoring mode {mode!r}; choose from {', '.join(MODES)}")
    return MODES[mode]

# Numeric closeness is linear and reaches 0 once the gap hits this tolerance,
# so a 0.5 energy gap earns nothing (plain 1 - |diff| would still give half).
TOLERANCE = 0.5

# release_year is normalised by this span so a year gap becomes a 0-1 distance.
YEAR_MIN, YEAR_MAX = 1960, 2025

# Near-miss moods earn graded partial credit (0-1 of the mood points) instead of
# zero. How close two moods feel differs by pair, so each pair has its own value;
# these are hand-picked judgements, not measured from data.
MOOD_SIMILARITY = {
    frozenset(pair): credit for pair, credit in [
        (("intense", "aggressive"), 0.9),     # nearly the same energy and attitude
        (("sad", "melancholic"), 0.9),        # same feeling, different intensity
        (("chill", "relaxed"), 0.7),
        (("relaxed", "laid-back"), 0.7),
        (("chill", "focused"), 0.6),          # both calm, but one is task-driven
        (("chill", "laid-back"), 0.6),
        (("happy", "euphoric"), 0.6),         # euphoric is a much bigger high
        (("moody", "melancholic"), 0.6),
    ]
}


# Near-miss genres earn half credit too, so a rock fan sees metal before pop.
PARTIAL_GENRE_CREDIT = 0.5
RELATED_GENRES = {
    frozenset(pair) for pair in [
        ("rock", "metal"), ("pop", "indie pop"), ("pop", "edm"),
        ("edm", "synthwave"), ("lofi", "ambient"), ("lofi", "jazz"),
        ("ambient", "classical"), ("hip-hop", "r&b"), ("folk", "country"),
        ("folk", "indie pop"), ("reggae", "r&b"),
    ]
}

# Preferred acousticness when the user only says whether they like acoustic music.
ACOUSTIC_TARGET_YES, ACOUSTIC_TARGET_NO = 0.8, 0.2

# Diversity penalties for the final top-k list (see _diversify). Each song already
# chosen by the same artist / from the same sonic cluster lowers a candidate's
# effective score by this much (on the 0-1 scale).
ARTIST_PENALTY = 0.20
CLUSTER_PENALTY = 0.05


def _closeness(a: float, b: float) -> float:
    """1.0 when equal, falling linearly to 0.0 at a gap of TOLERANCE."""
    return max(0.0, 1 - abs(a - b) / TOLERANCE)


def load_songs(csv_path: str) -> List[Dict]:
    """Loads songs from a CSV file, converting numeric columns to numbers."""
    int_cols = {"id", "release_year"}
    float_cols = {"energy", "tempo_bpm", "valence", "danceability", "acousticness",
                  "instrumentalness", "speechiness"}
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for col in int_cols:
                if row.get(col):
                    row[col] = int(row[col])
            for col in float_cols:
                if row.get(col):
                    row[col] = float(row[col])
            songs.append(row)
    return songs


def _acoustic_target(user_prefs: Dict) -> Optional[float]:
    """
    Returns the acousticness the user wants (0-1), or None if they gave no preference.

    An explicit "acousticness" number wins. Otherwise "likes_acoustic" is read as
    a yes/no. Strings such as "no" are parsed rather than treated as truthy, and
    anything unrecognisable raises ValueError instead of being silently guessed.
    """
    if "acousticness" in user_prefs:
        value = user_prefs["acousticness"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"acousticness must be a number from 0 to 1, got {value!r}")
        return float(value)
    if "likes_acoustic" not in user_prefs:
        return None
    likes = user_prefs["likes_acoustic"]
    if isinstance(likes, str):
        word = likes.strip().lower()
        if word in {"yes", "y", "true", "1"}:
            likes = True
        elif word in {"no", "n", "false", "0"}:
            likes = False
        else:
            raise ValueError(f"likes_acoustic must be a bool or yes/no, got {likes!r}")
    if not isinstance(likes, bool):
        raise ValueError(f"likes_acoustic must be a bool or yes/no, got {likes!r}")
    return ACOUSTIC_TARGET_YES if likes else ACOUSTIC_TARGET_NO


def _cluster(song: Dict) -> str:
    """Rough sonic neighbourhood of a song, used to keep a top-k list varied."""
    if song["energy"] >= 0.7:
        return "high-energy"
    if song["acousticness"] >= 0.6:
        return "mellow-acoustic"
    return "mid-tempo"


def _diversify(ranked: List[Tuple], k: int) -> List[Tuple]:
    """
    Greedily picks k entries from a best-first list, re-ranking as it goes.

    A candidate's effective score is its real score minus ARTIST_PENALTY for each
    song by the same artist already chosen and CLUSTER_PENALTY for each song from
    the same cluster already chosen. Unlike a hard cap, a clearly better song is
    never blocked, and a weak filler only gets in if it beats the penalised
    favourites. Reported scores stay the real ones, so they may not be strictly
    descending after a repeat is pushed down.
    """
    remaining = list(ranked)
    chosen: List[Tuple] = []
    while remaining and len(chosen) < k:
        def effective(item: Tuple) -> float:
            song, score = item[0], item[1]
            same_artist = sum(1 for c in chosen if c[0]["artist"] == song["artist"])
            same_cluster = sum(1 for c in chosen if _cluster(c[0]) == _cluster(song))
            return score - ARTIST_PENALTY * same_artist - CLUSTER_PENALTY * same_cluster
        # max() returns the first best item, so ties keep the original ranking.
        best = max(remaining, key=effective)
        remaining.remove(best)
        chosen.append(best)
    return chosen


def score_song(user_prefs: Dict, song: Dict, mode="balanced") -> Tuple[float, List[str]]:
    """
    Scores a song against user preferences on a 0-1 scale, using the weights of
    the chosen scoring mode (see MODES).

    Recognised pref keys: genre, mood, energy, valence, acousticness (0-1
    target) or likes_acoustic (bool), instrumentalness, speechiness,
    release_year.
    Numeric features earn points by closeness to the target (see _closeness);
    genre and mood are full credit on a match and half on a related one.
    Returns (score, reasons), where reasons list the points earned.
    """
    weights = get_mode(mode).weights()
    parts = []  # (max points, fraction earned, reason)

    def add(key: str, fraction: float, reason: str) -> None:
        """Records one feature's max points, fraction earned and reason string."""
        parts.append((weights[key], fraction, f"{reason} (+{weights[key] * fraction:.2f})"))

    if "energy" in user_prefs:
        add("energy", _closeness(song["energy"], user_prefs["energy"]),
            f"energy {song['energy']:.2f} vs target {user_prefs['energy']:.2f}")
    if "mood" in user_prefs:
        if song["mood"] == user_prefs["mood"]:
            add("mood", 1.0, f"mood matches ({song['mood']})")
        elif frozenset((song["mood"], user_prefs["mood"])) in MOOD_SIMILARITY:
            add("mood", MOOD_SIMILARITY[frozenset((song["mood"], user_prefs["mood"]))],
                f"mood is close ({song['mood']})")
        else:
            add("mood", 0.0, f"mood differs ({song['mood']})")
    acoustic_target = _acoustic_target(user_prefs)
    if acoustic_target is not None:
        add("acousticness", _closeness(song["acousticness"], acoustic_target),
            f"acousticness {song['acousticness']:.2f} vs target {acoustic_target:.2f}")
    if "genre" in user_prefs:
        if song["genre"] == user_prefs["genre"]:
            add("genre", 1.0, f"genre matches ({song['genre']})")
        elif frozenset((song["genre"], user_prefs["genre"])) in RELATED_GENRES:
            add("genre", PARTIAL_GENRE_CREDIT, f"genre is close ({song['genre']})")
        else:
            add("genre", 0.0, f"genre differs ({song['genre']})")
    if "valence" in user_prefs:
        add("valence", _closeness(song["valence"], user_prefs["valence"]),
            f"valence {song['valence']:.2f} vs target {user_prefs['valence']:.2f}")
    for key in ("instrumentalness", "speechiness"):
        if key in user_prefs and song.get(key) is not None:
            add(key, _closeness(song[key], user_prefs[key]),
                f"{key} {song[key]:.2f} vs target {user_prefs[key]:.2f}")
    if "release_year" in user_prefs and song.get("release_year") is not None:
        gap = abs(song["release_year"] - user_prefs["release_year"])
        add("release_year", max(0.0, 1 - gap / (YEAR_MAX - YEAR_MIN)),
            f"released {song['release_year']} vs target {user_prefs['release_year']}")

    available = sum(p for p, _, _ in parts)
    if available == 0:
        return 0.0, ["no preferences provided"]
    score = sum(p * f for p, f, _ in parts) / available
    return score, [reason for _, _, reason in parts]


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    diversify: bool = True, mode="balanced") -> List[Tuple[Dict, float, str]]:
    """
    Returns the top-k (song_dict, score, explanation) tuples, best first.

    mode picks the scoring strategy (see MODES). With diversify=True (default)
    repeats of an artist or sonic cluster are penalised when choosing the
    list; see _diversify.
    """
    get_mode(mode)  # fail fast on an unknown mode, even for an empty catalog
    # Judge every song once: (song, score, reasons).
    judged = [(song, *score_song(user_prefs, song, mode)) for song in songs]
    # sorted() returns a new list and leaves `songs` untouched. It is stable,
    # so tied scores keep their original CSV order.
    ranked = sorted(judged, key=lambda item: item[1], reverse=True)
    picked = _diversify(ranked, k) if diversify else ranked[:k]
    # Only build explanation strings for the k songs we actually return.
    return [(song, score, "; ".join(reasons)) for song, score, reasons in picked]


def _prefs_from_profile(user: UserProfile) -> Dict:
    """Converts a UserProfile into the preferences dict that score_song expects."""
    prefs = {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
    }
    if user.target_acousticness is not None:
        prefs["acousticness"] = user.target_acousticness
    return prefs


class Recommender:
    """OOP wrapper around the scoring logic. Required by tests/test_recommender.py"""

    def __init__(self, songs: List[Song], mode="balanced"):
        """Stores the song catalog to recommend from and the scoring mode to use."""
        get_mode(mode)
        self.songs = songs
        self.mode = mode

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the k songs that best fit the user, highest score first."""
        by_id = {song.id: song for song in self.songs}
        results = recommend_songs(_prefs_from_profile(user),
                                  [asdict(s) for s in self.songs], k=k, mode=self.mode)
        return [by_id[song["id"]] for song, _, _ in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns the song's score and the reasons behind it as one string."""
        score, reasons = score_song(_prefs_from_profile(user), asdict(song), self.mode)
        return f"Score {score:.2f}: " + "; ".join(reasons)
