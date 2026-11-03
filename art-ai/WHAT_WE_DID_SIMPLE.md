# ART-AI — what we actually did, in plain words

No jargon where I can avoid it. Where I can't, every term is explained at the
bottom in the **Concepts** section.

---

## The project in one sentence

We built a program that tries to "hack" a set of practice websites running on your
own computer, learns which order of steps works best, and — importantly — actually
sends real requests to those websites instead of pretending.

That's it. Everything below is detail.

---

## The one-paragraph version

The project started as a demo that *looked* like it worked but didn't. The learning
part was broken (it played worse than random guessing). Two of its scanners made up
their results instead of checking anything. We fixed the learning, replaced the fake
scanners with real ones, and then built a mode where the agent genuinely attacks the
practice lab and proves each success with a saved record of the request it sent. Then we
added a guard to the practice sites so attacks could actually fail, and measured when the
learning is worth anything at all. Along the way we found three things worth writing
about — including one where the honest answer was "this made it worse.

---

## What we achieved (8 concrete things)

### 1. We fixed the "brain" so it actually learns

Before: the agent won **2%** of the time. Random guessing won **49%**. So the
"smart" agent was much worse than luck.

After: the agent wins **96%** of the time, and we can prove that's near the best
score mathematically possible on this problem.

*Why it was broken:* it was rewarded for an action that looked successful but didn't
actually make progress, so it kept repeating that useless action forever. We removed
that trap and gave it a proper goal.

### 2. We caught the program lying about what it found

- The **port scanner** (the part that checks which doors on a computer are open)
  wasn't checking anything — it guessed using a math trick on the address. It reported
  two doors open that were actually closed, and missed every door that was really open.
- The **vulnerability scanner** reported the same three fake weaknesses for every
  website, with fake ID numbers like `CVE-2023-ZZZZZ` (ZZZZZ is literally a
  "fill-this-in-later" placeholder nobody filled in). It even flagged the program's
  own backend as vulnerable, which it never tested.

We replaced both with real checks. Now it only reports something if it actually saw
proof — for example, it only claims "this site leaks the password file" if the
response really contained the contents of that file.

### 3. We made the agent attack for real, and keep receipts

The old agent never touched the practice websites — it just rolled dice. The new
"live" mode sends a real request for every action and only counts a win when the
website actually responds the way a real successful attack would. Every single step
is written to a log file with the exact request sent and the exact proof, so anyone
can check that the attack really happened and wasn't made up.

### 4. We showed the "textbook" difficulty scores are wrong here

There are industry-standard scores (CVSS, EPSS) that are supposed to tell you how
likely a weakness is to be exploitable. We used them to *guess* how hard each attack
would be (guesses ranged from 13% to 81% likely to work).

Then we actually tried each attack 30 times. Every single one worked **100%** of the
time. So the official scores were badly off — in one case they said the key attack was
only 13% likely when it actually worked every time.

The honest takeaway: those scores describe "the internet in general," not "this
specific unpatched website in front of you."

### 5. We found that the *map*, not the *odds*, was the real problem

This is the most interesting result.

The simulation assumed that once you break into *one* website, you're "logged in"
everywhere — like one master key for a whole building. But the practice lab is six
*separate* buildings. A key to one doesn't open the others.

Because of this wrong assumption, the agent that trained in simulation completely
**failed** the first time it attacked for real (0% success) — it kept trying to use a
key from one site on a different site. Once we fixed the map to say "each building has
its own lock," it worked perfectly.

The lesson: a simulation can't catch its own bad assumptions. You only find them when
you test against the real thing.

### 6. We gave the practice sites a way to fight back — and found out when learning actually pays off

This is the result most worth putting in the paper.

We added a "guard" to the practice sites. It blocks some attempts outright, locks you
out after repeated tries, and limits how fast you can knock. Then we asked one question:
now that attacks can fail, does the trained agent beat a simple fixed rule?

The answer turned out to depend entirely on **whether the guard is equally strict
everywhere**:

| Guard setup | Simple fixed rule | Trained agent | Difference |
|---|---|---|---|
| Equally strict on every site | wins **60%** | wins **32%** | trained agent is **worse** |
| Stricter on some sites than others | wins **32%** | wins **100%** | trained agent is **+68 points better** |

