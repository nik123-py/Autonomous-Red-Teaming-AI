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
practice lab and proves each success with a saved record of the request it sent. Along
the way we found two interesting things that are worth writing about.

---

## What we achieved (5 concrete things)

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

---

## The honest part (so you don't get caught out)

- This is a **practice lab on one computer**, not a real network. The attacks always
  succeed because the practice sites are deliberately broken and never fight back.
- Because the attacks always succeed, the "learning" part doesn't have much to prove
  here — a simple rule does almost as well as the trained agent. That's expected and
  we say so.
- Other researchers (papers called **GAP**, **PenGym**, **CRLF**, 2024–2025) already
  did the "agent attacks a real lab" idea, and more thoroughly. So that part is **not
  new**. What's genuinely ours is the specific lesson in point 5 and the "keep
  receipts" evidence log.
- The chatbot feature doesn't work (no AI model connected) and some API keys were
  accidentally saved in the code and should be changed.

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
