"""
Command line runner for the Music Recommender Simulation.

Run from the project root with either:
    python -m src.main
    python src/main.py

Options:
    --mode NAME   scoring strategy: balanced (default), genre-first,
                  mood-first or energy-focused
    --compare     show the top 3 of every mode side by side for each profile
"""

import argparse
from pathlib import Path

try:  # works for `python -m src.main`
    from .recommender import MODES, load_songs, recommend_songs
except ImportError:  # works for `python src/main.py`
    from recommender import MODES, load_songs, recommend_songs

SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
WIDTH = 64


# Distinct taste profiles used to evaluate the scoring logic.
PROFILES = {
    "High-Energy Pop": {
        "genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False,
    },
    "Chill Lofi": {
        "genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False,
    },
    # Adversarial: sad mood but very high energy, which almost never go together.
    "Conflicted (sad but high-energy)": {
        "genre": "folk", "mood": "sad", "energy": 0.9, "likes_acoustic": True,
    },
    # Adversarial: genre and energy point to metal, but the mood is chill.
    "Adversarial: metal fan who wants chill": {
        "genre": "metal", "mood": "chill", "energy": 0.97, "likes_acoustic": False,
    },
    # Adversarial: acoustic taste contradicts an acoustic-free genre and energy.
    "Adversarial: acoustic-loving EDM fan": {
        "genre": "edm", "mood": "euphoric", "energy": 0.95, "likes_acoustic": True,
    },
    # Adversarial: no preferences at all.
    "Adversarial: empty profile": {},
    # Adversarial: wrong capitalisation, so exact matching never hits.
    "Adversarial: wrong-case genre and mood": {
        "genre": "Pop", "mood": "Happy", "energy": 0.8, "likes_acoustic": False,
    },
    # Adversarial: a string where a bool belongs. "no" used to be truthy; it is now parsed.
    "Adversarial: likes_acoustic='no'": {
        "genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": "no",
    },
    # Adversarial: an unparseable string; should be rejected, not guessed.
    "Adversarial: likes_acoustic='maybe'": {
        "genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": "maybe",
    },
    # Numeric acoustic target (middle of the road) instead of a yes/no switch.
    "Numeric acousticness=0.5": {
        "genre": "jazz", "mood": "relaxed", "energy": 0.5, "acousticness": 0.5,
    },
    # Adversarial: a single weak preference gets normalised to a full 0-1 range.
    "Adversarial: genre-only (lofi)": {"genre": "lofi"},
    # Adversarial: energy outside the 0-1 range.
    "Adversarial: energy out of range (1.5)": {
        "genre": "pop", "mood": "happy", "energy": 1.5, "likes_acoustic": False,
    },
    # Adversarial: wrong type for energy; expected to crash.
    "Adversarial: energy='high' (wrong type)": {
        "genre": "pop", "mood": "happy", "energy": "high", "likes_acoustic": False,
    },
}


def format_recommendations(name: str, user_prefs: dict, recommendations: list) -> str:
    """Builds a readable block: profile header, then one entry per song."""
    profile = ", ".join(f"{key}={value}" for key, value in user_prefs.items())
    lines = [
        "=" * WIDTH,
        f"TOP RECOMMENDATIONS: {name}".center(WIDTH),
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


def format_comparison(name: str, user_prefs: dict, songs: list, k: int = 3) -> str:
    """One block per profile: the top k songs of every scoring mode, one mode per line."""
    profile = ", ".join(f"{key}={value}" for key, value in user_prefs.items()) or "(empty)"
    lines = [f"{name}", f"  Profile: {profile}"]
    for mode_name in MODES:
        picks = recommend_songs(user_prefs, songs, k=k, mode=mode_name)
        cells = " > ".join(f"{song['title']} ({score:.2f})" for song, score, _ in picks)
        lines.append(f"  {mode_name:<15} {cells}")
    return "\n".join(lines)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument("--mode", choices=list(MODES), default="balanced",
                        help="scoring strategy (default: balanced)")
    parser.add_argument("--compare", action="store_true",
                        help="compare the top 3 of every mode for each profile")
    args = parser.parse_args(argv)

    songs = load_songs(str(SONGS_CSV))
    print(f"Loaded songs: {len(songs)}\n")

    if args.compare:
        print("Top 3 per scoring mode (score in brackets)")
        print("=" * WIDTH)
        for mode in MODES.values():
            print(f"  {mode.name:<15} {mode.description}")
        print("=" * WIDTH + "\n")
        for name, user_prefs in PROFILES.items():
            try:
                print(format_comparison(name, user_prefs, songs))
            except Exception as error:  # adversarial profiles may be invalid on purpose
                print(f"{name}: CRASHED with {type(error).__name__}: {error}")
            print()
        return

    for name, user_prefs in PROFILES.items():
        try:
            recommendations = recommend_songs(user_prefs, songs, k=5, mode=args.mode)
        except Exception as error:  # adversarial profiles may be invalid on purpose
            print(f"{name}: CRASHED with {type(error).__name__}: {error}\n")
            continue
        label = name if args.mode == "balanced" else f"{name} [{args.mode}]"
        print(format_recommendations(label, user_prefs, recommendations))
        print()


if __name__ == "__main__":
    main()
