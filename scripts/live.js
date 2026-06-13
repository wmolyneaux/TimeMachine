window.TMLive = class TMLive {
  constructor({ animals, onTick, onFix }) {
    this.animals = animals;
    this.onTick = onTick || (() => {});
    this.onFix = onFix || (() => {});
    this._intervalId = null;
    this.active = false;
  }

  start() {
    if (this.active) return;
    this.active = true;

    this._intervalId = setInterval(() => {
      const now = Date.now();

      for (const animal of this.animals) {
        if (animal.status !== "Transmitting") continue;

        const pts = animal._pts;
        if (!pts || pts.length === 0) continue;

        const last = pts[pts.length - 1];

        // Generate a believable random step: ~tens of meters, biased to wander
        // ~0.0001° per 10m at mid-latitudes; use a random walk with slight persistence
        // Believable walking step (~tens of meters per 2.5s tick) with slight
        // directional persistence so the path wanders rather than jitters.
        const stepLat = (Math.random() - 0.5) * 0.00016; // ~±9 m
        const stepLng = (Math.random() - 0.5) * 0.00016;

        let biasLat = 0, biasLng = 0;
        if (pts.length >= 2) {
          const prev = pts[pts.length - 2];
          biasLat = (last.lat - prev.lat) * 0.3;
          biasLng = (last.lng - prev.lng) * 0.3;
        }

        const newLat = last.lat + stepLat + biasLat;
        const newLng = last.lng + stepLng + biasLng;
        const tISO = new Date(now).toISOString().slice(0, 16) + "Z"; // "YYYY-MM-DDThh:mmZ"

        // Append to _pts (map reads this) AND pings (metrics read this) so the
        // map head moves and the profile numbers update together.
        pts.push({ lat: newLat, lng: newLng, ms: now, t: tISO, place: null });
        animal.pings.push({ lat: newLat, lng: newLng, t: tISO });
        this.onFix(animal);
      }

      this.onTick(now);
    }, 2500);
  }

  stop() {
    if (!this.active) return;
    this.active = false;
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }
};
