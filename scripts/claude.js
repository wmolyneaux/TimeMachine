window.TMClaude = {
  _key: null,

  hasKey() {
    return !!this._getKey();
  },

  clearKey() {
    localStorage.removeItem('tm_anthropic_key');
    this._key = null;
  },

  _getKey() {
    if (this._key) return this._key;
    const stored = localStorage.getItem('tm_anthropic_key');
    if (stored) {
      this._key = stored;
      return stored;
    }
    const prompted = prompt('Enter your Anthropic API key for Claude Field Notes:');
    if (prompted && prompted.trim()) {
      localStorage.setItem('tm_anthropic_key', prompted.trim());
      this._key = prompted.trim();
      return this._key;
    }
    return null;
  },

  fieldNotes(animal, metrics) {
    const key = this._getKey();
    if (!key) {
      return Promise.resolve(animal.note);
    }

    const recentPlaces = animal.pings
      .filter(p => p.place)
      .slice(-3)
      .map(p => p.place)
      .join(', ');

    const prompt = `Write a brief naturalist field note about this animal.

Species: ${animal.commonName} (${animal.scientificName})
Status: ${animal.status}
Sex: ${animal.sex}
Life stage: ${animal.lifeStage}
Recent locations: ${recentPlaces || 'none recorded'}
Total distance: ${Math.round(metrics.feet).toLocaleString()} ft (${metrics.miles.toFixed(1)} mi)
Average speed on the move: ${metrics.avgMph.toFixed(1)} mph
Top speed: ${metrics.topMph.toFixed(1)} mph
Last night distance: ${Math.round(metrics.lastDistFeet).toLocaleString()} ft

Write 2-3 sentences in a naturalist's voice, noting behavior, habitat use, and movement patterns.`;

    return fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': key,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 300,
        messages: [{ role: 'user', content: prompt }]
      })
    })
    .then(res => {
      if (!res.ok) throw new Error('API error');
      return res.json();
    })
    .then(data => {
      return data.content[0].text;
    })
    .catch(() => {
      return animal.note;
    });
  }
};
