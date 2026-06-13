(function () {
  'use strict';

  var data = window.BIRD_DATA;
  var animals = data.animals;
  var venue = data.venue;

  // Precompute _pts (ms-stamped, sorted) for the map/live; metrics read .pings.
  animals.forEach(function (a) {
    a._pts = a.pings.map(function (p) {
      return { lat: p.lat, lng: p.lng, ms: TM.parseT(p.t), place: p.place || null };
    });
    a._pts.sort(function (x, y) { return x.ms - y.ms; });
  });

  // Global time bounds
  var allMs = [];
  animals.forEach(function (a) {
    if (a._pts.length) { allMs.push(a._pts[0].ms); allMs.push(a._pts[a._pts.length - 1].ms); }
  });
  var minMs = Math.min.apply(null, allMs);
  var maxMs = Math.max.apply(null, allMs);

  function getAnimal(id) {
    for (var i = 0; i < animals.length; i++) { if (animals[i].id === id) return animals[i]; }
    return null;
  }

  // Map
  var map = new TMMap('map', venue);
  map.setAnimals(animals);
  map.fitAll();

  // Header stats
  document.getElementById('stat-animals').textContent = animals.length;
  var activeCount = animals.filter(function (a) { return a.status === 'Transmitting'; }).length;
  document.getElementById('stat-active').textContent = activeCount;

  // Repo link
  document.getElementById('about-repo').href = 'https://github.com/wmolyneaux/TimeMachine';

  var selectedId = null;
  var sidebar; // assigned below; referenced by handleSelect

  // Single selection path shared by list clicks, map clicks and the close/clear buttons.
  function handleSelect(id) {
    selectedId = id;
    var btnClear = document.getElementById('btn-clear');
    if (id) {
      var animal = getAnimal(id);
      if (!animal) return;
      map.focus(id);
      map.emphasize(id);
      sidebar.renderProfile(animal, TM.metrics(animal.pings));
      btnClear.hidden = false;
    } else {
      sidebar.select(null);          // clears card highlight + profile DOM
      map.emphasize(null);
      btnClear.hidden = true;
    }
  }

  // Timeline
  var timeline = new TMTimeline({
    minMs: minMs,
    maxMs: maxMs,
    onChange: function (ms) { map.setTime(ms, selectedId); }
  });

  // Sidebar
  sidebar = new TMSidebar({
    data: data,
    onSelect: handleSelect,
    onFilterChange: function (idSet) {
      map.setVisible(idSet);
      if (selectedId && idSet.indexOf(selectedId) === -1) handleSelect(null);
      map.setTime(timeline.value(), selectedId);
    }
  });

  // Clicking a head/trail on the map behaves like clicking the list card.
  map.onSelect(function (id) {
    sidebar.select(id);
    handleSelect(id);
  });

  // Live mode
  var live = new TMLive({
    animals: animals,
    onTick: function (nowMs) {
      map.setTime(nowMs, selectedId);
      if (selectedId) {
        var animal = getAnimal(selectedId);
        if (animal) sidebar.update(animal, TM.metrics(animal.pings));
      }
    }
  });

  document.getElementById('tl-live').addEventListener('click', function () {
    var btn = this;
    var goingLive = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', goingLive ? 'true' : 'false');
    sidebar.liveMode = goingLive;
    if (goingLive) {
      timeline.setEnabled(false);
      live.start();
    } else {
      live.stop();
      timeline.setEnabled(true);
      timeline.setValueMs(maxMs);
      map.setTime(maxMs, selectedId);
    }
    if (selectedId) {
      var a = getAnimal(selectedId);
      if (a) sidebar.update(a, TM.metrics(a.pings));
    }
  });

  // About modal (toggle the hidden attribute; CSS handles [hidden])
  document.getElementById('btn-about').addEventListener('click', function () {
    document.getElementById('about').hidden = false;
  });
  document.getElementById('about-close').addEventListener('click', function () {
    document.getElementById('about').hidden = true;
  });

  // Mobile drawer
  document.getElementById('btn-menu').addEventListener('click', function () {
    document.getElementById('sidebar').classList.toggle('tm-sidebar--open');
  });

  // Clear selection
  document.getElementById('btn-clear').addEventListener('click', function () { handleSelect(null); });

  // Reset filters
  document.getElementById('btn-reset').addEventListener('click', function () { sidebar.reset(); });

  // Initial draw — full tracks, heads at latest, transmitting heads pulsing.
  map.setTime(maxMs, null);
})();
