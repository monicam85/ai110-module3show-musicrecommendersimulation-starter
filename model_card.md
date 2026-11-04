# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeScorecard 1.0**: a small, explainable music recommender that scores every song against a listener's stated taste.

---

## 2. Goal, Intended Use and Non-Intended Use  

**Goal:** predict which songs a listener will like best. VibeScorecard suggests five songs from an 18-song catalog. It uses the listener's favorite genre, favorite mood, target energy (0 to 1) and how acoustic they want the music. Every suggestion comes with a plain-language list of the points it earned. A person can see exactly why it was chosen.

**Assumptions it makes about the listener:**

- They can describe their taste in one sitting, as a single genre, a single mood and a single energy number. There is no listening history and no "people like you" signal.
- Their taste is one consistent mood. Someone who wants calm songs on Monday and workout songs on Friday would need two separate profiles.
- They type genres and moods exactly as the catalog spells them (lowercase, such as "pop" or "happy").

**Intended use:** this is a classroom exploration. It shows how a content-based recommender turns song attributes into a ranked list. It is good for learning, for testing scoring ideas, and for explaining how recommendations work.

**Non-intended use:** do not use it for real listeners or real products. Do not use it to decide what music gets promoted, paid or hidden. Do not use it to judge anyone's taste. The songs are invented examples. The weights are my own hand-picked judgements, not learned from data. The catalog is too small and too lopsided to treat the results as fair for every kind of listener.

---

## 3. How the Model Works  

Think of it as a judge with a 10-point scorecard. The judge looks at every song in the catalog, one at a time, and asks how well it fits what the listener says they want. The songs with the most points are recommended.

**What the listener tells us:** their favorite genre, their favorite mood, how energetic they want the music (a number from 0 to 1), and how acoustic they want it, either as a yes/no ("likes acoustic") or as a number from 0 to 1. They can optionally add a few extras, such as how upbeat or how recent the music should be.

**How a song earns points:**

- **Energy (up to 3.5 points):** the closer the song's energy is to the listener's target, the more points. A near-perfect match earns almost all 3.5, and a song that is 0.5 or more away earns none.
- **Mood (up to 3 points):** full points if the mood is the same. A close cousin earns a share that depends on the pair: "intense" and "aggressive", or "sad" and "melancholic", earn 90%; "chill" and "relaxed" earn 70%; "happy" and "euphoric" earn 60%. Unrelated moods earn nothing.
- **Acoustic feel (up to 2 points):** closeness to the listener's acousticness target. A yes/no answer becomes a target of 0.8 (acoustic) or 0.2 (electronic); a number is used as given. An answer the system cannot read, such as "maybe", is rejected with an error instead of being guessed.
- **Genre (up to 1.5 points):** full points for the same genre, half points for a neighbor (for example rock and metal, or pop and indie pop), none otherwise.

Extras only count if the listener asked for them, and the final score is simply points earned divided by points available, so it always lands between 0 and 1. The songs are then sorted from highest to lowest and the top five are picked one at a time. Each pick lowers the score of later songs by the same artist (by 0.20) or from the same sound group (by 0.05), so one artist or one cluster of similar songs cannot take over the list. Each recommendation comes with a plain-language list of why it earned its points.

**Scoring modes:** the recipe above is the default, called "balanced". Three other modes change how many points each feature is worth: "genre-first", "mood-first" and "energy-focused". Only the weights change. The scoring steps are the same. You pick a mode when you run the program (`--mode`), or compare all four (`--compare`).

**Why mood counts for more than genre:** a genre label is a blunt tool, and most genres in this small catalog have only one song. Mood and energy describe how a song actually feels, so they get most of the points. A happy, high-energy song from a neighboring genre can therefore beat a same-genre song with the wrong vibe.

**Changes from the starter logic:** the starter only had empty placeholders. I added the point-based scorecard, a stricter closeness rule (a gap of 0.5 or more earns zero rather than half credit), and the "reasons" list so every recommendation is explainable. After testing I added graded credit for related moods, half credit for related genres, a numeric acousticness target with input checking, and the artist and cluster penalty. I tried and rejected two weight changes (see the README experiments): lowering the mood weight and doubling the energy weight.

---

## 4. Data  

The catalog is [data/songs.csv](data/songs.csv): 18 songs, each with a genre, a mood, and numbers for energy, tempo, valence, danceability, acousticness, instrumentalness, speechiness and release year (1972 to 2024).

**What is represented:** 15 genres and 14 moods, but thin. 13 of the 15 genres and 11 of the 14 moods have exactly one song; lofi (3 songs) and pop (2 songs) are the only genres with more than one. Energy is lopsided: 7 songs are below 0.45, only 3 are between 0.45 and 0.7, and 8 are at 0.75 or above. Mood and energy also move together, since every sad, chill, relaxed or focused song is low energy and every happy, intense, aggressive or euphoric song is high energy. Acousticness is similar, with only 1 song between 0.4 and 0.7.

