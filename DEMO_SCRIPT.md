# TimeMachine — Demo & Pitch Script

**Logline:** *A live map of every wild mammal in a city — and a time machine to replay where they've been.*

**Runtime:** ~4 minutes (3 min demo + 1 min the business). All numbers below are the
**real values the app computes** from the demo dataset, so they match what's on screen.

**On screen at open:** the TimeMachine app, centered on **SHACK15 (1 Ferry Building)**,
five collared mammals clustered around the venue, the **time scrubber** at the bottom.

> Optional cold-open B-roll: a 5-second cinematic intro clip already exists in `assets/intro.mp4`.

---

## 0:00 — Cold open (the hook)

> *[Stand in front of the map, zoomed to SHACK15. Five dots pulse around the Ferry Building.]*

**SAY:**
"Right now, without anyone noticing, this building is surrounded by wildlife.
A coyote slept in the Presidio today. A raccoon spent last night working the piers
fifty feet from where we're standing. A skunk is in the park next door.

We tagged five of them. This is **TimeMachine** — and it doesn't just show you where
they are. It lets you rewind."

---

## 0:30 — The live demo

### Beat 1 — Meet the animals *(0:30)*
> *[Pan the sidebar: Scout the coyote, Bandit the raccoon, Pepper the skunk, Ember the gray fox, Willow the deer.]*

**SAY:** "Five mammals, five collars, three weeks of fixes — all within a few miles of here.
Green is transmitting, grey is a completed study, **red is a lost signal**. Hold that thought."

### Beat 2 — Open a profile, hit the metrics *(0:50)*
> *[Click **Scout** the coyote. The map flies to his track; the profile slides in.]*

**SAY:** "This is Scout, an adult coyote collared in the Presidio. Here's what matters —
the two numbers every wildlife manager actually acts on:

- **Distance walked: 152 miles in three weeks** — almost **25,000 feet just last night.**
- **Average speed on the move: 4.1 miles an hour** — and he **hit 17 crossing the Marina.**

Distance and speed. That's the heartbeat. A coyote that suddenly stops moving is a coyote
that's been hit by a car. A coyote sprinting at 3 a.m. just got chased — or chased something."

### Beat 3 — Travel through time *(1:25)*
> *[Grab the scrubber, drag it back three weeks, then press **Play**. The tracks animate; the dots walk the city night by night.]*

**SAY:** "This is the time machine. I'm replaying three weeks of movement in ten seconds.
Watch Scout commute from the Presidio along the waterfront — every night, a little bolder,
until last night he walked right past this building. **You can't see a corridor in a
spreadsheet. You can see it here.**"

### Beat 4 — Go live *(1:55)*
> *[Toggle **LIVE**. The clock jumps to now; fresh fixes start dropping in real time.]*

**SAY:** "And this is now. In live mode the collars keep reporting — new fixes, updated
speed, the moment it happens. At one animal it's a pet. At ten thousand, it's an
**early-warning system.**"

### Beat 5 — Ask Claude *(2:15)*
> *[Open Ember the gray fox — the **red, signal-lost** one. Click **Ask Claude → Field Notes**.]*

**SAY:** "Ember's collar went silent in the Presidio two days ago. A biologist would have
to read hundreds of GPS rows to know why. Instead — Claude reads the whole track and tells us:

> *'Ember's last fixes trace the coastal bluffs from Lands End toward the Presidio, then stop
> dead. Movement didn't slow gradually — it cut off. Likely a failed collar or canopy blocking
> the uplink, not a mortality.'*

That's the unlock. **The dots aren't the product. The model that reads a million tracks for you is.**"

---

## 2:45 — Why this matters

**SAY:** "We are pushing cities into habitat faster than ever, and the result is collisions —
literal and otherwise. In the U.S. alone there are **over a million deer–vehicle crashes a
year**, billions in damage, hundreds of human deaths. The four carnivores we tagged tonight —
coyote, raccoon, skunk, fox — are the **top rabies-vector species in North America.** Knowing
where animals go, how fast, and when that changes isn't a nice-to-have. It's public safety,
public health, and the difference between a species recovering or not."

---

## 3:05 — Scale

**SAY:** "Here's the part I love. **We built this engine for sharks. Then birds. This afternoon
we pointed it at five mammals around this building** — and it just worked, because to TimeMachine
a track is a track. The animal is a config file.

Tag hardware is collapsing — satellite IoT, cellular, LoRa — cheap enough to put on millions of
animals. The bottleneck was never the collars. It's that nobody can read the firehose. **TimeMachine
is the layer that makes a million animals legible:** distance, speed, dwell, home range, and
anomalies computed in-stream, and Claude on top to turn it into plain English. Five collars or
five million — same screen."

