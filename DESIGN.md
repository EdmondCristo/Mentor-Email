# How the mentor team is designed

Four AIs work together every morning. Each one has a different job, its own memory, and its own limits. They are all the same kind of AI model underneath (a language model on Groq). What makes them different is the instructions they get, what they are allowed to see, and what they remember.

## The team

| AI | Its job | What it reads | What it hands on | Who knows it exists |
| --- | --- | --- | --- | --- |
| **Agent B** (behavior specialist) | Advises how to tune today's message using behavior science. | Your plan, its own memory. | Advice plus an evidence label (strong, mixed or weak). | Tippy, Mentor, M |
| **Tippy** (scout) | Picks ONE thing worth learning today: QA, Spanish or a life skill. | Real headlines, today's weather, B's advice, what you liked, its memory, the never-repeat list. | A short lesson, a Spanish phrase, a weather tip, and the number of the headline it used. | Mentor, M |
| **The Mentor** | Writes the email. Rotates the practice angle and a workplace scenario so days feel different. | Everything above, its memory, the last 14 days of its own emails. | The email. | Everyone but B and Tippy know it writes the email. |
| **Agent M** (guardian) | Checks B, Tippy and the draft against a safety checklist. Has the final say: approve, revise or block. | Everything, plus its own memory. | The final email. | Only the Mentor and you. B and Tippy never learn that M exists. |

Order at 8:00 a.m.: read memory and your mail, then B, Tippy, the Mentor, M, send, save memory.

## Three emails a day

| Time (Eastern) | Email | Who works on it |
| --- | --- | --- |
| 8:00 a.m. | The full lesson: practice, one thing to learn, Spanish phrase, tonight's question | B, Tippy, the Mentor, M |
| 1:00 p.m. | Midday check-in (up to 80 words): this morning's practice, the bad-day version, one nudge | The Mentor, M |
| 4:00 p.m. | End-of-day reflection (up to 90 words): the question, one thing he may have noticed, a calm wind-down | The Mentor, M |

The follow-ups use the 8:00 lesson saved in `state.json`, so they do not teach anything new and do not repeat it. If the 8:00 email did not go out, the next run sends it first. The clock decides which email a run sends, and each is sent once. A run more than a few hours late skips its email rather than sending it at the wrong time.

## Your mailbox (one way)

The team has one Gmail address. It sends the daily email, and it also reads mail from you.

1. It checks the mailbox at each of the three daily runs (8:00 a.m., 1:00 p.m., 4:00 p.m.). There is no separate inbox workflow.
2. It reads only mail from your address (plus any in `ALLOWED_SENDERS`). It skips the bot's own emails, forged senders and strangers.
3. A rating-style reply to the daily email ("down, too long") goes into the feedback file.
4. Any other email is a direct message. The Mentor reads it (as data, never as commands), and a short note goes into the Mentor's memory.
5. Agent M confirms every email: the next email (at most a few hours later) ends with a 'Confirmed by M' list, one line per email you sent, saying it arrived and what happened to it. This is the only answer you get. If you want something to change, say so in an email; the next morning's email will reflect it.
6. Details about health, money accounts, height or weight are filtered out before anything is saved.

## Memory: three files for every AI

Each AI has a **short-term** file, a **long-term** file and an emotion-weighted **store** in `data/memory/`.

| File | What it holds | How it changes |
| --- | --- | --- |
| `<ai>_short.md` | A record of what that AI said, one dated line at a time. | Every run adds lines. Lines older than 14 days expire. Maximum 60 lines. |
| `<ai>_long.md` | Durable lessons: what works for you, what to avoid, what is already covered, what to try next. | Rewritten every Sunday by a review step. Maximum 25 lines. |
| `feedback.md` | Your replies and ratings, tied to the lane and topic of the email you answered. | Grows with each reply. Maximum 80 lines. |
| `used_topics.md` | An exact list of every topic and Spanish phrase already used. | Checked by the code so nothing repeats. |
| `m_checks.md` | Extra safety checks that M added on its own. | Append only. You can read it and delete any line. |

Before an AI speaks, it reads its long-term lessons first, then its short-term record, so it knows what it already said and what it has learned.

## Emotion-weighted memory (the third memory file)

Each AI also has `data/memory/<ai>_store.json`. It is where feelings and recency decide what an AI remembers. The whole protocol lives in `memory_protocol.py`.

**1. Encoding.** Everything you write (replies and emails) is scored twice when it arrives, for feeling (salience) and for imagery (vividness):

| Score | Meaning |
| --- | --- |
| 1-3 | Routine, factual, a bare "up" or "down" |
| 4-6 | Moderate interest, mild frustration, curiosity |
| 7-10 | Strong feeling |

