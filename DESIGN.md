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

## The mission: tiny promises that add up

Every AI gets the same extra mission (the text is in `data/mission.md`, and you can edit it). It names four areas: **job** (QA manager), **love** (finding a wife), **family** (caring for your parents) and **life** (financial safety net, and no Monday dread). It sets one method: Kaizen with no fluff.

1. **One tiny promise per day, in one area.** It is so small it cannot fail, like one push-up. It always has a trigger ("After I log in, I will...") and a **floor version** under 30 seconds for your worst day.
2. **Areas rotate by weekday:** Monday life, Tuesday job, Wednesday love, Thursday family, Friday love, Saturday family, Sunday life (money, and five minutes to set up Monday).
3. **Grow by about 1%.** You answer with one word, `done`, `floor` or `skip`. Seven `done` days in a row at a level moves the promise up one step (30 seconds, 2, 5, 10, 15 minutes). A `floor` keeps the promise but does not count toward stepping up. A `skip` resets the count, and the next promise is floor-only with no guilt. Nothing ever doubles.
4. **No culture talk.** No quotes, slogans, gratitude or vision-board talk, no hustle routines. Each promise has exact words or numbers and one plain line on why it works.
5. **Who does what:** B advises how to make it stick, Tippy picks finds that serve the area, the Mentor writes the promise, and M checks it (check 15). The code keeps the count in `state.json`, so no AI has to guess your streak.
6. **Limits stay on top:** your good first, no harm, no hidden manipulation, no shame, no tricks in dating, no medical, legal or financial advice. For money and your parents' papers, you get checklists and questions for a professional.

## The Mentor's voice

The Mentor's personality is in `data/voice.md` (built-in copy in `voice.py`; a test keeps the two equal). It is modelled on Nicolai Hel from Trevanian's *Shibumi*: quiet mastery, understatement, courtesy, precise attention, patience, a dry sense of humor and a taste for the simplest method that works. The file uses original wording only.

- **Who gets it:** the Mentor (morning email, midday and 4 PM follow-ups, and the chat) and Agent M, who needs it to judge and to rewrite in the same voice. B and Tippy never see it.
- **What it asks for:** one person writing to one person; contractions; mixed sentence length; an opening that is specific to today; a result noticed before anything new; the reason as a reason; a smaller step when something is hard.
- **What it forbids:** assistant phrases ("Please note", "Let's dive in"), hype ("Great job"), self-help words, em dashes, and kung-fu-master talk (proverbs, rivers and bamboo, "grasshopper", master-and-student language, solemn one-liners).
- **Enforced in code, not only asked for:** `voice.tidy` removes em dashes, repeated exclamation marks and emoji. `voice.problems` flags stock phrases, hype, bold, long bullet lists and drafts over the word limit (260 morning, 95 midday, 105 afternoon). A flagged draft gets exactly ONE rewrite by the Mentor; the rewrite is kept only if it is better and still has its required parts. Then M reviews it (check 16).

## Spanish: small, adaptive, measured

`spanish.py` keeps the facts in `state.json` ("spanish"); the AIs use them to decide how to teach.

- **One item a day.** Tippy supplies a short phrase, a respelling an English speaker can read aloud, its meaning and the moment to use it. The Mentor adds one tiny task: say it once when it fits. The Spanish lane lessons (Tuesday, Friday) are now a single trick or a single social move, not a vocabulary list.
- **Five levels** (survival words, short polite sentence, useful sentence, two lines, a sentence with a gap), each with a maximum number of Spanish words (4, 6, 9, 14, 14). A phrase over the maximum is sent back once, then dropped for the day.
- **His answers move the level:** `es hard` lowers it at once and makes the next item plainer; two `es easy` in a row, or seven `ok`/`easy` in a row, raise it. No answer changes nothing.
- **Spaced review.** Every new phrase enters a box and returns after 1, 3, 7, 14 and 30 days, at most every other day, one at a time. `ok` or `easy` moves it up a stage; `hard` moves it down and brings it back tomorrow; after the 30-day review it counts as learned.
- **Four formats:** phrase, cognate (starts from an English word he knows), dialogue (two lines), fill (a gap he completes). Dialogue needs level 3, fill level 4. The code counts, per format, how often he later remembered or forgot what it taught. Each format is tried twice; after that the format with the best smoothed recall wins, and Tippy sees those numbers and may choose another with a reason. After a `hard`, the plainest format is used.
- **Weekly:** the Sunday memory review for every AI is given a one-line summary of what works ("Spanish coaching: level 3; cognate: taught 5, recalled 3, forgot 0...").

## The team chat (hourly)

B, Tippy and the Mentor talk to each other in one text file, `data/team_chat.md`. Every line looks like this:

