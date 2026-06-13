#!/usr/bin/env python3
"""
TimeMachine — Bay Area mammal tracking data generator.

Produces `scripts/data.js` (a `window.BIRD_DATA` global so the app runs from a
plain file:// open with no server or fetch/CORS issues — the global keeps that
name for back-compat with the engine, but it now carries mammals).

Five collared land mammals roaming San Francisco and the greater Bay Area, each
with a recent (~3 week) telemetry history. Most recent fixes cluster near
SHACK15 (1 Ferry Building, 37.7955, -122.3937) so the map opens on the hackathon
venue; historical tracks fan out across the city parks, the Presidio and down
the Peninsula ridgelines.

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
        "Presidio Wildlife Watch", "Presidio of San Francisco",
        "Collared in the Presidio, Scout is one of San Francisco's resident urban "
        "coyotes. Like the city's small but established population he moves mostly "
        "after dark, threading park corridors and the northern waterfront — and on "
        "bold nights trotting all the way down to the Embarcadero.",
        "Scout covered an unusually long loop last night — out of the Presidio, along "
        "the marina and the piers, and right past the Ferry Building before dawn. "
        "Healthy movement for a city coyote holding a large territory.",
        "#f4a23b", "Transmitting",
        "mountain_lake",
        ["presidio_post", "crissy_field", "marina_green", "fort_mason",
         "aquatic_park", "russian_hill", "north_beach", "gg_conservatory"],
        ["lake_merced", "twin_peaks", "san_bruno_mtn"],
        "embarcadero", 20, 0,
    ),
    Mammal(
        "bandit", "Bandit", "Raccoon", "Procyon lotor", "Procyonidae",
        "Male", "Adult", 62, 8.2,
        "Embarcadero Urban Wildlife", "Telegraph Hill, San Francisco",
        "A waterfront raccoon whose nightly rounds loop between the lush Filbert Steps "
        "gardens on Telegraph Hill and the piers of the Embarcadero. Bandit is rarely "
        "more than a kilometre or two from the Ferry Building.",
        "Bandit stuck to his usual beat — down the Filbert Steps, a sweep of the piers, "
        "and a long stop around the Ferry Building's planters. A textbook compact urban "
        "home range.",
        "#6ec6ff", "Transmitting",
        "filbert_steps",
        ["coit_tower", "levis_plaza", "pier7", "embarcadero", "aquatic_park",
         "north_beach"],
        [],
        "shack15", 20, 0,
    ),
    Mammal(
        "pepper", "Pepper", "Striped Skunk", "Mephitis mephitis", "Mephitidae",
        "Male", "Subadult", 36, 2.8,
        "SoMa Wildlife Survey", "Yerba Buena Gardens, San Francisco",
        "A striped skunk denning in the green spaces of SoMa. Pepper forages a tight "
        "range through Yerba Buena Gardens, Rincon Hill and the small parks beside the "
        "Ferry Building, ambling at a deliberate skunk's pace.",
        "Pepper kept it slow and local — Yerba Buena Gardens to Rincon Hill, then the "
        "lawns by the Ferry Building. Short legs, small range, very routine.",
        "#b388ff", "Transmitting",
        "yerba_buena",
        ["rincon_hill", "soma", "south_park", "sue_bierman", "embarcadero"],
        [],
        "sue_bierman", 20, 0,
    ),
    Mammal(
        "ember", "Ember", "Gray Fox", "Urocyon cinereoargenteus", "Canidae",
        "Male", "Adult", 64, 4.6,
        "Lands End Carnivore Study", "Lands End, San Francisco",
        "A gray fox ranging the coastal scrub from Lands End into the Presidio — the "
        "only American canid that readily climbs trees. Ember's collar fell silent in "
        "the Presidio after eight nights.",
        "Ember's last good fixes trace the coastal bluffs from Lands End toward the "
        "Presidio. The collar has been quiet since — possibly a failed unit, possibly "
        "dense canopy blocking the uplink.",
        "#ff7a59", "Signal lost",
        "lands_end",
        ["sea_cliff", "baker_beach", "presidio_post", "mountain_lake", "crissy_field"],
        [],
        "presidio_post", 8, 2,
    ),
    Mammal(
        "willow", "Willow", "Black-tailed Deer", "Odocoileus hemionus columbianus", "Cervidae",
        "Male", "Adult", 150, 58.0,
        "Peninsula Deer Project", "Mount Sutro, San Francisco",
        "A Columbian black-tailed deer whose range covers the wooded hills of Mount "
        "Sutro, Twin Peaks and Golden Gate Park, with occasional forays down the "
        "Peninsula ridgelines. Willow's study collar completed its program this week.",
        "Willow's full record shows a classic west-side deer range — Mount Sutro and "
        "Twin Peaks, the green sweep of Golden Gate Park, and two long excursions south "
        "along the Peninsula ridges before the study collar was retired.",
        "#5ed1a5", "Track complete",
        "mount_sutro",
        ["twin_peaks", "tank_hill", "buena_vista", "stow_lake", "gg_conservatory"],
        ["san_bruno_mtn", "sweeney_ridge", "glen_canyon"],
        "gg_conservatory", 17, 3,
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


def night_path(m: Mammal, rng, is_last: bool) -> list[str]:
    """Choose the sequence of node keys an animal visits in one night."""
    den = m.den
    k = rng.randint(2, 4)
    pool = list(m.nodes)
    rng.shuffle(pool)
    chosen = pool[:k]
    # rare long excursion to the greater Bay Area
    if m.far and rng.random() < 0.18:
        chosen.append(rng.choice(m.far))
        rng.shuffle(chosen)
    path = [den] + chosen + [den]      # out from the den and back by dawn
    if is_last:
        path = [den] + chosen + [m.current]   # last night ends at the current fix
    return path


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
    rng = random.Random(f"{SEED}:{m.mid}")
    base = date(2026, 5, 1)            # arbitrary; the series is translated to TODAY below
    fixes = []                          # (datetime, lat, lng, place_or_None)

    for day in range(m.track_days):
        is_last = day == m.track_days - 1
        day_date = base + timedelta(days=day)

        if day > 0:                     # midday rest at the den
            rest = datetime(day_date.year, day_date.month, day_date.day, 12, 30) + \
                timedelta(minutes=rng.randint(-60, 60))
            fixes.append((rest,
                          round(P[m.den][0] + rng.gauss(0, JITTER_DEG * 1.5), 5),
                          round(P[m.den][1] + rng.gauss(0, JITTER_DEG * 1.5), 5), None))

        dusk = datetime(day_date.year, day_date.month, day_date.day, 19, 30) + \
            timedelta(minutes=rng.randint(-30, 50))
        nf, _ = night_fixes(m, night_path(m, rng, is_last), dusk, rng)
        fixes.extend(nf)

    fixes.sort(key=lambda f: f[0])

    # translate the whole series so the latest fix lands this morning
    # (or end_offset_days earlier for non-transmitting animals)
    target_last = datetime(TODAY.year, TODAY.month, TODAY.day, 5, 0) - \
        timedelta(days=m.end_offset_days, minutes=rng.randint(0, 40))
    shift = target_last - fixes[-1][0]
    fixes = [(t + shift, lat, lng, place) for (t, lat, lng, place) in fixes]

    pings = []
    last_t = None
    for t, lat, lng, place in fixes:
        if last_t is not None and t <= last_t:
            t = last_t + timedelta(minutes=2)
        last_t = t
        ping = {"lat": lat, "lng": lng, "t": t.strftime("%Y-%m-%dT%H:%MZ")}
        if place:
            ping["place"] = place
        pings.append(ping)

    # force the final fix exactly onto the current node
    pings[-1]["lat"], pings[-1]["lng"] = P[m.current]
    pings[-1]["place"] = NAMES.get(m.current)
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
        out["animals"].append({
            "id": m.mid, "name": m.name, "commonName": m.common_name,
            "scientificName": m.scientific_name, "family": m.family,
            "sex": m.sex, "lifeStage": m.life_stage,
            "lengthCm": m.length_cm, "weightKg": m.weight_kg,
            "tagger": m.tagger, "taggedLocation": m.tagged_location,
            "taggedDate": (TODAY - timedelta(days=m.end_offset_days + m.track_days)).isoformat(),
            "status": m.status, "color": m.color, "bio": m.bio, "note": m.note,
            "distanceKm": round(dist, 1), "homeRange": NAMES.get(m.den),
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