(The two 32% figures are a coincidence, not a typo — they describe different things: the
trained agent under an even guard, and the fixed rule under an uneven one. Each row is 25
attempts per side. In the second row the margin is wide enough that it isn't luck; in the
first row the agent is genuinely losing, and we report that rather than hiding it.)

*Why:* if every door is equally hard to open, there is nothing to be clever about — you
just keep pushing on whichever door you happen to be standing at. Learning only pays off
when some doors are easier than others, because only then is there a **route** worth
finding. The agent's advantage comes from choosing *where* to attack, not from attacking
better.

We could not tune our way around this, and we didn't try to. It's a property of the
problem, not a flaw in the agent.

*The failure we also report:* we built a version that remembers "this site keeps blocking
me, give up on it." It did **worse** — 0% success instead of 32%. Remembering the blocks
made the agent abandon sites it should have kept trying. We left that result in the paper
instead of deleting it.

### 7. We measured how good the built-in "guesser" models are — nobody ever had

The project shipped machine-learning models that rank which exploit to try first. Nobody
had ever tested them on examples they hadn't already seen, so there was no honest accuracy
number anywhere.

We tested them properly (train on 8,000 records, test on 2,000 the model never saw):

- **92 out of 100 correct** on unseen examples (0.918).
- Always guessing the single most common answer gets **58 out of 100** (0.5765). So the
  model genuinely adds **+34 points**, it isn't just riding the most common category.
- Its weak spot: the `remote` category, where it only catches **71%** of cases. That
  category has only 632 examples out of 10,000, so the model has seen too few of them.

The number the project previously implied (0.948) was measured on data the model was
probably trained on, which always flatters a model. We report both and say which is which.

### 8. Our own tests were lying to us too — the same way the scanner was

Embarrassing, and worth stating because it's the same disease as point 2.

Our test suite had 42 checks. The function that recorded a failed check only **wrote the
failure down** — it never actually made the test fail. So the standard test command
printed `5 passed` whether the checks inside had passed or not. Green lights, no matter
what.

We proved it by deliberately writing a check that must fail: the old code reported
`1 passed`, the fixed code correctly fails.

A second problem: when the practice lab wasn't running, some checks reported a **failure**
rather than saying "skipped — the lab is off." That makes a working system look broken. Now
skips are counted separately from passes, so a skip can never be mistaken for a pass.

---

## The honest part (so you don't get caught out)

- This is a **practice lab on one computer**, not a real network. With the guard turned
  off, attacks always succeed, because the practice sites are deliberately broken. The
  guard in point 6 is something we added ourselves, not a real defence product, and it
  does not learn or adapt to the attacker.
- With the guard off, the attacks always succeed, so the "learning" part doesn't have
  much to prove — a simple rule does almost as well as the trained agent. That's
  expected and we say so. Point 6 is the one setting where learning clearly wins, and
  only because the guard is uneven there.
- Other researchers (papers called **GAP**, **PenGym**, **CRLF**, 2024–2025) already
  did the "agent attacks a real lab" idea, and more thoroughly. So that part is **not
  new**. What's genuinely ours is the lesson in point 5, the
  "learning only helps when defences are uneven" result in point 6, and the "keep
  receipts" evidence log.
- The chatbot feature doesn't work — no AI model is connected to it.
- One real API key (for Google's Gemini) was typed directly into the code and committed.
  It is still readable in the project's saved history, so it has to be **cancelled at
  Google**, not just deleted from the file — deleting it from today's code does not remove
  it from the history. To be exact about what did *not* happen: the `.env` secrets file was
  never committed at all. Only that one key in `main.py` was exposed.
- The **dashboard is a demo, not the experiment.** The research numbers all come from the
  scripts in `backend/experiments/`. The dashboard still uses the old rough guesswork
  numbers, so clicking around the web interface will not reproduce any result in the
  paper. We say this in the paper rather than letting a reader assume otherwise.

---

## Concepts (the terms, explained once)

**Agent** — the program making decisions (which attack to try next).

**Reinforcement learning (RL)** — teaching a program by reward and punishment. It
tries things, gets points for good outcomes, loses points for bad ones, and over many
attempts learns which choices earn the most points. Like training a dog with treats.

**Q-learning** — one specific recipe for RL. It keeps a table of "how good is each
action in each situation" and updates those numbers as it learns. (The table was the
thing that was broken — it had only 9 entries, meaning it had barely learned anything.)

