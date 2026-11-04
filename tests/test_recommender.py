from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ---- genre similarity, numeric acousticness and diversity ----

import pytest
from src.recommender import score_song, recommend_songs


def _song(**overrides):
    base = dict(id=1, title="T", artist="A", genre="rock", mood="intense",
                energy=0.9, acousticness=0.1)
    base.update(overrides)
    return base


def test_related_genre_gets_half_credit_between_match_and_miss():
    prefs = {"genre": "rock"}
    exact = score_song(prefs, _song(genre="rock"))[0]
    related = score_song(prefs, _song(genre="metal"))[0]
    unrelated = score_song(prefs, _song(genre="pop"))[0]
    assert exact == 1.0 and related == 0.5 and unrelated == 0.0


def test_acousticness_number_is_used_as_target():
    score, _ = score_song({"acousticness": 0.5}, _song(acousticness=0.5))
    assert score == 1.0


@pytest.mark.parametrize("text, target", [("no", 0.2), ("False", 0.2), ("yes", 0.8)])
def test_likes_acoustic_strings_are_parsed_not_truthy(text, target):
    score, _ = score_song({"likes_acoustic": text}, _song(acousticness=target))
    assert score == 1.0


def test_unparseable_likes_acoustic_raises():
    with pytest.raises(ValueError):
        score_song({"likes_acoustic": "maybe"}, _song())


def test_diversify_pushes_down_repeat_artist_but_not_a_clearly_better_song():
    # Three equally good songs by X, one slightly worse by Y, one far worse by Z.
    songs = [_song(id=1, artist="X", energy=0.90), _song(id=2, artist="X", energy=0.90),
             _song(id=3, artist="X", energy=0.90), _song(id=4, artist="Y", energy=0.85),
             _song(id=5, artist="Z", energy=0.30)]
    top3 = [s["id"] for s, _, _ in recommend_songs({"energy": 0.9}, songs, k=3)]
    assert top3 == [1, 4, 2]  # Y jumps ahead of X's repeats; weak Z does not


def test_diversify_off_keeps_plain_score_order():
    songs = [_song(id=i, artist="X") for i in range(1, 4)] + [_song(id=9, artist="Y", energy=0.8)]
    ids = [s["id"] for s, _, _ in recommend_songs({"energy": 0.9}, songs, k=4, diversify=False)]
    assert ids == [1, 2, 3, 9]


def test_diversify_still_returns_k_when_everything_is_a_repeat():
    songs = [_song(id=i, artist="Same") for i in range(5)]
    assert len(recommend_songs({"energy": 0.9}, songs, k=5)) == 5


def test_related_moods_get_graded_credit():
    # intense/aggressive are closer than happy/euphoric, so they earn more of the mood points.
    close = score_song({"mood": "intense"}, _song(mood="aggressive"))[0]
    looser = score_song({"mood": "happy"}, _song(mood="euphoric"))[0]
    exact = score_song({"mood": "intense"}, _song(mood="intense"))[0]
    none = score_song({"mood": "intense"}, _song(mood="chill"))[0]
    assert exact == 1.0 and none == 0.0
    assert close == 0.9 and looser == 0.6


# ---- scoring modes (Strategy pattern) ----

from src.recommender import MODES, get_mode, ScoringMode


def test_every_mode_keeps_scores_between_0_and_1_and_perfect_match_is_1():
    prefs = {"genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": False}
    perfect = _song(genre="rock", mood="intense", energy=0.9, acousticness=0.2)
    worst = _song(genre="x", mood="y", energy=0.0, acousticness=1.0)
    for name in MODES:
        assert score_song(prefs, perfect, mode=name)[0] == pytest.approx(1.0), name
        assert score_song(prefs, worst, mode=name)[0] == pytest.approx(0.0), name


def test_balanced_mode_matches_the_default_scoring():
    prefs = {"genre": "rock", "mood": "intense", "energy": 0.9}
    song = _song(mood="chill", energy=0.6)
    assert score_song(prefs, song) == score_song(prefs, song, mode="balanced")


def test_genre_first_and_mood_first_rank_the_same_songs_differently():
    right_genre = _song(id=1, title="RG", genre="rock", mood="chill", energy=0.5)
    right_mood = _song(id=2, title="RM", genre="pop", mood="intense", energy=0.5)
    prefs = {"genre": "rock", "mood": "intense", "energy": 0.5}
    best = lambda mode: recommend_songs(prefs, [right_genre, right_mood], k=1, mode=mode)[0][0]["id"]
    assert best("genre-first") == 1
    assert best("mood-first") == 2


def test_unknown_mode_is_rejected_everywhere():
    with pytest.raises(ValueError):
        get_mode("loudest")
    with pytest.raises(ValueError):
        recommend_songs({"energy": 0.5}, [_song()], mode="loudest")
    with pytest.raises(ValueError):
        Recommender([], mode="loudest")


def test_a_custom_mode_object_can_be_passed_in():
    only_energy = ScoringMode("only-energy", "test", {"mood": 0.0, "genre": 0.0, "acousticness": 0.0})
    prefs = {"mood": "intense", "energy": 0.9}
    assert score_song(prefs, _song(mood="chill", energy=0.9), mode=only_energy)[0] == 1.0


def test_recommender_class_uses_its_mode():
    songs = [Song(id=1, title="RG", artist="A", genre="rock", mood="chill", energy=0.5,
                  tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.2),
             Song(id=2, title="RM", artist="B", genre="pop", mood="intense", energy=0.5,
                  tempo_bpm=100, valence=0.5, danceability=0.5, acousticness=0.2)]
    user = UserProfile("rock", "intense", 0.5, False)
    assert Recommender(songs, mode="genre-first").recommend(user, k=1)[0].id == 1
    assert Recommender(songs, mode="mood-first").recommend(user, k=1)[0].id == 2