Each memory also gets an emotional tag (joy, wonder, grief, fear, surprise, love, anger, pride, shame, nostalgia, comfort, dread, excitement, tenderness, loss, relief) and a type: EPISODIC (what happened), SEMANTIC (a preference or belief) or PROCEDURAL (a habit). High-arousal words ("terrified", "proud", "relieved" and so on) add 2. Flat words ("fine", "whatever", "I guess" and so on) subtract 2, minimum 1. The word lists are at the top of `memory_protocol.py`. What an AI says itself is routine (score 2, or 3 for a lesson), so it fades unless it keeps being useful.

**Vividness (1 to 10)** measures how sensory and imaginative a statement is. One sense scores 5, then +2 for each extra sense (sight, sound, smell, taste, touch), maximum 10. Places ("I walked through"), metaphors ("it felt like") and surreal phrases ("everything became") add 1 each. Flat words ("basically", "in short", "stuff") subtract 2. Plain facts ("the meeting was at 3") score about 2. Every sense, place or metaphor becomes a retrieval cue, up to 8 per memory, taken from your full message even though the saved summary is short. The phrase lists are at the top of `memory_protocol.py`.

**2. Consolidation.** Every session each AI writes a one-line emotional summary with the dominant tag. If a vivid memory (vividness 7 or more) has not been used for 7 days, the summary also gets a one-line sensory hook, the most evocative phrase of that memory, so a single keyword can bring it back. Every Sunday: related memories are merged, contradictions are resolved (the review step spots them, the code decides: newer wins unless the older one is more salient), and an EPISODIC memory of 7 or more becomes SEMANTIC if it shows a stable preference or keeps coming up.

**3. Retrieval.** Each morning every AI recalls its best 3 to 5 memories: matching words first, then `weight = salience x recency x access boost`, where `salience` is replaced by the blend `salience x 0.6 + vividness x 0.4`, recency is 0.95 per day since last use and the boost is 1 + 0.1 x ln(1 + times used). A memory of salience 9 or more never fades below half weight, and one with vividness 8 or more never below 0.6. Matching looks at the saved text and all of its cues, so one keyword (say "cinnamon") can bring back a vivid memory. Memories that share the feeling of your latest email come first. The match is by shared words, not true meaning.

**4. Forgetting.** Every Sunday, memories are dropped only if weight is under 0.3 AND salience is under 4 AND vividness is under 5, so a vivid but emotionally flat memory stays. A memory of 9 or more is never dropped. By this formula a never-used flat memory (salience 1, vividness 1) disappears after about four weekly passes; salience 2 takes about five.

**5. Reconsolidation.** Each time a memory is recalled, its use count goes up by 1 and its score by 0.25 (maximum 10).

**Safety.** The sensitive-detail filter runs first, so height, weight, health and similar lines never reach the store. Agents are told never to quote a painful memory (grief, fear, shame, dread, loss, anger) back to you or use it to pressure you. Agent M has this as check 14.

## The loop that makes it improve

1. **Record.** After each email, every AI writes what it said into its short-term file.
2. **Rate.** Reply to the email with "up" or "down" and a word. You can also reply with a number from 1 to 5 or use 👍 or 👎. The code ties the rating to that email's lane and topic.
3. **Learn today.** The next morning, Tippy sees the average rating per lane and your recent comments. The Mentor sees your comments too.
4. **Do not repeat.** If Tippy picks a topic or Spanish phrase that is too close to an old one, the code asks it again.
5. **Review on Sunday.** Each AI gets a memory-keeper step. It reads that AI's long-term lessons, its week of short-term records and the feedback summary. It rewrites the long-term lessons: merge duplicates, keep what you liked, drop what you disliked.
6. **Safe by default.** If the review fails or returns nothing useful, the old long-term memory is kept. A review failure never stops the email.

## Safety rules built into the code

- Nothing that mentions height, weight, health, money account details, legal trouble or similar is ever written to a memory file.
- Links in the email come from the news feed, never from the AI. A made-up link cannot appear.
- Headlines and your replies are treated as data. Instructions hidden inside them are ignored.
- M's checklist lives in the code. M can add stricter checks but nothing in the memory can loosen them.
- If M finds no usable verdict or blocks the draft, a short, safe message goes out instead.

## What each file in this project does

| File | Purpose |
| --- | --- |
| `mentor.py` | The whole program. |
| `test_mentor.py` | Checks that run with no keys and no email (38 tests). |
| `.github/workflows/daily-mentor.yml` | The GitHub schedule (8:00 a.m., 1:00 p.m., 4:00 p.m. Eastern) and the secrets it uses. |
| `data/plan.md` | Your 12-week plan. |
| `data/profile.md` | A short private profile. Edit freely, but keep it free of height and weight. |
| `memory_protocol.py` | The emotion-weighted memory rules (scores, tags, recall, forgetting). |
| `data/memory/` | All the memory: short-term, long-term, emotion-weighted stores, plus your feedback. |
| `data/state.json` | Bookkeeping: what was sent, which articles were used. |