**Did I add or remove data:** the starter file had 10 songs. I added 8 (ids 11 to 18: r&b, hip-hop, country, classical, metal, reggae, edm and folk) so that more genres and moods exist, and removed none.

**What is missing:** the songs are invented examples, not real recordings, and there is no listening history, language, artist popularity or lyrics. Whole areas of taste are absent or have one song each, such as Latin, K-pop, gospel and heavy electronic subgenres, and there are no mid-energy happy songs or high-energy sad ones.

---

## 5. Strengths  

- **It works well when a listener's tastes line up the way the catalog does.** Chill Lofi gets "Library Rain" (0.98), "Midnight Coding" and "Spacewalk Thoughts", all quiet, slow and acoustic. High-Energy Pop gets "Sunrise City" (0.97) first, a song that matches every one of its preferences. Both lists matched what I would have picked by hand.
- **The two ordinary profiles pull apart cleanly.** Pop and Lofi share no songs, which shows the scorecard really separates a loud, bright taste from a quiet, mellow one.
- **Near misses are treated sensibly.** Songs in neighboring moods and genres earn partial credit, so a lofi fan also sees a calm "focused" lofi track, a chill ambient track and a relaxed jazz track. After I gave each related mood pair its own credit, the Deep Intense Rock list put "Iron Tide" (metal, aggressive) ahead of "Gym Hero" (pop, intense), which matches how a rock fan would hear them.
- **Every recommendation is explainable.** Each result lists the points earned for energy, mood, acoustic feel and genre, which is how I found each of the weaknesses described in this card.
- **It fails safely on bad input.** Scores always stay between 0 and 1, an empty profile says "no preferences provided" rather than inventing a taste, and values it cannot read (such as `likes_acoustic = "maybe"`) are rejected with an error instead of being guessed. The word "no" is read correctly as "not acoustic".
- **The ranking avoids obvious repeats.** A song by an artist who already has a pick in the list, or one from the same sound group, is nudged down, so one artist does not fill the list.
- **It is tested.** 12 automatic tests cover the scoring rules, the related genre and mood credit, the acousticness parsing and the diversity step.

---

## 6. Limitations and Bias 

Energy and mood move together in my catalog: sad and chill songs are all low energy, and happy and intense songs are all high energy. A "sad but high-energy" listener shows the problem, because "Hollow Lantern" (energy 0.30) wins at 0.62 as the only sad song, even though it earns 0 of the 3.5 energy points. The system never says that nothing fits both wishes, and doubling the energy weight just made a rock song the winner instead. Listeners at the extremes also lose out, since an energy request of 0.1 earns credit from only 10 of 18 songs. The root cause is the tiny catalog, where five loud songs fill 28 of the 60 top-5 slots, so more songs would help more than better weights.

---

## 7. Evaluation  

### Which profiles I tested

I tested 14 listener profiles. I looked at the top 5 songs for each. 12 ran. 2 were refused on purpose.

- **Three ordinary tastes:** High-Energy Pop (pop, happy, energy 0.85, not acoustic). Chill Lofi (lofi, chill, energy 0.35, acoustic). Deep Intense Rock (rock, intense, energy 0.92, not acoustic).
- **Eleven tricky tastes:**
  - Sad but high-energy folk.
  - A metal fan who wants chill music.
  - An acoustic-loving EDM fan.
  - An empty profile.
  - "Pop" and "Happy" typed with capital letters.
  - `likes_acoustic = "no"` typed as a word.
  - A jazz fan with acousticness 0.5.
  - A profile that only names a genre (lofi).
  - Energy set to 1.5, which is off the scale.
  - `likes_acoustic = "maybe"`.
  - Energy typed as the word "high".
- The last two are refused with an error message. That is on purpose.

I also did these checks:

- I ran 12 automatic tests.
- I checked by hand that scores stay between 0 and 1.
- I checked that the points in each "why" list add up.
- I ran four experiments. Each changed one rule. The README has the details.
  1. A lower mood weight.
  2. Double energy and half genre.
  3. A higher flat credit for similar moods.
  4. A separate credit for each pair of similar moods. I kept this one.
- I compared four scoring modes side by side. Each mode flipped at least one result. For example, "genre-first" lifts "Gym Hero" to second place for Happy Pop fans, and "energy-focused" makes a rock song the top pick for the sad folk fan.

### Why "Gym Hero" keeps showing up for "Happy Pop" fans

Think of the recommender as a judge with a scorecard. A Happy Pop fan wants pop, happy, energetic, not acoustic. "Gym Hero" is a pop song. It is very energetic. It is not acoustic at all.

So it earns almost every point. It earns 2.9 points for energy. It earns 1.4 for not being acoustic. It earns 1.5 for being pop. It earns **0 of 3 mood points**. Its mood is "intense", not "happy".