---

## 3:30 — Who this is for

**SAY (governments):** "**Governments** are the anchor. Wildlife and parks agencies for endangered-species
recovery and corridor protection. **Departments of transportation** — our speed-and-path data shows
*exactly* where animals cross roads, so you build the wildlife crossing in the right place.
**Public health** for zoonotic early warning. **Animal control** for urban-coyote conflict and
mortality alerts."

**SAY (private):** "And **private industry** pays too. **Insurers** price collision risk from real
movement near roads. **Utilities and energy** owe endangered-species impact studies on every wind
farm and transmission line — today that's slow and manual; this automates the monitoring.
**Ranching** gets predator early-warning. **Developers and ESG teams** get a verifiable biodiversity
audit trail. Same data, two checkbooks."

---

## 3:50 — Close

**SAY:** "Five animals around one building tonight. The exact same screen is a national wildlife
network tomorrow. **TimeMachine turns movement into foresight** — for the agencies protecting
species, and the companies that have to coexist with them.

Rewind, watch, act. Thank you."

---

# Appendix A — Q&A talking points

- **"Is the data real?"** The *species, locations, home-range behavior and speeds are real and
  documented for the SF Bay Area.* The individual animals, names, collar IDs, dates and GPS fixes
  are **synthetic** for this demo — generated by a reproducible script (`tools/generate_data.py`).
  Production ingests real collars (Vectronic, Lotek, cellular/satellite tags) and standards like
  Movebank.
- **"How is this different from existing trackers (Movebank, OCEARCH)?"** Those store and plot data.
  Our wedge is the **decision layer**: in-stream metrics + automatic anomaly detection +
  natural-language query and field notes via Claude, so a non-technical agency analyst gets answers,
  not CSVs. The time-scrubber UX makes patterns (corridors, range shifts) visible at a glance.
- **"What's the moat?"** Not the map — anyone can draw dots. It's the model layer that makes scale
  legible, plus the multi-species, animal-agnostic engine (we proved the pivot speed live).
- **"Privacy / poaching risk?"** Endangered-species locations are access-controlled and can be
  fuzzed/delayed — a real concern OCEARCH handles too. Worth naming proactively.
- **"Business model?"** B2G/B2B SaaS: per-tag ingestion + seat-based analytics, with premium
  anomaly/alerting and the Claude query layer. Government contracts anchor; private compliance scales.

# Appendix B — The metrics, defined (what the numbers mean)

| Metric | Definition | Why a customer cares |
|---|---|---|
| **Feet walked** | Sum of great-circle distance between consecutive fixes (shown in ft + miles) | Home-range size, energy expenditure, habitat quality |
| **Avg speed (on the move)** | Mean of per-segment speeds while moving (≥0.3 mph) | Behavioral baseline; deviation = stress / disturbance |
| **Top speed** | Fastest sustained segment (GPS-sampled, outliers filtered) | Flight/pursuit events; predation or human disturbance |
| **Last-night distance** | Feet walked in the most recent ~14 h | Daily activity; the headline "is it healthy/active" number |
| **Speed → 0 (derived alert)** | No movement beyond GPS noise for N hours | **Mortality / immobilization alert** |

**Demo-day reference numbers (live-computed):**

| Animal | Species | Status | Feet walked | Avg (moving) | Top | Last night |
|---|---|---|---|---|---|---|
| Scout | Coyote | Transmitting | ~803,000 ft (152 mi) | 4.1 mph | 17 mph | ~24,900 ft |
| Bandit | Raccoon | Transmitting | ~225,000 ft (43 mi) | 2.6 mph | 15 mph | ~5,600 ft |
| Pepper | Striped Skunk | Transmitting | ~333,000 ft (63 mi) | 1.9 mph | 12 mph | ~18,300 ft |
| Ember | Gray Fox | Signal lost | ~240,000 ft (46 mi) | 3.5 mph | 16 mph | — (silent) |
| Willow | Black-tailed Deer | Track complete | ~492,000 ft (93 mi) | 4.3 mph | 18 mph | — (study ended) |

# Appendix C — Demo-day checklist

- [ ] Open on SHACK15, zoom framed so all five animals are visible.
- [ ] Scrubber pulled to the start before you begin (so Play has somewhere to go).
- [ ] LIVE mode tested once beforehand (it appends fresh fixes in real time).
- [ ] Claude Field Notes: API key set, **or** rely on the built-in canned fallback (works offline).
- [ ] Network check — Leaflet basemap tiles load from a CDN.
