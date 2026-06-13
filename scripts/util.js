window.TM = {
  STATUS: {
    "Transmitting": "live",
    "Track complete": "done",
    "Signal lost": "lost"
  },

  parseT: function(t) {
    return Date.parse(t);
  },

  el: function(tag, props, children) {
    var el = document.createElement(tag);
    if (props) {
      if (props.class) el.className = props.class;
      if (props.dataset) {
        for (var key in props.dataset) {
          el.dataset[key] = props.dataset[key];
        }
      }
      if (props.onclick) el.onclick = props.onclick;
      if (props.html) el.innerHTML = props.html;
      if (props.text) el.textContent = props.text;
      if (props.style) el.style.cssText = props.style;
    }
    if (children) {
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (typeof child === 'string') {
          el.appendChild(document.createTextNode(child));
        } else {
          el.appendChild(child);
        }
      }
    }
    return el;
  },

  fmtDate: function(ms) {
    var d = new Date(ms);
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
  },

  fmtDateTime: function(ms) {
    var d = new Date(ms);
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var h = d.getHours();
    var m = d.getMinutes();
    return months[d.getMonth()] + ' ' + d.getDate() + ', ' +
      (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m;
  },

  timeAgo: function(ms) {
    var diff = Date.now() - ms;
    if (diff < 0) return 'just now';
    var mins = Math.floor(diff / 60000);
    if (mins < 60) return mins + 'm ago';
    var hours = Math.floor(mins / 60);
    if (hours < 24) return hours + 'h ago';
    var days = Math.floor(hours / 24);
    return days + 'd ago';
  },

  fmtInt: function(n) {
    return n.toLocaleString('en-US');
  },

  metrics: function(pings) {
    var M2FT = 3.28084;
    var M2MI = 1 / 1609.34;
    var SPEED_CAP_MPH = 45;
    var MOVING_MIN_MPH = 0.3;

    if (!pings || pings.length < 2) {
      return {
        feet: 0,
        miles: 0,
        km: 0,
        avgMph: 0,
        topMph: 0,
        lastDistFeet: 0,
        currentSpeedMph: 0,
        days: 0,
        fixes: pings ? pings.length : 0
      };
    }

    var totalMeters = 0;
    var segmentMph = [];
    var lastT = TM.parseT(pings[pings.length - 1].t);
    var firstT = TM.parseT(pings[0].t);
    var last14hThreshold = lastT - 14 * 3600000;
    var lastDistMeters = 0;
    var finalSegmentMph = 0;

    for (var i = 0; i < pings.length - 1; i++) {
      var a = pings[i];
      var b = pings[i + 1];
      var d_m = haversine_m(a, b);
      totalMeters += d_m;

      var dt_h = (TM.parseT(b.t) - TM.parseT(a.t)) / 3600000;
      if (dt_h > 0) {
        var mph = (d_m * M2MI) / dt_h;
        if (mph < SPEED_CAP_MPH) {
          segmentMph.push(mph);
          if (i === pings.length - 2) {
            finalSegmentMph = mph;
          }
        }
        if (TM.parseT(b.t) >= last14hThreshold && TM.parseT(a.t) >= last14hThreshold) {
          lastDistMeters += d_m;
        }
      }
    }

    var movingMph = [];
    for (var j = 0; j < segmentMph.length; j++) {
      if (segmentMph[j] >= MOVING_MIN_MPH) {
        movingMph.push(segmentMph[j]);
      }
    }

    var avgMph = 0;
    if (movingMph.length > 0) {
      var sum = 0;
      for (var k = 0; k < movingMph.length; k++) {
        sum += movingMph[k];
      }
      avgMph = sum / movingMph.length;
    }

    var topMph = 0;
    if (segmentMph.length > 0) {
      topMph = segmentMph[0];
      for (var l = 1; l < segmentMph.length; l++) {
        if (segmentMph[l] > topMph) topMph = segmentMph[l];
      }
    }

    var lastGapH = (lastT - TM.parseT(pings[pings.length - 2].t)) / 3600000;
    var currentSpeedMph = (lastGapH > 6) ? 0 : finalSegmentMph;

    return {
      feet: Math.round(totalMeters * M2FT),
      miles: totalMeters * M2MI,
      km: totalMeters / 1000,
      avgMph: avgMph,
      topMph: topMph,
      lastDistFeet: Math.round(lastDistMeters * M2FT),
      currentSpeedMph: currentSpeedMph,
      days: (lastT - firstT) / 86400000,
      fixes: pings.length
    };

    function haversine_m(a, b) {
      var R = 6371000;
      var dLat = (b.lat - a.lat) * Math.PI / 180;
      var dLng = (b.lng - a.lng) * Math.PI / 180;
      var lat1 = a.lat * Math.PI / 180;
      var lat2 = b.lat * Math.PI / 180;
      var sinDLat = Math.sin(dLat / 2);
      var sinDLng = Math.sin(dLng / 2);
      var h = sinDLat * sinDLat + Math.cos(lat1) * Math.cos(lat2) * sinDLng * sinDLng;
      return 2 * R * Math.asin(Math.sqrt(h));
    }
  }
};
