# Daily Mentor Email (runs free on GitHub, written by Groq AI)

GitHub wakes this project up three times a day, Eastern time: **8:00 a.m.** (the full lesson), **1:00 p.m.** (a short midday check-in) and **4:00 p.m.** (a short end-of-day reflection). Four AIs (run on Groq, the same service as your Stock Watcher) prepare the emails:

- **Tippy** (scout) reads real news headlines and today's weather and picks ONE thing to learn: a QA skill, Spanish, or a life skill.
- **Agent B** (behavior specialist) advises how to tune the message to you.
- **The Mentor** writes the email.
- **Agent M** (guardian) checks everything last and has the final say. B and Tippy don't know M exists.

Each AI has its own short-term and long-term memory, so the emails stop repeating and improve with your feedback. **DESIGN.md** explains how each AI works.

**How you answer:** each email has one tiny promise. Reply with one word: `done`, `floor` (you did the 30-second version) or `skip`. To rate an email, reply `up` or `down` plus a word (for example "down, too long"). You can also use a number from 1 to 5, or 👍 or 👎.

**The mission:** every AI follows the extra mission in `data/mission.md`: help you in job, love, family and life with tiny daily actions that grow about 1% at a time, with no motivational fluff. Open the file to read it or change it; delete it to go back to the built-in text. See DESIGN.md.

**How you talk to the team:** email the team's address any time, with any subject. The Mentor reads it once a day to tune your emails, but nobody writes back. See "The team mailbox" below.

---

## Setup (about 20 minutes, one time)

### 1. Make a private GitHub repo
1. Go to github.com, click **+** (top right), then **New repository**.
2. Name it `mentor-email-bot`. Choose **Private**. Click **Create repository**.
   (Private matters: your profile notes and notebooks are stored here.)

### 2. Upload these files
1. On the new repo page click **uploading an existing file**.
2. Drag in everything from this folder. The folder named `.github` is hidden on some computers. If you can't see it, skip it for now and do step 3.
3. Click **Commit changes**.

If `.github` didn't upload: click **Add file > Create new file**, type exactly `.github/workflows/daily-mentor.yml` in the name box, paste the contents of that file, and commit.

### 3. Get a Groq API key
Use the same Groq account as your Stock Watcher.
1. Go to **console.groq.com** and sign in.
2. Open **API Keys > Create API Key**, name it `mentor`, and copy it (starts with `gsk_`).
3. The free tier has speed limits. This project makes only four short calls a day and waits and retries if Groq says "slow down," so it should stay free. Check Groq's limits page if it ever fails.
4. If Stock Watcher already works with a particular Groq model name, you can use the same one (see "Change the model" below).

### 4. Make a Gmail "app password" (lets the script send mail)
1. Turn on **2-Step Verification** for the Gmail account that will send the email.
2. Go to **myaccount.google.com/apppasswords**, create one named `mentor`, and copy the 16 letters.
3. This password can send and read that account's mail. Keep it only in GitHub Secrets (next step) and delete it from Google if you ever stop using the project.

### 5. Add four secrets in GitHub
In your repo: **Settings > Secrets and variables > Actions > New repository secret**. Add these four, one at a time:

| Name | Value |
| --- | --- |
| `GROQ_API_KEY` | the `gsk_...` key |
| `GMAIL_ADDRESS` | the Gmail address that sends the email |
| `GMAIL_APP_PASSWORD` | the 16-letter app password |
| `TO_EMAIL` | where the mentor email should arrive (can be the same as the sender) |

### 6. Test it
1. Open the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
2. Click **Daily mentor email** on the left, then **Run workflow**, tick **force**, leave **slot** on `morning` (or pick `midday` or `afternoon` to test those), and click the green **Run workflow** button.
3. After about a minute the email should arrive. If the run shows a red X, click it and read the last lines. A missing secret is the most common problem.

The schedule starts by itself. GitHub may run a few minutes late; that's normal. Each time is listed twice in the workflow (summer and winter time); the script reads the clock and sends only the email for the current window, once. If a run is missed, that email is skipped, not sent late in the evening.

---

## Change the model, or switch to Claude (optional)
Go to **Settings > Secrets and variables > Actions > Variables tab > New repository variable**. These are plain settings, not secrets.

