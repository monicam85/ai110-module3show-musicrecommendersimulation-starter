"""
Command line runner for the Music Recommender Simulation.

Run from the project root with either:
    python -m src.main
    python src/main.py
"""

from pathlib import Path

try:  # works for `python -m src.main`
    from .recommender import load_songs, recommend_songs
except ImportError:  # works for `python src/main.py`
    from recommender import load_songs, recommend_songs

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
WIDTH = 64


def format_recommendations(user_prefs: dict, recommendations: list) -> str:
    """Builds a readable block: profile header, then one entry per song."""
    profile = ", ".join(f"{key}={value}" for key, value in user_prefs.items())
    lines = [
        "=" * WIDTH,
        "TOP RECOMMENDATIONS".center(WIDTH),
        "=" * WIDTH,
        f"Profile: {profile}",
        "",
    ]
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        lines.append(f"{rank}. {song['title']} by {song['artist']}")
        lines.append(f"   Score: {score:.2f} / 1.00   [{song['genre']} | {song['mood']}]")
        lines.append("   Why:")
        lines.extend(f"     - {reason}" for reason in explanation.split("; "))
        lines.append("")
    lines.append("-" * WIDTH)
    return "\n".join(lines)


def main() -> None:
    songs = load_songs(str(SONGS_CSV))
    print(f"Loaded songs: {len(songs)}\n")

    # Default profile: a pop fan who wants upbeat, non-acoustic music
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}

    recommendations = recommend_songs(user_prefs, songs, k=5)
    print(format_recommendations(user_prefs, recommendations))


if __name__ == "__main__":
    main()