**MDP (Markov Decision Process)** — the formal name for "a situation where you're in
some state, you pick an action, something happens with some probability, and you move
to a new state." Hacking fits this: you have some access, you try something, it works
or doesn't, your access changes. RL is the standard tool for MDPs.

**State** — the agent's current situation: what access it has, which sites it has
found, where it currently is. The old version only tracked "access level" (4 options),
which was too little to be useful. We expanded it.

**Reward** — the points. We kept it simple: a small penalty per step (to encourage
speed) and a big reward for reaching full admin control. The old version gave a
huge bonus for an unrelated thing, which confused the agent — we removed that.

**Value iteration** — a math method that calculates the *perfect* strategy exactly,
when the problem is small enough. We use it as the "100% score" line to measure how
close our agent gets. (Our agent reaches 93% of perfect.)

**Simulation vs. live** —
- *Simulation* = the agent decides outcomes by rolling dice against a guessed
  probability. Fast, safe, but possibly wrong.
- *Live* = the agent sends a real request to a real (practice) website and the real
  response decides the outcome. Slower, but true.

**Oracle** — the specific check that decides "did this attack actually succeed?"
It has to be based on real proof. Example: "the login attack worked" is only true if
the server actually handed back an admin token. Not a guess — a yes/no based on the
real response.

**Guard (we call it the "defender")** — code we added that makes the practice sites push
back: it blocks a share of attempts, locks you out after repeated failures, and limits how
fast you can try. It only ever makes attacks *fail*; it can never hand the agent a success
it didn't earn. It does not learn or adapt, so it is not a real blue-team opponent.

**Baseline (the "simple fixed rule")** — a dumb comparison opponent that always does the
same obvious thing in the same order, with no learning. If the trained agent can't beat
this, the learning isn't worth anything. Reporting the gap against a baseline is the
difference between "our agent got 100%" and a result that actually means something.

**Held-out test** — judging a model only on examples it was never shown during training.
Testing a model on data it already learned from is like marking your own homework with the
answer sheet open: the score looks good and tells you nothing. This is why point 7 reports
0.918 rather than the flattering 0.948.

**Evidence log** — a file where we record every action: what request was sent, what
the server replied, and the proof that justified counting it as a success. This is what
makes "the agent really attacked" checkable instead of just claimed.

**Sim-to-real gap** — the difference between how well something works in simulation
versus in reality. Measuring this gap honestly is the main point of the project.

**Zero-shot transfer** — taking an agent trained only in simulation and dropping it
into the real task *without extra training*, to see if what it learned still works.
(Ours failed at first due to the "map" problem, then worked perfectly after the fix.)

**CVSS / EPSS** — industry scoring systems for software weaknesses. CVSS rates how
*severe* a weakness is; EPSS estimates how *likely it'll be attacked in the wild*.
Neither actually tells you "will this exact attack work on this exact site" — which is
the point of finding #4.

**Port scanner** — a tool that checks which network "doors" (ports) on a computer are
open, and what service is behind each.

**Vulnerability (vuln) scanner** — a tool that checks a website for known weaknesses
(like SQL injection, where you trick a site's database into revealing data).

**CVE / CWE** —
- *CVE* = a unique ID for one specific publicly-known vulnerability
  (e.g. `CVE-2021-41773`). You should never make these up.
- *CWE* = the *category* of weakness (e.g. CWE-89 = "SQL injection"). We report these
  because they accurately describe what we saw, without inventing a fake CVE number.

**The lab** — six deliberately-insecure practice websites (Juice Shop, DVWA, WebGoat,
VAmPI, bWAPP, and a custom Flask app) running in Docker containers on your own machine.
They exist specifically for people to practice security testing safely.