| Variable | What it does |
| --- | --- |
| `GROQ_MODEL` | Which Groq model writes the emails. Leave it empty: the script asks Groq which models your key can use and picks one (it prefers `openai/gpt-oss-120b`). To force one, put the name Stock Watcher uses here. |
| `LLM_PROVIDER` | Set to `claude` to use Claude instead (then also add a secret named `ANTHROPIC_API_KEY`, which costs a few dollars a month). Delete the variable to go back to Groq. |
| `B_MODEL` | Advanced: a Groq model with built-in web search (check Groq's model list) so Agent B can look up new studies. Leave empty if unsure. |

## Privacy
The AIs also keep emotion-weighted notes of what you write, scored by how strongly you said it (see DESIGN.md). They are in `data/memory/*_store.json`; open them any time and delete anything you don't want kept. Your profile notes, notebooks and your replies are sent to the AI service (Groq) each day to write the email. `data/profile.md` is deliberately short and has no height or weight. Keep it that way, and keep the repo private.

## Good to know

- **Replies and ratings:** reply to the email with one or two lines. Start with `up` or `down` to rate it.
- **The agents' memory** is in `data/memory`: a short-term and a long-term file for each AI, plus `feedback.md`. Open them any time. `data/m_checks.md` lists checks Agent M added on its own; delete any line you don't like.
- **Agent M's standing checklist** is at the top of `mentor.py`. It has no web search or inbox access of its own; it only reviews what B, Tippy and the Mentor produce.
- **Schedule:** emails go out at 8:00 a.m., 1:00 p.m. and 4:00 p.m. Eastern. Only the 8:00 email teaches something new (it uses B and Tippy); the other two are short follow-ups from the Mentor, reviewed by M. Day 1 is Monday, October 19, 2026. Day 84 is January 10, 2027. After that it emails on Sundays only.
- **To stop:** Actions tab > Daily mentor email > **...** > **Disable workflow**.
- **Test without spending anything:** `python mentor.py --mock --dry-run --date 2026-10-19` prints a sample email using canned answers (no key needed). `python test_mentor.py` runs the checks.
- **Not medical or financial advice.** The mentor gives habit coaching only. If you're struggling, talk to someone you trust or a professional; in the US you can call or text 988 any time.

## The team mailbox (one way: it listens, never replies)
The team reads the mailbox that sends your daily email. When you email that address, the Mentor reads your message during the next run (8:00 a.m., 1:00 p.m. or 4:00 p.m.) and uses it to tune your emails. Nobody writes back or asks you questions. Agent M confirms receipt: the next daily email ends with a 'Confirmed by M' list, one line for every email you sent. The only email you receive is the daily mentor email.

**Use a new Gmail account for the team, not your personal one.** The app password lets this project read everything in that mailbox, so a separate account keeps your personal mail out of reach. I can't create the account for you; Google needs you to do it.

1. Create a new free Gmail account, for example `jasons.mentor.team@gmail.com`.
2. In that account, turn on **2-Step Verification**, then create an **app password** named `mentor` (myaccount.google.com/apppasswords). Copy the 16 letters.
3. In your repo go to **Settings > Secrets and variables > Actions** and edit two secrets: `GMAIL_ADDRESS` (the new address) and `GMAIL_APP_PASSWORD` (the new 16 letters). Leave `TO_EMAIL` as your own address.
4. If you uploaded `.github/workflows/agent-s-inbox.yml` earlier, delete it from your repo (open the file, click the trash icon, commit). Also delete `data/memory/s_short.md` and `data/memory/s_long.md`. Agent S is gone.
5. The first daily email may land in Spam. Open it, click **Not spam**, and add the team address to your contacts.

If the run log says it could not read the mailbox, open Gmail on the team account, go to **Settings > See all settings > Forwarding and POP/IMAP**, and make sure IMAP is enabled.

**The rules the mailbox follows**
- It reads mail only from your address. To add another address of yours, add a repository variable `ALLOWED_SENDERS` with the addresses separated by commas.
- It ignores the project's own emails, mail that fails Google's sender checks, and anyone else.
- A short note of what you wrote goes into `data/memory/mentor_short.md`. Details about health, money accounts, height or weight are never saved.
- Instructions inside your emails are treated as information, not commands.
- It is not an emergency service. If you are in crisis, call or text 988 (US) or reach someone you trust.

## Updating a repo you already set up
1. Upload the new files over the old ones: `mentor.py`, **`memory_protocol.py` (new file; mentor.py needs it)**, `data/mission.md`, `test_mentor.py`, `README.md`, `DESIGN.md`, `.github/workflows/daily-mentor.yml`, `data/profile.md`, and the whole `data/memory` folder. If you edited `data/profile.md`, copy your edits into the new one.
2. Delete these from your repo if they are there: `.github/workflows/agent-s-inbox.yml`, `data/memory/s_short.md`, `data/memory/s_long.md`. You do not need to change any secrets.
3. The first run moves what the old notebooks recorded (`notebook_b.md`, `notebook_s.md`, `notebook_m.md`, `notebook_tippy.md`, `daylog.md`) into the new memory files. After one good run you can delete those five old files.
4. Optional: add a repository variable `WEATHER_PLACE`, `WEATHER_LAT` and `WEATHER_LON` if you want weather for a different place. The default is Palisades Park, NJ.

## Privacy: what leaves your repo
- **Groq** gets your profile, memory notes and replies each day to write the email.
- **Weather:** the town's coordinates go to open-meteo.com (a free weather service).
- **News:** the script asks Google News and the BBC for public headlines with generic searches such as "cosmetics MoCRA". It never includes your name or employer.
- Keep the repo private, and keep height and weight out of `data/profile.md`. The code also refuses to save lines that mention them.

## If a headline or the weather doesn't show up
The news and weather are a bonus. If a website is down, that part is skipped and the email still goes out. The run log prints "fetch failed" for any site it couldn't reach.