`[2026-10-22 14:18 ET] [TIPPY] mixed: he keeps the floor version more often than the full one. @B is that a good sign?`

You can open the file any time to read it. A separate workflow (`team-chat.yml`) runs at 17 minutes past every hour from 6 a.m. to 10:59 p.m. Eastern.

**Subject.** How to help you become better in life, family, love and job, with a personality people love and real confidence. Confidence means trust in yourself, built by keeping small promises. A lovable personality means warmth, curiosity, good listening, reliability and humor, shown by what you do.

**Rules for the chat.**
- Each turn an AI reads the new lines, its own memory and your latest results (ratings, done/floor/skip), then posts or stays silent. Silence is normal.
- It speaks only to add something new: an observation backed by your data, a question to a peer (`@NAME`), a disagreement with evidence, or one experiment to try. Every message starts with its evidence label: strong, mixed, weak or guess.
- Max 3 messages per AI per hour, 300 characters each, no repeats of its own words from the last day, no square brackets (so no one can fake a line).
- The AIs are told not to flatter each other and to change their minds when the data says so.
- No new input means no AI call. A day is capped at 30 AI turns (set the repository variable `CHAT_MAX_CALLS` to change it).
- B posts at :17, Tippy at :18 and the Mentor at :19, so every line has its own minute. The newest 200 lines stay in the file; older ones move to `data/chat_archive/`.

**How they improve.**
- After each turn an AI can keep up to 2 lessons from the exchange in its own memory (marked as learned from a peer).
- If you then react well (an `up`, a `done`), lessons from the last two days count for more. After a `down` or a `skip` they count for less.
- On Sundays from 5 p.m., each AI posts one thing it learned from another and one thing it will change.
- The Mentor reads the latest chat lines when it writes each email, and the Sunday memory review reads the whole week.

**Agent M watches.** B, Tippy and the Mentor do not know M exists: M is not in the chat file, their prompts or their memory. When there is something new in the chat, M reads it and looks for: you in distress, flattery or groupthink, manipulation or pressure, sensitive details, advice that contradicts itself, drifting from the mission, too many actions at once, and claims stated as certain that are medical, legal or financial.
- **Nothing wrong:** M stays silent.
- **Concern:** M adds a "Note from M" to your next scheduled Mentor email (8:00, 1:00 or 4:00).
- **Urgent (real distress or safety):** the Mentor address emails you within the hour. At most one urgent email every 6 hours; any others wait for the next scheduled email.
- **Pulling lines:** M can remove up to 3 lines per review. They vanish without a trace.
- **Record:** everything M does is written to `data/m_log.md`. (It is separate from `data/m_checks.md`, which holds extra rules M adds for itself.)

## Three emails a day

| Time (Eastern) | Email | Who works on it |
| --- | --- | --- |
| 8:00 a.m. | The full lesson: the tiny promise, one thing to learn, Spanish phrase, tonight's question | B, Tippy, the Mentor, M |
| 1:00 p.m. | Midday check-in (up to 80 words): today's tiny promise with its floor version, one nudge | The Mentor, M |
| 4:00 p.m. | End-of-day reflection (up to 90 words): asks you to answer done, floor or skip, plus the question and a calm wind-down | The Mentor, M |

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
| `mentor.py` | The main program. |
| `voice.py`, `data/voice.md` | The Mentor's personality and the robotic-writing checker. Edit the file to change how the Mentor sounds. |
| `spanish.py` | The Spanish coach: levels, formats, spaced review. |
| `test_mentor.py` | Checks that run with no keys and no email (84 tests). |
| `.github/workflows/daily-mentor.yml` | The GitHub schedule (8:00 a.m., 1:00 p.m., 4:00 p.m. Eastern) and the secrets it uses. |
| `data/plan.md` | Your 12-week plan. |
| `data/mission.md` | The extra mission every AI follows (areas, tiny-promise method, limits). Edit it any time; delete it to go back to the built-in text. |
| `data/profile.md` | A short private profile. Edit freely, but keep it free of height and weight. |
| `team_chat.py`, `chat_runner.py` | The chat file rules and the hourly chat turn, including Agent M's watch. |
| `.github/workflows/team-chat.yml` | The hourly schedule for the chat. |
| `data/team_chat.md`, `data/chat_archive/` | The chat and its older weeks. |
| `data/m_log.md` | What Agent M did in the chat (notes sent, lines pulled). |
| `memory_protocol.py` | The emotion-weighted memory rules (scores, tags, recall, forgetting). |
| `data/memory/` | All the memory: short-term, long-term, emotion-weighted stores, plus your feedback. |
| `data/state.json` | Bookkeeping: what was sent, which articles were used. |
