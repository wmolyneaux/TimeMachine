window.TMMap = (function() {
  'use strict';

  function TMMap(elId, venue) {
    this._map = L.map(elId, {
      center: [venue.lat, venue.lng],
      zoom: 13,
      zoomControl: true,
      attributionControl: true
    });

    // Basemaps (light, keyless)
    var streets = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(this._map);

    var light = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    });

    var terrain = L.tileLayer('https://tile.opentopomap.org/{z}/{x}/{y}.png', {
      attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
      maxZoom: 17
    });

    var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      maxZoom: 19
    });

    L.control.layers({
      'Streets': streets,
      'Light': light,
      'Terrain': terrain,
      'Satellite': satellite
    }, null, { position: 'bottomright' }).addTo(this._map);

    // SHACK15 marker
    var shackIcon = L.divIcon({
      className: 'tm-shack-icon',
      html: '<div class="tm-shack-pin">SHACK15</div>',
      iconSize: [80, 30],
      iconAnchor: [40, 15]
    });
    L.marker([venue.lat, venue.lng], { icon: shackIcon })
      .addTo(this._map)
      .bindPopup('<b>' + venue.name + '</b><br>' + venue.address);

    this._venue = venue;
    this._animalLayers = {};
    this._visibleIds = null;
    this._currentTime = null;
    this._focusId = null;
    this._selectCb = null;
    this._emphasizedId = null;
  }

  TMMap.prototype.setAnimals = function(animals) {
    var self = this;

    // Remove old layers
    for (var id in this._animalLayers) {
      if (this._animalLayers.hasOwnProperty(id)) {
        var layers = this._animalLayers[id];
        if (layers.ghost) this._map.removeLayer(layers.ghost);
        if (layers.trail) this._map.removeLayer(layers.trail);
        if (layers.stops) this._map.removeLayer(layers.stops);
        if (layers.head) this._map.removeLayer(layers.head);
      }
    }
    this._animalLayers = {};

    animals.forEach(function(animal) {
      var pts = animal._pts;
      if (!pts || pts.length === 0) return;

      var color = animal.color;
      var trailLatLngs = pts.map(function(p) { return [p.lat, p.lng]; });

      // Ghost polyline: persistent faint full track (never collapsed), drawn under the bright trail
      var ghost = L.polyline(trailLatLngs, {
        color: color,
        weight: 2,
        opacity: 0.22
      }).addTo(self._map);

      // Trail polyline (bright, traveled-portion line on top)
      var trail = L.polyline(trailLatLngs, {
        color: color,
        weight: 3,
        opacity: 0.8
      }).addTo(self._map);

      // Named stop dots
      var stopMarkers = [];
      pts.forEach(function(p) {
        if (p.place) {
          var marker = L.circleMarker([p.lat, p.lng], {
            radius: 4,
            color: color,
            fillColor: color,
            fillOpacity: 0.8,
            weight: 1
          }).bindTooltip(p.place, { permanent: false, direction: 'top' });
          stopMarkers.push(marker);
        }
      });
      var stopsGroup = L.layerGroup(stopMarkers).addTo(self._map);

      // Head marker
      var lastPt = pts[pts.length - 1];
      var head = L.circleMarker([lastPt.lat, lastPt.lng], {
        radius: 8,
        color: color,
        fillColor: color,
        fillOpacity: 1,
        weight: 2,
        className: 'tm-head' + (animal.status === 'Transmitting' ? ' tm-head--live' : '')
      }).addTo(self._map);

      // Click handler
      (function(animalId) {
        trail.on('click', function() { if (self._selectCb) self._selectCb(animalId); });
        head.on('click', function() { if (self._selectCb) self._selectCb(animalId); });
      })(animal.id);

      self._animalLayers[animal.id] = {
        ghost: ghost,
        trail: trail,
        stops: stopsGroup,
        head: head,
        pts: pts,
        animal: animal
      };
    });

    // Apply visibility if set
    if (this._visibleIds) {
      this.setVisible(this._visibleIds);
    }

    // Apply current time if set
    if (this._currentTime !== null) {
      this.setTime(this._currentTime, this._focusId);
    }
  };

  TMMap.prototype.setVisible = function(idSet) {
    idSet = (idSet instanceof Set) ? idSet : new Set(idSet);
    this._visibleIds = idSet;
    for (var id in this._animalLayers) {
      if (this._animalLayers.hasOwnProperty(id)) {
        var layers = this._animalLayers[id];
        var visible = idSet.has(id);
        if (layers.ghost) {
          if (visible) {
            this._map.addLayer(layers.ghost);
          } else {
            this._map.removeLayer(layers.ghost);
          }
        }
        if (layers.trail) {
          if (visible) {
            this._map.addLayer(layers.trail);
          } else {
            this._map.removeLayer(layers.trail);
          }
        }
        if (layers.stops) {
          if (visible) {
            this._map.addLayer(layers.stops);
          } else {
            this._map.removeLayer(layers.stops);
          }
        }
        if (layers.head) {
          if (visible) {
            this._map.addLayer(layers.head);
          } else {
            this._map.removeLayer(layers.head);
          }
        }
      }
    }
  };

  TMMap.prototype.setTime = function(ms, focusId) {
    this._currentTime = ms;
    if (focusId !== undefined) this._focusId = focusId;

    for (var id in this._animalLayers) {
      if (this._animalLayers.hasOwnProperty(id)) {
        var layers = this._animalLayers[id];
        var pts = layers.pts;
        var animal = layers.animal;

        // Check if visible
        if (this._visibleIds && !this._visibleIds.has(id)) continue;

        // Find bracketing fixes
        var before = null;
        var after = null;
        for (var i = 0; i < pts.length; i++) {
          if (pts[i].ms <= ms) {
            before = pts[i];
          }
          if (pts[i].ms >= ms && after === null) {
            after = pts[i];
          }
        }

        if (before === null) {
          // Not started yet - empty the bright trail and hide the head,
          // but keep the faint ghost (full track) visible so the path stays findable.
          if (layers.ghost && !this._map.hasLayer(layers.ghost)) this._map.addLayer(layers.ghost);
          if (layers.trail) layers.trail.setLatLngs([]);
          if (layers.head) this._map.removeLayer(layers.head);
          continue;
        }

        // Ensure head is on map
        if (!this._map.hasLayer(layers.head)) {
          this._map.addLayer(layers.head);
        }

        // Interpolate position
        var headLat, headLng;
        if (after === null || after === before) {
          headLat = before.lat;
          headLng = before.lng;
        } else {
          var t = (ms - before.ms) / (after.ms - before.ms);
          headLat = before.lat + (after.lat - before.lat) * t;
          headLng = before.lng + (after.lng - before.lng) * t;
        }

        layers.head.setLatLng([headLat, headLng]);

        // Update trail up to current time
        var trailLatLngs = [];
        for (var j = 0; j < pts.length; j++) {
          if (pts[j].ms <= ms) {
            trailLatLngs.push([pts[j].lat, pts[j].lng]);
          } else {
            // Interpolate last segment
            if (j > 0) {
              var prev = pts[j - 1];
              var t2 = (ms - prev.ms) / (pts[j].ms - prev.ms);
              trailLatLngs.push([
                prev.lat + (pts[j].lat - prev.lat) * t2,
                prev.lng + (pts[j].lng - prev.lng) * t2
              ]);
            }
            break;
          }
        }
        layers.trail.setLatLngs(trailLatLngs);

        // Update head class for live pulsing
        var atLatest = before === pts[pts.length - 1];
        var isLive = animal.status === 'Transmitting' && atLatest;
        var headEl = layers.head.getElement();
        if (headEl) {
          if (isLive) {
            headEl.classList.add('tm-head--live');
          } else {
            headEl.classList.remove('tm-head--live');
          }
        }
      }
    }

    // Pan to focus if set: only when the focused head leaves the view, and without animation (avoids per-frame pan jank)
    if (focusId && this._animalLayers[focusId]) {
      var focusHead = this._animalLayers[focusId].head;
      if (focusHead && this._map.hasLayer(focusHead)) {
        var headLatLng = focusHead.getLatLng();
        if (!this._map.getBounds().pad(-0.1).contains(headLatLng)) {
          this._map.panTo(headLatLng, { animate: false });
        }
      }
    }
  };

  TMMap.prototype.focus = function(id) {
    var layers = this._animalLayers[id];
    if (!layers) return;

    var pts = layers.pts;
    if (pts.length === 0) return;

    var latLngs = pts.map(function(p) { return [p.lat, p.lng]; });
    var bounds = L.latLngBounds(latLngs);
    this._map.fitBounds(bounds, { padding: [50, 50] });
    this.emphasize(id);
  };

  TMMap.prototype.emphasize = function(id) {
    this._emphasizedId = id;
    for (var animalId in this._animalLayers) {
      if (this._animalLayers.hasOwnProperty(animalId)) {
        var layers = this._animalLayers[animalId];
        var selectedOrAll = (id === null || animalId === id);
        var opacity = selectedOrAll ? 1.0 : 0.25;
        if (layers.ghost) {
          layers.ghost.setStyle({ opacity: selectedOrAll ? 0.22 : 0.08 });
        }
        if (layers.trail) {
          layers.trail.setStyle({ opacity: selectedOrAll ? 1.0 : 0.2 });
        }
        if (layers.head) {
          layers.head.setStyle({ opacity: opacity });
        }
        if (layers.stops) {
          layers.stops.eachLayer(function (mk) {
            if (mk.setStyle) mk.setStyle({ opacity: selectedOrAll ? 0.8 : 0.15, fillOpacity: selectedOrAll ? 0.8 : 0.15 });
          });
        }
      }
    }
  };

  TMMap.prototype.fitAll = function(idSet) {
    if (idSet && !(idSet instanceof Set)) idSet = new Set(idSet);
    var allLatLngs = [];
    for (var id in this._animalLayers) {
      if (this._animalLayers.hasOwnProperty(id)) {
        if (idSet && !idSet.has(id)) continue;
        var layers = this._animalLayers[id];
        var pts = layers.pts;
        pts.forEach(function(p) {
          allLatLngs.push([p.lat, p.lng]);
        });
      }
    }
    // Add venue
    allLatLngs.push([this._venue.lat, this._venue.lng]);

    if (allLatLngs.length > 0) {
      var bounds = L.latLngBounds(allLatLngs);
      this._map.fitBounds(bounds, { padding: [50, 50] });
    }
  };

  TMMap.prototype.onSelect = function(cb) {
    this._selectCb = cb;
  };

  return TMMap;
})();
