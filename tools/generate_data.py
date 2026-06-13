#!/usr/bin/env python3
"""
TimeMachine — Bay Area mammal tracking data generator.

Produces `scripts/data.js` (a `window.BIRD_DATA` global so the app runs from a
plain file:// open with no server or fetch/CORS issues — the global keeps that
name for back-compat with the engine, but it now carries mammals).

Five collared land mammals, all tagged at the Ferry Building (SHACK15, 1 Ferry
Building, 37.7955, -122.3937) and tracked for the last 6 hours. Every track starts
at the Ferry Building and fans out into a tight downtown range, so the map opens on
the hackathon venue with the animals clustered around it.

The data is ILLUSTRATIVE. Species, locations and home-range behaviour are real
and well documented for the Bay Area; the individual animals, names, collar
programs, dates and GPS fixes are synthetic.

Deterministic: a fixed RNG seed + a hardcoded "today" make regeneration stable.

    python tools/generate_data.py
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

TODAY = date(2026, 6, 13)
SEED = 20260613

SHACK15 = (37.7955, -122.3937)

# All five animals are collared at the Ferry Building and tracked for the last 6 hours.
# END_TS is the real "now" at generation time so the window is genuinely recent; the
# track GEOMETRY stays deterministic via the per-animal SEED — only the absolute
# timestamps shift with the clock.
END_TS = datetime.utcnow().replace(second=0, microsecond=0)
WINDOW = timedelta(hours=6)

STEP_KM = 0.32          # one fix roughly every ~320 m along a night's path
JITTER_DEG = 0.00045    # ~50 m organic GPS scatter on interpolated fixes


# --------------------------------------------------------------------------- #
# Geo helpers
# --------------------------------------------------------------------------- #
def haversine_km(a, b) -> float:
    r = 6371.0088
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def lerp(a, b, t):
    return a + (b - a) * t


# Named Bay Area places (lat, lng). Real coordinates.
P = {
    "shack15":        (37.7955, -122.3937),
    "embarcadero":    (37.7968, -122.3955),
    "sue_bierman":    (37.7972, -122.3968),
    "pier7":          (37.8016, -122.3989),
    "levis_plaza":    (37.8019, -122.4015),
    "filbert_steps":  (37.8009, -122.4053),
    "coit_tower":     (37.8024, -122.4058),
    "north_beach":    (37.8009, -122.4100),
    "russian_hill":   (37.8017, -122.4180),
    "aquatic_park":   (37.8077, -122.4216),
    "fort_mason":     (37.8060, -122.4309),
    "marina_green":   (37.8066, -122.4430),
    "crissy_field":   (37.8038, -122.4650),
    "presidio_post":  (37.7989, -122.4662),
    "mountain_lake":  (37.7872, -122.4690),
    "baker_beach":    (37.7936, -122.4836),
    "sea_cliff":      (37.7886, -122.4880),
    "lands_end":      (37.7825, -122.5057),
    "gg_conservatory":(37.7726, -122.4604),
    "stow_lake":      (37.7699, -122.4750),
    "buena_vista":    (37.7686, -122.4413),
    "tank_hill":      (37.7603, -122.4477),
    "twin_peaks":     (37.7544, -122.4477),
    "mount_sutro":    (37.7585, -122.4585),
    "glen_canyon":    (37.7405, -122.4430),
    "lake_merced":    (37.7270, -122.4920),
    "san_bruno_mtn":  (37.6920, -122.4350),
    "sweeney_ridge":  (37.6030, -122.4480),
    "rincon_hill":    (37.7880, -122.3899),
    "yerba_buena":    (37.7847, -122.4029),
    "south_park":     (37.7817, -122.3934),
    "soma":           (37.7810, -122.3980),
    # Shared downtown congregation nodes — multiple animals route through these,
    # so their tracks overlap and markers converge (esp. the Tenderloin).
    "tenderloin":     (37.7840, -122.4135),
    "civic_center":   (37.7790, -122.4170),
    "un_plaza":       (37.7800, -122.4140),
    # Compact NE-downtown nodes (all within ~1.5 km of SHACK15) — keeps every
    # animal's range small and overlapping instead of sprawling across the city.
    "nob_hill":       (37.7930, -122.4140),
    "chinatown":      (37.7941, -122.4078),
    "union_square":   (37.7880, -122.4075),
    "jackson_sq":     (37.7969, -122.4029),
    "portsmouth_sq":  (37.7946, -122.4060),
}


@dataclass
class Mammal:
    mid: str
    name: str
    common_name: str
    scientific_name: str
    family: str
    sex: str
    life_stage: str
    length_cm: int
    weight_kg: float
    tagger: str
    tagged_location: str
    bio: str
    note: str                       # canned "field note" fallback (no API key)
    color: str
    status: str                     # Transmitting | Track complete | Signal lost
    den: str                        # home/rest node key
    nodes: list[str]                # frequently used range nodes
    far: list[str]                  # rare excursion targets (greater Bay Area)
    current: str                    # final / most-recent fix node key
    track_days: int                 # nights of history to generate
    end_offset_days: int            # days before TODAY the last fix sits


MAMMALS: list[Mammal] = [
    Mammal(
        "scout", "Scout", "Coyote", "Canis latrans", "Canidae",
        "Male", "Adult", 95, 13.5,
        "Downtown Wildlife Watch", "Nob Hill, San Francisco",
        "Scout is one of San Francisco's bold urban coyotes, denning in the quiet "
        "blocks of Nob Hill. He holds a compact downtown territory — the alleys of "
        "Chinatown and Union Square, a nightly pass through the Tenderloin, and a dawn "
        "slip down to the Embarcadero.",
        "Scout kept a tight downtown circuit last night — Nob Hill to Chinatown, "
        "through the Tenderloin, and back. A small, well-defended urban territory.",
        "#f4a23b", "Transmitting",
        "nob_hill",
        ["chinatown", "union_square", "tenderloin", "north_beach", "russian_hill"],
        [],
        "embarcadero", 14, 0,
    ),
    Mammal(
        "bandit", "Bandit", "Raccoon", "Procyon lotor", "Procyonidae",
        "Male", "Adult", 62, 8.2,
        "Embarcadero Urban Wildlife", "Telegraph Hill, San Francisco",
        "A waterfront raccoon whose nightly rounds loop between the lush Filbert Steps "
        "gardens on Telegraph Hill and the piers of the Embarcadero. Bandit is rarely "
        "more than a few blocks from the Ferry Building.",
        "Bandit stuck to his usual beat — down the Filbert Steps, a sweep of the piers, "
        "and a long stop around the Ferry Building's planters. A textbook compact urban "
        "home range.",
        "#6ec6ff", "Transmitting",
        "filbert_steps",
        ["coit_tower", "levis_plaza", "pier7", "embarcadero", "jackson_sq"],
        [],
        "shack15", 14, 0,
    ),
    Mammal(
        "pepper", "Pepper", "Striped Skunk", "Mephitis mephitis", "Mephitidae",
        "Male", "Subadult", 36, 2.8,
        "SoMa Wildlife Survey", "Yerba Buena Gardens, San Francisco",
        "A striped skunk denning in the green spaces of SoMa. Pepper keeps a very tight "
        "range — Yerba Buena Gardens, the SoMa side streets and the edge of the "
        "Tenderloin — ambling at a deliberate skunk's pace and rarely covering ground.",
        "Pepper kept it slow and local — Yerba Buena Gardens to the Tenderloin edge and "
        "back. Short legs, tiny range, very routine.",
        "#b388ff", "Transmitting",
        "yerba_buena",
        ["soma", "south_park", "tenderloin", "civic_center"],
        [],
        "soma", 12, 0,
    ),
    Mammal(
        "ember", "Ember", "Gray Fox", "Urocyon cinereoargenteus", "Canidae",
        "Male", "Adult", 64, 4.6,
        "Downtown Carnivore Study", "Chinatown, San Francisco",
        "A gray fox that surprised researchers by turning up in the dense blocks around "
        "Chinatown and the Tenderloin — the only American canid that readily climbs. "
        "Ember's collar fell silent after eight nights.",
        "Ember's last good fixes loop through Chinatown and the Tenderloin. The collar "
        "has been quiet since — possibly a failed unit, possibly the urban canyon "
        "blocking the uplink.",
        "#ff7a59", "Signal lost",
        "portsmouth_sq",
        ["chinatown", "nob_hill", "tenderloin", "union_square"],
        [],
        "tenderloin", 8, 2,
    ),
    Mammal(
        "willow", "Willow", "Black-tailed Deer", "Odocoileus hemionus columbianus", "Cervidae",
        "Male", "Adult", 150, 58.0,
        "Urban Deer Project", "Russian Hill, San Francisco",
        "A black-tailed deer that wandered into the city and settled on the steep green "
        "slopes of Russian Hill and Telegraph Hill — a small, cautious range of gardens "
        "and quiet stairways. Willow's study collar completed its program this week.",
        "Willow's record shows a tight hillside range — Russian Hill to the Filbert "
        "Steps greenery and back. Very little ground covered; a careful, contained "
        "urban deer.",
        "#5ed1a5", "Track complete",
        "russian_hill",
        ["north_beach", "filbert_steps", "coit_tower"],
        [],
        "north_beach", 12, 3,
    ),
]


def densify(a, b, rng):
    """Points from a->b (excluding a, including b) with organic jitter."""
    seg = haversine_km(a, b)
    n = max(1, round(seg / STEP_KM))
    out = []
    for j in range(1, n + 1):
        t = j / n
        lat = lerp(a[0], b[0], t)
        lng = lerp(a[1], b[1], t)
        if j != n:  # keep the destination node exact
            lat += rng.gauss(0, JITTER_DEG)
            lng += rng.gauss(0, JITTER_DEG)
        out.append((round(lat, 5), round(lng, 5)))
    return out


# Downtown animals route THROUGH a shared congregation node on MOST nights, so
# their tracks overlap and markers converge on the Tenderloin. Per-animal config:
#   prob  — chance a given night includes a congregation waypoint
#   nodes — weighted choices ("tenderloin" dominant, civic_center/un_plaza rarer)
# This is a thin config overlay over the generalized night_path mechanism; the
# Tenderloin is inserted mid-route (not at the den/current endpoints) so the path
# visibly threads through it. ember/willow do NOT get a CONGREGATION entry — they
# carry "tenderloin" in their `far` list and additionally get a small dedicated
# rare-drift chance (RARE_DRIFT_P) so they OCCASIONALLY appear downtown, not nightly.
CONGREGATION = {
    "scout":  {"prob": 0.6, "nodes": ["tenderloin"] * 6 + ["civic_center", "union_square"]},
}

# Rare-drift: any non-trio animal with "tenderloin" in its `far` list gets this
# extra small chance per night to thread the Tenderloin, so it shows up there
# occasionally even if the generic far-excursion roll keeps picking other nodes.
RARE_DRIFT_P = 0.14


def night_path(m: Mammal, rng, is_last: bool) -> list[str]:
    """Choose the sequence of node keys an animal visits in one night."""
    den = m.den
    # Roaming scales with activity so total travel stays small and consistent with
    # the step counts: low-activity animals barely move (0-1 nearby node), others
    # make a short 1-2 node loop.
    act = ACTIVITY_PROFILE.get(m.mid, "normal")
    # Frequent REST nights (k=0 = barely leaves the den) keep total travel low and
    # make movement vary day-to-day like the step counts do.
    k = rng.choice([0, 0, 1]) if act == "low" else (
        rng.choice([0, 1, 1, 2]) if act == "high" else rng.choice([0, 1, 1]))
    pool = list(m.nodes)
    rng.shuffle(pool)
    chosen = pool[:k]
    # rare long excursion to the greater Bay Area
    if m.far and rng.random() < 0.18:
        chosen.append(rng.choice(m.far))
        rng.shuffle(chosen)

    # Downtown trio: thread the night through a shared congregation waypoint on
    # MOST nights so tracks overlap and converge (esp. the Tenderloin).
    cfg = CONGREGATION.get(m.mid)
    drift_node = None
    if cfg and rng.random() < cfg["prob"]:
        drift_node = rng.choice(cfg["nodes"])
    elif (not cfg) and "tenderloin" in m.far and rng.random() < RARE_DRIFT_P:
        # ember/willow: rare downtown drift to the shared congregation point.
        drift_node = "tenderloin"
    if drift_node is not None:
        # insert into the MIDDLE of the route (a genuine mid-route waypoint with
        # stops on either side where possible), not the den/current endpoints.
        insert_at = len(chosen) // 2 if chosen else 0
        chosen = chosen[:insert_at] + [drift_node] + chosen[insert_at:]

    path = [den] + chosen + [den]      # out from the den and back by dawn
    if is_last:
        path = [den] + chosen + [m.current]   # last night ends at the current fix
    return path


# Daily-steps activity profile per animal. Pedometer-style counts, distinct from
# the GPS track. high -> mostly 3000-10000; normal -> 500-6000; low -> mostly
# 5-400 with at least two days dropping into 5-30 ("some animals move only a few
# steps in a day"). All counts clamped to [0, 10000].
ACTIVITY_PROFILE = {
    "scout":  "high",
    "willow": "high",
    "bandit": "normal",
    "pepper": "low",
    "ember":  "low",
}

STEPS_DAYS = 14   # length of the stepsByDay history (oldest -> newest)


def daily_steps(m: Mammal):
    """Deterministic step counts for the 6-hour tracking window.

    Uses its own seeded stream — random.Random(f"{SEED}:{m.mid}:steps") — independent
    of the GPS track. Returns (steps_total_6h, steps_by_hour[6], activity): high
    animals are busy; low animals barely move (a couple of hours only a handful of
    steps).
    """
    activity = ACTIVITY_PROFILE[m.mid]
    rng = random.Random(f"{SEED}:{m.mid}:steps")

    def clamp(v):
        return max(0, min(10000, int(round(v))))

    by_hour = []
    if activity == "high":
        for _ in range(6):
            by_hour.append(clamp(rng.randint(300, 1800)))
    elif activity == "normal":
        for _ in range(6):
            by_hour.append(clamp(rng.randint(80, 900)))
    else:  # "low": mostly tiny, with a couple of near-stationary hours (~5 steps)
        for _ in range(6):
            by_hour.append(clamp(rng.randint(0, 120)))
        for i in rng.sample(range(6), 2):
            by_hour[i] = clamp(rng.randint(0, 8))

    return clamp(sum(by_hour)), by_hour, activity


# Movement model per animal: (walk/trot km/h baseline, sprint km/h max, burst prob).
# Sprints are based on documented species top speeds (coyote ~35 mph, deer ~35 mph,
# gray fox ~30 mph, raccoon ~15 mph, skunk ~10 mph) so the speed metrics are credible.
SPEED = {
    "scout":  (5.0, 56, 0.12),
    "bandit": (2.6, 24, 0.08),
    "pepper": (2.2, 16, 0.06),
    "ember":  (4.5, 49, 0.10),
    "willow": (5.5, 60, 0.10),
}


def night_fixes(m: Mammal, path, start_dt, rng):
    """Walk a night's path, deriving timestamps from realistic per-step speeds.

    Most steps are an amble/trot; a small fraction are running bursts (giving a
    believable top speed), and each arrival at a named stop adds a stationary
    dwell fix (speed -> 0) — the way a real collar keeps pinging while an animal
    feeds or beds down. Distance (feet walked) is pure geometry; only the timing,
    and therefore the speed metrics, changes.
    """
    walk, run, burst_p = SPEED[m.mid]
    fixes = [(start_dt, P[path[0]][0], P[path[0]][1], NAMES.get(path[0]))]
    clock = start_dt
    prev = P[path[0]]
    for i in range(len(path) - 1):
        seg = densify(P[path[i]], P[path[i + 1]], rng)
        for k, (lat, lng) in enumerate(seg):
            dist_m = haversine_km(prev, (lat, lng)) * 1000
            spd = run * rng.uniform(0.55, 0.95) if rng.random() < burst_p \
                else walk * rng.uniform(0.5, 1.7)
            clock += timedelta(seconds=dist_m / (max(spd, 0.4) * 1000 / 3600))
            place = NAMES.get(path[i + 1]) if k == len(seg) - 1 else None
            fixes.append((clock, round(lat, 5), round(lng, 5), place))
            prev = (lat, lng)
        # dwell at the stop just reached
        clock += timedelta(minutes=rng.uniform(6, 30))
        fixes.append((clock, P[path[i + 1]][0], P[path[i + 1]][1], None))
        prev = P[path[i + 1]]
    return fixes, clock


def build_track(m: Mammal):
    """A single 6-hour walk: every animal is collared at the Ferry Building and has
    wandered its tight downtown range over the past six hours. Movement scales with
    activity — low animals mostly rest near the start, high animals roam more — so
    the tracks fan out from SHACK15 and stay short and contained."""
    rng = random.Random(f"{SEED}:{m.mid}")
    walk, run, burst_p = SPEED[m.mid]
    act = ACTIVITY_PROFILE.get(m.mid, "normal")
    if act == "high":
        p_move, dwell = 0.8, (6, 18)
    elif act == "low":
        p_move, dwell = 0.3, (30, 80)
    else:
        p_move, dwell = 0.6, (12, 32)

    start = END_TS - WINDOW
    nodes = list(m.nodes) or [m.den]
    fixes = [(start, P["shack15"][0], P["shack15"][1], "SHACK15 · Ferry Building")]
    clock = start
    prev = P["shack15"]
    guard = 0
    while clock < END_TS and guard < 500:
        guard += 1
        arrived_key = None
        if rng.random() < p_move:
            arrived_key = rng.choice(nodes)
            broke = False
            for (lat, lng) in densify(prev, P[arrived_key], rng):
                if clock >= END_TS:
                    broke = True
                    break
                dist_m = haversine_km(prev, (lat, lng)) * 1000
                spd = run * rng.uniform(0.55, 0.95) if rng.random() < burst_p \
                    else walk * rng.uniform(0.5, 1.7)
                clock += timedelta(seconds=dist_m / (max(spd, 0.4) * 1000 / 3600))
                fixes.append((clock, round(lat, 5), round(lng, 5), None))
                prev = (lat, lng)
            if broke:
                arrived_key = None
        # dwell where we ended up (label it if we just arrived at a named node)
        clock += timedelta(minutes=rng.uniform(*dwell))
        fixes.append((clock, round(prev[0], 5), round(prev[1], 5),
                      NAMES.get(arrived_key) if arrived_key else None))

    fixes = [f for f in fixes if f[0] <= END_TS]
    if len(fixes) < 2:
        fixes.append((END_TS, round(prev[0], 5), round(prev[1], 5), None))

    pings = []
    last_t = None
    for t, lat, lng, place in fixes:
        if last_t is not None and t <= last_t:
            t = last_t + timedelta(seconds=30)
        last_t = t
        ping = {"lat": lat, "lng": lng, "t": t.strftime("%Y-%m-%dT%H:%MZ")}
        if place:
            ping["place"] = place
        pings.append(ping)

    # anchor exactly: first fix = the Ferry Building start, last fix = END_TS ("now")
    pings[0]["place"] = "SHACK15 · Ferry Building"
    pings[-1]["t"] = END_TS.strftime("%Y-%m-%dT%H:%MZ")
    return pings


# Human-readable labels for named places (shown on fix popups).
NAMES = {
    "shack15": "SHACK15 · Ferry Building", "embarcadero": "Embarcadero",
    "sue_bierman": "Sue Bierman Park", "pier7": "Pier 7", "levis_plaza": "Levi's Plaza",
    "filbert_steps": "Filbert Steps", "coit_tower": "Coit Tower", "north_beach": "North Beach",
    "russian_hill": "Russian Hill", "aquatic_park": "Aquatic Park", "fort_mason": "Fort Mason",
    "marina_green": "Marina Green", "crissy_field": "Crissy Field",
    "presidio_post": "Presidio Main Post", "mountain_lake": "Mountain Lake",
    "baker_beach": "Baker Beach", "sea_cliff": "Sea Cliff", "lands_end": "Lands End",
    "gg_conservatory": "GG Park · Conservatory", "stow_lake": "Stow Lake",
    "buena_vista": "Buena Vista Park", "tank_hill": "Tank Hill", "twin_peaks": "Twin Peaks",
    "mount_sutro": "Mount Sutro", "glen_canyon": "Glen Canyon", "lake_merced": "Lake Merced",
    "san_bruno_mtn": "San Bruno Mountain", "sweeney_ridge": "Sweeney Ridge",
    "rincon_hill": "Rincon Hill", "yerba_buena": "Yerba Buena Gardens",
    "south_park": "South Park", "soma": "SoMa",
    "tenderloin": "Tenderloin", "civic_center": "Civic Center",
    "un_plaza": "UN Plaza",
    "nob_hill": "Nob Hill", "chinatown": "Chinatown", "union_square": "Union Square",
    "jackson_sq": "Jackson Square", "portsmouth_sq": "Portsmouth Square",
}


def main():
    out = {
        "generatedAt": TODAY.isoformat(),
        "venue": {"name": "SHACK15", "address": "1 Ferry Building, Suite 201, San Francisco, CA 94111",
                  "lat": SHACK15[0], "lng": SHACK15[1]},
        "disclaimer": ("Illustrative demo data. Species, locations and home-range behaviour "
                       "are real and well documented for the San Francisco Bay Area; the "
                       "individual animals, names, collar programs, dates and GPS fixes are "
                       "synthetic."),
        "animals": [],
    }

    for m in MAMMALS:
        pings = build_track(m)
        dist = sum(haversine_km((pings[i - 1]["lat"], pings[i - 1]["lng"]),
                                (pings[i]["lat"], pings[i]["lng"]))
                   for i in range(1, len(pings)))
        steps_today, steps_by_day, activity = daily_steps(m)
        out["animals"].append({
            "id": m.mid, "name": m.name, "commonName": m.common_name,
            "scientificName": m.scientific_name, "family": m.family,
            "sex": m.sex, "lifeStage": m.life_stage,
            "lengthCm": m.length_cm, "weightKg": m.weight_kg,
            "tagger": m.tagger, "taggedLocation": m.tagged_location,
            "taggedDate": (TODAY - timedelta(days=m.end_offset_days + m.track_days)).isoformat(),
            "status": m.status, "color": m.color, "bio": m.bio, "note": m.note,
            "distanceKm": round(dist, 1), "homeRange": NAMES.get(m.den),
            "stepsToday": steps_today, "stepsByDay": steps_by_day, "activity": activity,
            "pings": pings,
        })

    total = sum(len(a["pings"]) for a in out["animals"])
    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    banner = ("/* AUTO-GENERATED by tools/generate_data.py — do not edit by hand.\n"
              "   Regenerate with:  python tools/generate_data.py\n"
              f"   {len(out['animals'])} mammals, {total} fixes, centred on SHACK15. */\n")
    js = banner + "window.BIRD_DATA = " + payload + ";\n"

    with open("scripts/data.js", "w", encoding="utf-8") as fh:
        fh.write(js)

    print(f"Wrote scripts/data.js — {len(out['animals'])} mammals, {total} fixes, "
          f"{len(js) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
