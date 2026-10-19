# Daily Mentor Email (runs free on GitHub, written by Groq AI)

Every morning at about 6:45 a.m. Eastern, GitHub wakes this project up. Four AI "agents" (run on Groq, the same service as your Stock Watcher) prepare one short email and send it to you:

- **Agent B** (behavior specialist) draws on classic behavior-science ideas and advises how to tune the message. Groq's standard models can't search the web, so B says so and sticks to well-established research (see "Optional" below for live search).
- **Agent S** studies you from your replies and its notebook, and advises the same.
- **The Mentor** writes the email (about 150 words) from B's and S's advice.
- **Agent M** (guardian) checks everything last and has the final say. B and S don't know M exists.

You answer by **replying to the email**. Agent S reads your replies the next morning.

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
2. Click **Daily mentor email** on the left, then **Run workflow**, tick **force**, and click the green **Run workflow** button.
3. After about a minute the email should arrive. If the run shows a red X, click it and read the last lines. A missing secret is the most common problem.

The email schedule starts the next morning by itself. GitHub may run a few minutes late; that's normal.

---

## Change the model, or switch to Claude (optional)
Go to **Settings > Secrets and variables > Actions > Variables tab > New repository variable**. These are plain settings, not secrets.

| Variable | What it does |
| --- | --- |
| `GROQ_MODEL` | Which Groq model writes the emails. Leave it empty: the script asks Groq which models your key can use and picks one (it prefers `openai/gpt-oss-120b`). To force one, put the name Stock Watcher uses here. |
| `LLM_PROVIDER` | Set to `claude` to use Claude instead (then also add a secret named `ANTHROPIC_API_KEY`, which costs a few dollars a month). Delete the variable to go back to Groq. |
| `B_MODEL` | Advanced: a Groq model with built-in web search (check Groq's model list) so Agent B can look up new studies. Leave empty if unsure. |

## Privacy
Your profile notes, notebooks and your replies are sent to the AI service (Groq) each day to write the email. `data/profile.md` is deliberately short and has no height or weight. Keep it that way, and keep the repo private.

## Good to know

- **Replies:** reply to the email and write one or two lines. The script reads only replies from `TO_EMAIL` whose subject starts with "Re: Day..." or "Re: Maintenance check-in".
- **The agents' memory** is the files in the `data` folder. Open them any time. `data/m_checks.md` lists checks Agent M added on its own; delete any line you don't like.
- **Agent M's standing checklist** is at the top of `mentor.py`. It has no web search or inbox access of its own; it only reviews what B, S and the Mentor produce.
- **Schedule:** Day 1 is Monday, October 19, 2026. Day 84 is January 10, 2027. After that it emails on Sundays only.
- **To stop:** Actions tab > Daily mentor email > **...** > **Disable workflow**.
- **Test without spending anything:** `python mentor.py --mock --dry-run --date 2026-10-19` prints a sample email using canned answers (no key needed). `python test_mentor.py` runs the checks.
- **Not medical or financial advice.** The mentor gives habit coaching only. If you're struggling, talk to someone you trust or a professional; in the US you can call or text 988 any time.