Its total is 0.58 out of 1.00. That is only fourth place. "Sunrise City" scores 0.97. But the catalog has only 18 songs. Only two are pop. There are few other songs to fill the list.

The judge cannot hear the difference between a happy pop song and a workout pop song. It only sees labels and numbers. Loud, electronic songs match many tastes on the numbers. So "Gym Hero" also shows up for rock fans, EDM fans and the "metal fan who wants chill". It appeared in 6 of the 12 lists.

This makes sense for the scorecard. It is not what a real Happy Pop fan wants. A small catalog and number-only rules can repeat the same song.

### What surprised me

- **A few loud songs show up everywhere.** Five songs fill 28 of the 60 top-5 slots. I expected genre to cause this. But genre has the smallest main weight. The real cause is the small catalog.
- **A "sad but high-energy" listener gets a slow song first.** "Hollow Lantern" has energy 0.30. The listener asked for 0.9. It wins at 0.62 because it is the only sad song. Nothing says that no song fits both wishes.
- **Changing the weights barely helped.** A lower mood weight left almost every #1 song the same. A higher flat credit for similar moods did too. What fixed the rock list was a separate credit for each pair of similar moods.
- **Typing "Pop" instead of "pop" quietly breaks things.** The system still returns songs. It gives no warning. The genre and mood points are gone. The top score falls from 0.97 to 0.53.
- **One preference gives a perfect score.** A profile that only says "lofi" gives three songs a score of 1.00. That looks perfect. It only means the one thing I asked for matched.

### Comparing profiles, pair by pair

Every profile appears in at least one pair. In each pair, the profiles differ mostly in one way. So the change in the results shows what that preference controls.

1. **High-Energy Pop vs Chill Lofi.**
   - Pop gets "Sunrise City", "Rooftop Lights" and "Laser Cathedral". These are loud and bright.
   - Lofi gets "Library Rain", "Midnight Coding" and "Spacewalk Thoughts". These are quiet and acoustic.
   - The two lists share no songs.
   - This makes sense. Energy, mood and acoustic feel all point opposite ways. It is the clearest sign that the scorecard separates two tastes.
2. **High-Energy Pop vs Deep Intense Rock.**
   - Both want loud, non-acoustic music. Both lists come from the same pool of loud songs. "Gym Hero" and "Sunrise City" are in both.
   - The order changes. Pop puts the happy songs first. Rock puts the intense songs first: "Storm Runner" and "Iron Tide".
   - This is correct. The only real difference is mood and genre.
3. **Deep Intense Rock vs the `likes_acoustic = "no"` rock profile.**
   - These are meant to be the same taste. Energy is 0.92 and 0.90.
   - The lists are almost the same. "Storm Runner" is first at 0.95 in both. "Iron Tide" scores 0.80 and 0.78. "Gym Hero" scores 0.78 and 0.77.
   - This is what I wanted. The word "no" now means "not acoustic". It used to be read as "yes".
4. **Deep Intense Rock vs the metal fan who wants chill.**
   - Both want loud, non-acoustic music at about the same energy.
   - Rock tops out at 0.95 with "Storm Runner". The metal fan tops out at 0.64 with "Iron Tide". It matches the genre but not the mood.
   - This makes sense. No song is both very loud and chill. The system returns loud songs. The scores honestly drop.
5. **Chill Lofi vs the acoustic-loving EDM fan.**
   - Both say they like acoustic music. The results are opposite.
   - Lofi gets quiet acoustic songs. The EDM fan gets "Laser Cathedral" first. It is almost fully electronic. Its acousticness is 0.03.
   - Genre, mood and energy all match for the EDM fan. Acoustic feel is worth only 2 of 10 points.
   - So the acoustic wish is a weak voice. A real listener may not want that.
6. **The acoustic-loving EDM fan vs the "sad but high-energy" folk fan.**
   - Both want loud (0.9 to 0.95) and acoustic music. The EDM fan gets a loud song first. The folk fan gets a quiet one.
   - The cause is the catalog, not the wishes. EDM has a song that is loud and euphoric. The only sad song is slow.
   - The folk fan's wish for sad and loud cannot be met. This is the weakness in Section 6.
7. **Chill Lofi vs the jazz fan with acousticness 0.5.**
   - Both like mellow music. The jazz fan wants middle energy (0.5) and middle acoustic feel.
   - The jazz list moves to "Coffee Shop Stories" (jazz) and "Island Breeze" (reggae, middle energy). It adds a few lofi songs.
   - The best score is 0.75, not 0.98.
   - This makes sense. Few songs sit in the middle. A middle taste has fewer near-perfect matches than a taste at one end.
