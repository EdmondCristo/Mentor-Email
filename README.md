# Daily Mentor Email (runs free on GitHub, written by Claude)

Every morning at about 6:45 a.m. Eastern, GitHub wakes this project up. Four Claude "agents" prepare one short email and send it to you:

- **Agent B** (behavior specialist) looks up a recent behavior-science finding and advises how to tune the message.
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

### 3. Get a Claude API key (this is what replaces Gemini)
1. Go to **console.anthropic.com** and sign in.
2. Add a few dollars of credit under **Billing**. The API is billed separately from your Claude chat plan.
3. Open **API Keys > Create Key** and copy it (starts with `sk-ant-`).
4. Tip: in Billing, set a monthly spend limit. Each day uses about four short Claude calls; my rough estimate is a few dollars a month, so check the Console after the first week.

### 4. Make a Gmail "app password" (lets the script send mail)
1. Turn on **2-Step Verification** for the Gmail account that will send the email.
2. Go to **myaccount.google.com/apppasswords**, create one named `mentor`, and copy the 16 letters.
3. This password can send and read that account's mail. Keep it only in GitHub Secrets (next step) and delete it from Google if you ever stop using the project.

### 5. Add four secrets in GitHub
In your repo: **Settings > Secrets and variables > Actions > New repository secret**. Add these four, one at a time:

| Name | Value |
| --- | --- |
| `ANTHROPIC_API_KEY` | the `sk-ant-...` key |
| `GMAIL_ADDRESS` | the Gmail address that sends the email |
| `GMAIL_APP_PASSWORD` | the 16-letter app password |
| `TO_EMAIL` | where the mentor email should arrive (can be the same as the sender) |

### 6. Test it
1. Open the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
2. Click **Daily mentor email** on the left, then **Run workflow**, tick **force**, and click the green **Run workflow** button.
3. After about a minute the email should arrive. If the run shows a red X, click it and read the last lines. A missing secret is the most common problem.

The email schedule starts the next morning by itself. GitHub may run a few minutes late; that's normal.

---

## Good to know

- **Replies:** reply to the email and write one or two lines. The script reads only replies from `TO_EMAIL` whose subject starts with "Re: Day..." or "Re: Maintenance check-in".
- **The agents' memory** is the files in the `data` folder. Open them any time. `data/m_checks.md` lists checks Agent M added on its own; delete any line you don't like.
- **Agent M's standing checklist** is at the top of `mentor.py`. It has no web search or inbox access of its own; it only reviews what B, S and the Mentor produce.
- **Schedule:** Day 1 is Monday, October 19, 2026. Day 84 is January 10, 2027. After that it emails on Sundays only.
- **To stop:** Actions tab > Daily mentor email > **...** > **Disable workflow**.
- **Test without spending anything:** `python mentor.py --mock --dry-run --date 2026-10-19` prints a sample email using canned answers (no key needed). `python test_mentor.py` runs the checks.
- **Not medical or financial advice.** The mentor gives habit coaching only. If you're struggling, talk to someone you trust or a professional; in the US you can call or text 988 any time.
