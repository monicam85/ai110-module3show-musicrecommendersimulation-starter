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

# Scoring recipe, in points. Core features total 10 points:
#   energy +3.5 max, mood +3.0, acousticness +2.0, genre +1.5.
# Mood outweighs genre on purpose: in this catalog most genres have a single
# song, so a heavy genre weight would just pin the result to that one track.
# Optional extras only count when the user supplies that preference. Preferences
# the user did not supply (or features a song lacks) are skipped, and the final
# score is points earned / points available, a 0-1 value.
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

# Numeric closeness is linear and reaches 0 once the gap hits this tolerance,
# so a 0.5 energy gap earns nothing (plain 1 - |diff| would still give half).
TOLERANCE = 0.5

# release_year is normalised by this span so a year gap becomes a 0-1 distance.
YEAR_MIN, YEAR_MAX = 1960, 2025

# Near-miss moods earn half credit instead of zero.
PARTIAL_MOOD_CREDIT = 0.5
RELATED_MOODS = {
    frozenset(pair) for pair in [
        ("chill", "relaxed"), ("chill", "focused"), ("chill", "laid-back"),
        ("relaxed", "laid-back"), ("intense", "aggressive"),
        ("happy", "euphoric"), ("sad", "melancholic"), ("moody", "melancholic"),
    ]
}


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


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a song against user preferences on a 0-1 scale.

    Recognised pref keys: genre, mood, energy, valence, likes_acoustic (bool),
    instrumentalness, speechiness, release_year.
    Numeric features earn points by closeness to the target (see _closeness);
    genre is all-or-nothing; mood is full credit on a match, half on a related
    mood. Returns (score, reasons), where reasons list the points earned.
    """
    parts = []  # (max points, fraction earned, reason)

    def add(key: str, fraction: float, reason: str) -> None:
        """Records one feature's max points, fraction earned and reason string."""
        parts.append((POINTS[key], fraction, f"{reason} (+{POINTS[key] * fraction:.2f})"))

    if "energy" in user_prefs:
        add("energy", _closeness(song["energy"], user_prefs["energy"]),
            f"energy {song['energy']:.2f} vs target {user_prefs['energy']:.2f}")
    if "mood" in user_prefs:
        if song["mood"] == user_prefs["mood"]:
            add("mood", 1.0, f"mood matches ({song['mood']})")
        elif frozenset((song["mood"], user_prefs["mood"])) in RELATED_MOODS:
            add("mood", PARTIAL_MOOD_CREDIT, f"mood is close ({song['mood']})")
        else:
            add("mood", 0.0, f"mood differs ({song['mood']})")
    if "likes_acoustic" in user_prefs:
        target = 0.8 if user_prefs["likes_acoustic"] else 0.2
        add("acousticness", _closeness(song["acousticness"], target),
            f"acousticness {song['acousticness']:.2f} fits "
            f"{'acoustic' if user_prefs['likes_acoustic'] else 'non-acoustic'} taste")
    if "genre" in user_prefs:
        match = song["genre"] == user_prefs["genre"]
        add("genre", 1.0 if match else 0.0,
            f"genre matches ({song['genre']})" if match else f"genre differs ({song['genre']})")
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


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Returns the top-k (song_dict, score, explanation) tuples, best first."""
    # Judge every song once: (song, score, reasons).
    judged = [(song, *score_song(user_prefs, song)) for song in songs]
    # sorted() returns a new list and leaves `songs` untouched. It is stable,
    # so tied scores keep their original CSV order.
    ranked = sorted(judged, key=lambda item: item[1], reverse=True)
    # Only build explanation strings for the k songs we actually return.
    return [(song, score, "; ".join(reasons)) for song, score, reasons in ranked[:k]]


def _prefs_from_profile(user: UserProfile) -> Dict:
    """Converts a UserProfile into the preferences dict that score_song expects."""
    return {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
    }


class Recommender:
    """OOP wrapper around the scoring logic. Required by tests/test_recommender.py"""

    def __init__(self, songs: List[Song]):
        """Stores the song catalog to recommend from."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the k songs that best fit the user, highest score first."""
        prefs = _prefs_from_profile(user)
        ranked = sorted(self.songs, key=lambda s: score_song(prefs, asdict(s))[0], reverse=True)
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns the song's score and the reasons behind it as one string."""
        score, reasons = score_song(_prefs_from_profile(user), asdict(song))
        return f"Score {score:.2f}: " + "; ".join(reasons)
