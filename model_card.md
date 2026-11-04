# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

---

## 3. How the Model Works  

Think of it as a judge with a 10-point scorecard. The judge looks at every song in the catalog, one at a time, and asks how well it fits what the listener says they want. The songs with the most points are recommended.

**What the listener tells us:** their favorite genre, their favorite mood, how energetic they want the music (a number from 0 to 1), and whether they like acoustic sound. They can optionally add a few extras, such as how upbeat or how recent the music should be.

**How a song earns points:**

- **Energy (up to 3.5 points):** the closer the song's energy is to the listener's target, the more points. A near-perfect match earns almost all 3.5, and a song that is far off earns none.
- **Mood (up to 3 points):** full points if the mood is the same, half points if it is a close cousin (for example "chill" and "relaxed"), none otherwise.
- **Acoustic feel (up to 2 points):** closeness to a mostly acoustic sound for acoustic fans, or a mostly electronic sound for everyone else.
- **Genre (up to 1.5 points):** all or nothing. The song either has the listener's favorite genre or it doesn't.

Extras only count if the listener asked for them, and the final score is simply points earned divided by points available, so it always lands between 0 and 1. The songs are then sorted from highest to lowest and the top five are shown, each with a plain-language list of why it earned its points.

**Why mood counts for more than genre:** a genre label is a blunt tool. "Pop" and "indie pop" would count as a total miss, and most genres in this small catalog have only one song. Mood and energy describe how a song actually feels, so they get most of the points. A happy, high-energy song from a neighboring genre can therefore beat a same-genre song with the wrong vibe.

**Changes from the starter logic:** the starter only had empty placeholders. I added the point-based scorecard, the half-credit for related moods, a stricter closeness rule (a gap of 0.5 or more earns zero rather than half credit), and the "reasons" list so every recommendation is explainable.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
