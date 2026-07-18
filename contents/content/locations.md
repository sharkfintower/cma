---
title: Mountains
description: Climbs and hikes ordered by location
---
<script src="/assets/js/leaflet.js" type="text/javascript"></script>
<script src="/assets/js/leaflet.markercluster.js" type="text/javascript"></script>
<link rel="stylesheet" href="/assets/css/leaflet.css" media="screen" type="text/css"/>
<link rel="stylesheet" href="/assets/css/MarkerCluster.css" media="screen" type="text/css"/>
<link rel="stylesheet" href="/assets/css/MarkerCluster.Default.css" media="screen" type="text/css"/>
<link rel="stylesheet" href="/assets/css/Control.FullScreen.css"/>
<script src="/assets/js/Control.FullScreen.js"></script>

<div id="map" class="map leaflet-container" style="height: 500px; position:relative;"></div>

<script type="text/javascript">
  {{ locations_code }}

  // create the map object and set the cooridnates of the initial view:
  let map = L.map('map', {
      fullscreenControl: true,
      fullscreenControlOptions: {
        position: 'topleft'
      }
    }).setView([46.800604, 11.174361], 6);
  let tileserver = "https://c.tile.thunderforest.com/outdoors/{z}/{x}/{y}.png?apikey=f13bfa644ac14730b74927c01e626a71";

  // create the tile layer with correct attribution:
  L.tileLayer(tileserver, {
      attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
      maxZoom: 18
      }).addTo(map);

  let markers = new L.MarkerClusterGroup();

  function formatDate(d) {
    let d2 = new Date(d);
    const monthNames = ["January", "February", "March", "April",
      "May", "June", "July", "August", "September", "October",
      "November", "December"];
    return monthNames[d2.getMonth()] + ' ' + d2.getFullYear();
  }

  let nameToMarker = {};

  function addMarker(location) {
    const m = new L.marker(location.location);
    let triplist = "";
    location.trips.forEach((trip) => {
      const sdate = formatDate(trip.date);
      triplist += `<li><a href='${trip.url}'>${trip.title}</a> ${sdate}</li>\n`;
    });
    triplist = `<ul>${triplist}</ul>\n`;
    const popupstr = `<h3>${location.name}</h3>\n${triplist}`;
    m.bindPopup(popupstr);
    markers.addLayer(m);
    nameToMarker[location.name] = m;
  }

  mapdata.forEach((md) => {
    addMarker(md);
  });

  markers.addTo(map);

  // Let's deal with an argument.
  const params = new URL(location.href).searchParams;
  const place = params.get('place');
  if (place) {
    const marker = nameToMarker[place];
    if (marker) {
      console.log(`Moving map to ${place}.`);
      const latLngs = [ marker.getLatLng() ];
      const markerBounds = L.latLngBounds(latLngs);
      map.fitBounds(markerBounds);
    }
  }
</script>

# Mountains by location

{{ locations_formatted }}