8. **High-Energy Pop vs the capital-letter "Pop" and "Happy" profile.**
   - This is the same taste. The capital letters cost all the genre and mood points. The system compares text exactly.
   - "Sunrise City" is still first. Its score falls from 0.97 to 0.53. "Concrete Verses" (hip-hop, confident) jumps to second.
   - This result is not valid for a real user. A real user expects "Pop" to mean pop. It is a weakness, not good behavior.
9. **High-Energy Pop vs the energy 1.5 profile.**
   - Same genre and mood. The only change is that 1.5 is beyond every song.
   - The first two songs stay the same: "Sunrise City" and "Rooftop Lights". Mood and genre still count.
   - The top score drops from 0.97 to 0.64. The rest of the list gets weaker.
   - The system falls back on the other wishes. That is sensible. But it never tells the user the energy request was impossible.
10. **The empty profile vs the lofi-only profile.**
    - With nothing to go on, every song scores 0.00. The list is just the first songs in the file. "Sunrise City" is first.
    - With only "lofi", three lofi songs score 1.00. The ambient and jazz songs get 0.50 for being neighbors of lofi.
    - This follows the rules. But it shows how little a score means when almost nothing was asked. A 1.00 here does not mean "perfect for you".

### What I trust and what I do not

I trust the system when a taste matches how the catalog is built. Loud and happy works. Quiet and chill works.

I do not trust it in three cases. The first is a taste that crosses the line between low-energy and high-energy moods. The second is a preference typed with different capital letters. The third is a profile with only one or two preferences. The score looks confident in all three.

I did not use a number to measure accuracy. Every judgement above comes from comparing the results to what I would expect to hear.

---

## 8. Ideas for Improvement  

1. **Add many more songs.** Most problems I found come from having only 18 songs. Five loud songs fill 28 of 60 top-5 slots, and 13 of 15 genres have one song. Hundreds of songs, with some sad high-energy and happy mid-energy tracks, would help more than any weight change.
2. **Say so when nothing fits.** If the best score is low, or the request conflicts (like "sad" with energy 0.9), the output should say "closest I could find". Right now it shows the same confident list.
3. **Accept messier input.** Ignore capital letters and extra spaces, so "Pop" means "pop". Reject energy values outside 0 to 1 with a clear message.

**Smaller ideas:** let a listener give an energy range or two moods. Use tempo and danceability, which are in the data but unused. Learn which moods and genres are similar from real listening data instead of my guesses. Add a one-sentence summary above the points list, such as "close on energy, but not the mood you asked for."

---

## 9. Personal Reflection  

### My biggest learning moment

The weights were not the lever. I wanted "Iron Tide" to rank above "Gym Hero" for a rock fan. I lowered the mood weight. I doubled the energy weight. I raised the flat credit for similar moods. None of it fixed the problem. When I worked out the points by hand, I saw why. An exact mood match is worth much more than a related one, and one global number cannot fix one pair without loosening all the others. Giving each pair of similar moods its own credit fixed it. The bigger lesson is that a recommender is a chain of judgement calls. Which features count, how much each is worth and which moods are neighbors are all my choices. The results are only as good as those choices and the catalog behind them.

### How AI tools helped, and when I had to double-check them

I used Claude Code through the whole project. It wrote the tricky test profiles and ran them. It ran each experiment in a scratch script, so my code stayed unchanged until I chose to keep something. It also checked that scores stay between 0 and 1 and helped write the docs. That saved a lot of time.

Its predictions were often wrong, so I checked each one against the real output. Here are four examples:

- It said a genre similarity map would fix "Gym Hero" over "Iron Tide". It did not.
- It said a mood credit of 0.75 would flip the rock list. The credit had to be about 0.9 or more.
- It guessed that a chill song might beat "Iron Tide" for the metal fan. It did not.
- Its first variety rule, a hard cap per cluster, pushed weak filler songs into many lists. I replaced it with a gentler penalty.

One automatic check also flagged two "failures" that were only rounding. I only trusted a claim after the run or the arithmetic agreed with it. When an experiment was not better, I reverted it and wrote down why.

### What surprised me about simple algorithms

Four simple rules were enough to feel like real recommendations. The Chill Lofi list looked like a playlist I would make myself. A score of 0.97 felt like the system understood me. The "why" list made it feel even more convincing. But the system only compares numbers and labels. It cannot tell a happy pop song from a workout pop song. That is why "Gym Hero" kept appearing. It also gave a sad, high-energy listener a slow song with no warning. A confident-looking list can hide how little the system knows.

### What I would try next

1. Add many more songs, with some sad high-energy and happy mid-energy tracks. Most of my problems came from having only 18.
2. Make the system say "closest I could find" when nothing fits a listener's taste.
3. Ignore capital letters, so "Pop" means "pop".
4. Learn which moods and genres are similar from real listening data. My 0.9 for intense and aggressive was tuned to one test, so I would check it on a second dataset.
