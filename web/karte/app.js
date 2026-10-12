'use strict';
// Feldkarte – alle Flächen im Gebiet; ein Klick zeigt den ganzen Betrieb (Hof, Flächen, Kulturen).
// Daten: betriebe.json (öffentlich), flaechen-<Kennung>.pmtiles + grob-<Kennung>.pmtiles (Vektorkacheln),
// intern.bin (verschlüsselt).
(async function () {
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const zahl = (x, d = 1) => Number(x).toLocaleString('de-CH', { minimumFractionDigits: d, maximumFractionDigits: d });
  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const SCHMAL = () => matchMedia('(max-width: 760px)').matches;
  const SEL_FARBE = '#2563EB';
  const NEUTRAL = '#8DB255';
  const ADR_FARBEN = ['#D62828', '#1D4ED8', '#7C3AED', '#0F766E', '#B45309', '#BE185D', '#4D7C0F', '#0369A1', '#A16207'];
  const adrAn = () => !!(document.getElementById('adr') && document.getElementById('adr').checked);
  const toast = (t, ms = 3500) => { const e = $('#toast'); e.textContent = t; e.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => e.classList.remove('on'), ms); };
  const merke = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* privat */ } };
  const lies = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  // Version (aus 16_karte.py): Daten, Kacheln und Programm immer aus demselben Bau laden
  const V = ($('meta[name="fk-version"]') || {}).content || '';
  const mitV = u => new URL(V ? `${u}?v=${V}` : u, location.href).href;
  // Kacheln: Dateiname mit Kennung des Inhalts; nach einem Update findet eine alte Seite sie nicht mehr (→ Neu laden)
  const K = ($('meta[name="fk-kacheln"]') || {}).content || '';
  const kacheln = n => new URL(/^[0-9a-f]+$/.test(K) ? `${n}-${K}.pmtiles` : `${n}.pmtiles`, location.href).href;
  function neuLaden(text) {
    if ($('.ladefehler')) return;
    const d = document.createElement('div');
    d.className = 'ladefehler';
    d.innerHTML = esc(text) + ' <button class="knopf">Neu laden</button>';
    d.querySelector('button').onclick = () => location.reload();
    document.body.appendChild(d);
  }

  // ---------- Daten
  let D;
  try { D = await (await fetch(mitV('betriebe.json'))).json(); }
  catch (e) { document.body.innerHTML = '<p style="padding:20px">Daten konnten nicht geladen werden. Die Website über einen Webserver öffnen (lokal: <code>python3 scripts/server.py</code>).</p>'; return; }
  const META = D.meta, FELDER = META.felder;
  if (K && META.kacheln && META.kacheln !== K) neuLaden('Die Karte wurde inzwischen aktualisiert.');
  const B = D.b.map((a, i) => { const o = { i }; FELDER.forEach((k, j) => { o[k] = a[j]; }); return o; });
  const GR = META.gruppen;                       // [[Name, Farbe], …]
  const FAV = Object.fromEntries(META.favoriten.map(f => [f.key, f]));
  const FAV_IDX = META.favoriten.flatMap(f => f.i);
  let internDa = null;                            // intern.bin: null = unbekannt, false = keine Datei, true = vorhanden
  let INTERN = null;                              // {namen:{i:[[art,name,person,detail,quelle,url,sicherheit,abstand]]}, adr:{…}}
  const nrKurz = nr => nr.replace(/\s+/g, '');

  function anzeigeName(b) {
    if (b.favorit) return FAV[b.favorit].name;
    const n = INTERN && INTERN.namen[b.i];
    if (!n) return '';
    const gut = n.find(x => ['firma', 'hof', 'recherche', 'hofladen'].includes(x[0]) && x[6] !== 'unsicher')
      || n.find(x => x[0] === 'bezeichnung') || n.find(x => x[0] === 'hofname' && x[6] !== 'unsicher');
    return gut ? gut[1] : '';
  }
  const titel = b => anzeigeName(b) || b.adresse || ('Betrieb ' + b.nr);

  // Suchtext je Betrieb (öffentlich; Namen kommen nach dem Entsperren dazu)
  function suchtexte() {
    for (const b of B) {
      const teile = [b.nr, nrKurz(b.nr), b.adresse, b.gemeinde, b.gemeinden, b.kt];
      if (b.favorit) { const f = FAV[b.favorit]; teile.push(f.name, f.sub, ...f.teile.map(t => t.name + ' ' + t.kurz)); }
      const n = INTERN && INTERN.namen[b.i];
      if (n) n.forEach(x => teile.push(x[1], x[2]));
      b.such = norm(teile.join(' | '));
    }
  }
  suchtexte();

  // ---------- Karte
  const protokoll = new pmtiles.Protocol();
  maplibregl.addProtocol('pmtiles', protokoll.tile);
  const zwei = id => [id, id + '-g'];          // je Ebene: Detail (ab Zoom 12) und Übersicht (Zoom 10–11)
  const wmts = l => [`https://wmts.geo.admin.ch/1.0.0/${l}/default/current/3857/{z}/{x}/{y}.jpeg`];
  const kultFarbe = ['match', ['get', 'g'], ...GR.flatMap((g, j) => [j, g[1]]), '#999999'];
  const favFarbe = ['match', ['get', 'i'], ...META.favoriten.flatMap(f => f.i.flatMap(i => [i, f.color])), '#000000'];
  const favFilter = ['in', ['get', 'i'], ['literal', FAV_IDX]];
  const leer = ['in', ['get', 'i'], ['literal', []]];
  const keineFlaeche = ['==', ['get', 'p'], -1];
  const quelle = `Flächen: Kantone (geodienste.ch), Bezugsjahr ${META.jahr}`;
  const beide = (id, typ, opt) => [
    { id, type: typ, source: 'f', 'source-layer': 'f', minzoom: 12, ...opt },
    { id: id + '-g', type: typ, source: 'g', 'source-layer': 'f', maxzoom: 12, ...opt },
  ];
  const style = {
    version: 8,
    sources: {
      grau: { type: 'raster', tiles: wmts('ch.swisstopo.pixelkarte-grau'), tileSize: 256, maxzoom: 19, attribution: '© swisstopo' },
      farbe: { type: 'raster', tiles: wmts('ch.swisstopo.pixelkarte-farbe'), tileSize: 256, maxzoom: 19, attribution: '© swisstopo' },
      luft: { type: 'raster', tiles: wmts('ch.swisstopo.swissimage'), tileSize: 256, maxzoom: 20, attribution: '© swisstopo' },
      parz: { type: 'raster', tileSize: 256, minzoom: 17, attribution: 'Parzellen © Kanton Zürich',
        tiles: ['https://wms.zh.ch/avwms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=Liegenschaften,OSNR_liegenschaften&STYLES=&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}'] },
      f: { type: 'vector', url: 'pmtiles://' + kacheln('flaechen'), attribution: quelle },
      g: { type: 'vector', url: 'pmtiles://' + kacheln('grob'), attribution: quelle },
    },
    layers: [
      { id: 'bg-grau', type: 'raster', source: 'grau' },
      { id: 'bg-farbe', type: 'raster', source: 'farbe', layout: { visibility: 'none' } },
      { id: 'bg-luft', type: 'raster', source: 'luft', layout: { visibility: 'none' } },
      ...beide('f-fill', 'fill', { paint: { 'fill-color': NEUTRAL, 'fill-opacity': 0.4 } }),
      { id: 'f-line', type: 'line', source: 'f', 'source-layer': 'f', minzoom: 12.5,
        paint: { 'line-color': '#34472C', 'line-width': ['interpolate', ['linear'], ['zoom'], 13, 0.4, 17, 1.2], 'line-opacity': 0.6 } },
      ...beide('fav-fill', 'fill', { filter: favFilter, layout: { visibility: 'none' }, paint: { 'fill-color': favFarbe, 'fill-opacity': 0.55 } }),
      ...beide('fav-line', 'line', { filter: favFilter, layout: { visibility: 'none' }, paint: { 'line-color': favFarbe, 'line-width': 2.5 } }),
      { id: 'parz', type: 'raster', source: 'parz', layout: { visibility: 'none' } },
      ...beide('sel-fill', 'fill', { filter: leer, paint: { 'fill-color': SEL_FARBE, 'fill-opacity': 0.62 } }),
      ...beide('sel-line', 'line', { filter: leer, paint: { 'line-color': SEL_FARBE, 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.2, 16, 2.5] } }),
      // angeklickte Fläche: über ihre Kennung p, damit der Umriss über Kachelgrenzen und Zoomstufen ganz bleibt
      ...beide('klick-line', 'line', { filter: keineFlaeche, paint: { 'line-color': '#FFFFFF', 'line-width': 3.5 } }),
      ...beide('klick-strich', 'line', { filter: keineFlaeche, paint: { 'line-color': '#111111', 'line-width': 1.5, 'line-dasharray': [2, 1.5] } }),
    ],
  };
  const g = META.gebiet;
  const map = new maplibregl.Map({
    container: 'map', style, bounds: [[g[0], g[1]], [g[2], g[3]]], fitBoundsOptions: { padding: 20 },
    minZoom: 10, maxZoom: 20, dragRotate: false, pitchWithRotate: false, touchPitch: false, attributionControl: { compact: true },
  });
  const stilBereit = new Promise(r => map.once('style.load', r));
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }), 'top-right');
  map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
  map.on('error', e => {
    const text = String(e.error && e.error.message || '');
    if (!(e.sourceId === 'f' || e.sourceId === 'g' || /pmtiles|byte serving|content-length|range/i.test(text))) return;
    neuLaden('Flächen konnten nicht geladen werden (Verbindung, Karte inzwischen aktualisiert oder Webserver ohne Range-Anfragen).');
  });

  // Panel-Höhe je Zustand (Handy): daraus das Polster – nicht aus der laufenden Animation
  const HOEHE = { peek: () => 112, half: () => innerHeight * 0.52, full: () => innerHeight - 56 };
  const zustand = () => $('#side').dataset.state;
  function polster(st) {
    if (!SCHMAL()) return { top: 40, bottom: 40, left: 40, right: 40 };
    return { top: 50, bottom: Math.min(HOEHE[st || zustand()](), innerHeight * 0.6) + 20, left: 24, right: 24 };
  }
  function sichtbarMachen(px, st) {   // angetippten Punkt über die künftige Panelkante schieben
    if (!SCHMAL()) return;
    const oben = innerHeight - HOEHE[st]();
    if (px.y > oben - 30) map.panBy([0, px.y - oben / 2], { duration: 400 });
  }

  // ---------- Darstellung: Hintergrund, Farbe, Favoriten, Parzellen
  let modus = lies('fk-modus') || 'neutral';
  function grundOpazitaet() {
    const [a, b] = SEL ? (modus === 'kultur' ? [0.22, 0.3] : [0.12, 0.18]) : (modus === 'kultur' ? [0.6, 0.72] : [0.28, 0.4]);
    return ['interpolate', ['linear'], ['zoom'], 10, a, 14, b];
  }
  function favSetzen() {
    const an = $('#favon').checked;
    // nach Kultur: Favoriten nur als kräftiger Rand, sonst mischen sich Favoriten- und Kulturfarben
    for (const id of zwei('fav-fill')) map.setLayoutProperty(id, 'visibility', an && modus !== 'kultur' ? 'visible' : 'none');
    for (const id of zwei('fav-line')) map.setLayoutProperty(id, 'visibility', an ? 'visible' : 'none');
  }
  function farbeSetzen() {
    for (const id of zwei('f-fill')) { map.setPaintProperty(id, 'fill-color', modus === 'kultur' ? kultFarbe : NEUTRAL); map.setPaintProperty(id, 'fill-opacity', grundOpazitaet()); }
    $$('#farbe button').forEach(b => b.classList.toggle('on', b.dataset.m === modus));
    favSetzen(); legende();
  }

  function legende() {
    const L = $('#legende');
    const zeile = (farbe, text) => `<div class="row" style="cursor:default;padding:3px 0"><span class="farbe" style="background:${farbe};width:14px;border-radius:3px"></span><span class="txt">${esc(text)}</span></div>`;
    let h = '';
    if (modus === 'kultur') h += '<h3>Kulturen</h3>' + GR.map(x => zeile(x[1], x[0])).join('');
    h += '<h3>Favoriten</h3>' + META.favoriten.map(f => zeile(f.color, f.name)).join('');
    if (INTERN && INTERN.adr && adrAn()) h += '<h3>Regionen (intern)</h3>' + INTERN.adr.regionen.map((r, j) => zeile(ADR_FARBEN[j % ADR_FARBEN.length], r)).join('');
    L.innerHTML = h;
  }

  // ---------- Auswahl
  let SEL = null;                      // {is:[…], fav: Favorit als Ganzes gewählt, favKey: Favorit der Auswahl, parzelle}
  let hofMarker = [];
  const farbeVon = s => s && s.favKey ? FAV[s.favKey].color : SEL_FARBE;

  function auswahlZeichnen() {
    const is = SEL ? SEL.is : [];
    const f = ['in', ['get', 'i'], ['literal', is]];
    for (const id of [...zwei('sel-fill'), ...zwei('sel-line')]) map.setFilter(id, f);
    for (const id of zwei('sel-fill')) map.setPaintProperty(id, 'fill-color', farbeVon(SEL));
    for (const id of zwei('sel-line')) map.setPaintProperty(id, 'line-color', farbeVon(SEL));
    for (const id of zwei('f-fill')) map.setPaintProperty(id, 'fill-opacity', grundOpazitaet());
    const p = SEL && SEL.parzelle ? SEL.parzelle.p : -1;
    for (const id of [...zwei('klick-line'), ...zwei('klick-strich')]) map.setFilter(id, ['==', ['get', 'p'], p ?? -1]);
    hofMarker.forEach(m => m.remove()); hofMarker = [];
    for (const i of is) {
      const b = B[i], el = document.createElement('div');
      el.className = 'hof' + (b.sq >= 2 ? ' geschaetzt' : '');
      el.innerHTML = '<div class="pin"></div>';
      el.firstChild.style.background = farbeVon(SEL);
      el.title = (b.sq === 3 ? 'Lage geschätzt (Standort fehlt in den Kantonsdaten)' : 'Hof') + (b.adresse ? ': ' + b.adresse : '');
      el.addEventListener('click', ev => { ev.stopPropagation(); toast(el.title, 4000); });
      hofMarker.push(new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat([b.lon, b.lat]).addTo(map));
    }
  }

  function bboxVon(is) {
    let w = 180, s = 90, e = -180, n = -90;
    for (const i of is) { const b = B[i].bbox; w = Math.min(w, b[0], B[i].lon); s = Math.min(s, b[1], B[i].lat); e = Math.max(e, b[2], B[i].lon); n = Math.max(n, b[3], B[i].lat); }
    return [[w, s], [e, n]];
  }
  function zeigeAlle(st) {
    if (!SEL) return;
    const bb = bboxVon(SEL.is), pad = polster(st);
    const cam = map.cameraForBounds(bb, { padding: pad, maxZoom: 16 });
    if (cam && cam.zoom >= map.getMinZoom()) { map.fitBounds(bb, { padding: pad, maxZoom: 16, duration: 700 }); return; }
    // grösser als die Karte bei minZoom: Mitte selbst setzen (fitBounds rechnet das Polster für den ungeklemmten Zoom
    // und schiebt die Auswahl sonst über den Bildrand)
    const z = map.getMinZoom(), welt = 512 * Math.pow(2, z), c = map.getContainer();
    const mitte = maplibregl.MercatorCoordinate.fromLngLat([(bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2]);
    const dx = (c.clientWidth / 2 - (pad.left + c.clientWidth - pad.right) / 2) / welt;
    const dy = (c.clientHeight / 2 - (pad.top + c.clientHeight - pad.bottom) / 2) / welt;
    map.easeTo({ center: new maplibregl.MercatorCoordinate(mitte.x + dx, mitte.y + dy).toLngLat(), zoom: z, duration: 700 });
  }

  function waehle(is, opt = {}) {
    const offen = !!SEL;
    const k0 = B[is[0]].favorit;
    const favKey = k0 && is.every(i => B[i].favorit === k0) ? k0 : null;
    SEL = { is, fav: opt.fav || (favKey && FAV[favKey].i.length === is.length ? favKey : null), favKey, parzelle: opt.parzelle || null };
    auswahlZeichnen();
    detail();
    $('#side').classList.add('detail');
    zeigePanel('detail');
    const ziel = SCHMAL() && zustand() === 'peek' ? 'half' : zustand();
    if (SCHMAL()) blatt(ziel);
    if (opt.zoom) zeigeAlle(ziel);
    else if (opt.px) sichtbarMachen(opt.px, ziel);
    const h = '#b=' + encodeURIComponent(SEL.fav ? SEL.fav : B[is[0]].nr);
    if (location.hash !== h) {
      if (opt.ersetzen || offen) history.replaceState(history.state, '', h); else history.pushState({ fk: 1 }, '', h);
    }
  }
  function schliessen(ausVerlauf) {
    SEL = null; auswahlZeichnen();
    $('#side').classList.remove('detail'); zeigePanel(aktiverTab);
    if (ausVerlauf || !location.hash) return;
    if (history.state && history.state.fk) history.back(); else history.replaceState(null, '', location.pathname + location.search);
  }

  // ---------- Detail
  function kulturBlock(ha) {
    const tot = ha.reduce((a, b) => a + b, 0) || 1;
    const bar = ha.map((v, j) => v > 0 ? `<i style="width:${(100 * v / tot).toFixed(2)}%;background:${GR[j][1]}" title="${esc(GR[j][0])}"></i>` : '').join('');
    const zeilen = ha.map((v, j) => [v, j]).filter(x => x[0] > 0.004).sort((a, b) => b[0] - a[0])
      .map(([v, j]) => `<tr><td><span class="q" style="background:${GR[j][1]}"></span>${esc(GR[j][0])}</td><td class="z">${zahl(v, 2)} ha</td><td class="z">${Math.round(100 * v / tot)} %</td></tr>`).join('');
    return `<div class="balken">${bar}</div><table class="t">${zeilen}</table>`;
  }
  const SICHER = { 'geprüft': 'gut', 'amtlich': 'gut', 'sicher': 'gut', 'wahrscheinlich': '', 'unsicher': 'warn', 'vermutet': 'warn' };
  const ART = { firma: 'Firma an der Hofadresse (Handelsregister)', hof: 'Hof (eigener Eintrag)', hofladen: 'Hofladen', hofname: 'Hofname',
    bezeichnung: 'Bezeichnung in den Kantonsdaten', recherche: 'Recherche' };
  function namenBlock(is) {
    if (is.some(i => B[i].favorit)) return '';
    if (!INTERN) {
      const hinweis = internDa === false ? 'Bewirtschafter nicht angegeben (die Kantonsdaten enthalten keine Namen).'
        : 'Namen sind geschützt – im Tab <a href="#" data-tab-link="info">Info</a> mit Passwort entsperren.';
      return `<h3>Bewirtschafter</h3><p class="unbekannt">${hinweis}</p>`;
    }
    let h = '<h3>Bewirtschafter</h3>';
    for (const i of is) {
      const n = INTERN.namen[i] || [];
      if (is.length > 1) h += `<div class="nr">${esc(B[i].nr)}</div>`;
      if (!n.length) { h += `<p class="unbekannt">Bewirtschafter unbekannt – keine öffentliche Quelle zugeordnet.${B[i].adresse ? ' Hof: ' + esc(B[i].adresse) : ''}</p>`; continue; }
      h += n.map(x => `<div class="name"><div class="nn">${esc(x[1])}${x[2] ? ' · ' + esc(x[2]) : ''}<span class="tag ${SICHER[x[6]] || ''}">${esc(x[6])}</span></div>
        <div class="nd">${esc(ART[x[0]] || x[0])}${x[7] > 0 ? ` · ${x[7]} m vom Betriebspunkt` : ''}</div>
        ${x[3] ? `<div class="nd">${esc(x[3])}</div>` : ''}
        <div class="nd">Quelle: ${/^https?:\/\//i.test(x[5]) ? `<a href="${esc(x[5])}" target="_blank" rel="noopener noreferrer">${esc(x[4])}</a>` : esc(x[4])}</div></div>`).join('');
    }
    return h;
  }
  function adrBlock(is) {
    if (!(INTERN && INTERN.adr && adrAn())) return '';
    const tot = is.reduce((a, i) => a + B[i].ha, 0);
    const summe = {};
    for (const i of is) for (const [r, ha] of (INTERN.adr.anteile[i] || [])) summe[r] = (summe[r] || 0) + ha;
    const zeilen = Object.entries(summe).map(([r, ha]) => [+r, ha]).sort((a, b) => (a[0] < 0) - (b[0] < 0) || b[1] - a[1])
      .map(([r, ha]) => r < 0
        ? `<tr><td class="unbekannt"><span class="q" style="background:var(--line)"></span>in keiner Region</td><td class="z">${zahl(ha, 1)} ha</td><td class="z">${Math.round(100 * ha / tot)} %</td></tr>`
        : `<tr><td><span class="q" style="background:${ADR_FARBEN[r % ADR_FARBEN.length]}"></span>${esc(INTERN.adr.regionen[r])}</td><td class="z">${zahl(ha, 1)} ha</td><td class="z"><b>${Math.round(100 * ha / tot)} %</b></td></tr>`).join('');
    return `<h3>Regionen (intern)</h3>${zeilen ? `<table class="t">${zeilen}</table>` : '<p class="unbekannt">Keine Angaben.</p>'}
      <p class="hint">Anteil an ${zahl(tot, 1)} ha. Regionen können sich überschneiden – dann liegt eine Fläche in mehreren und die Summe über 100 %.</p>`;
  }
  const STANDORT = { 2: 'Standort in den Kantonsdaten ungültig – Lage aus der Adresse', 3: 'Standort fehlt in den Kantonsdaten – Lage der grössten Fläche' };
  function detail() {
    const P = $('#p-detail');
    const is = SEL.is, f = SEL.favKey ? FAV[SEL.favKey] : null, b = B[is[0]];
    const farbe = farbeVon(SEL);
    const hell = ['#D8C21A', '#F2E27C', '#E68A00'].includes(farbe);
    const ha = is.reduce((a, i) => a + B[i].ha, 0), n = is.reduce((a, i) => a + B[i].n, 0);
    const haG = GR.map((_, j) => is.reduce((a, i) => a + B[i].gruppen_ha[j], 0));
    const bio = is.reduce((a, i) => a + B[i].ha_bio, 0);
    let h = `<div class="band${hell ? ' hell' : ''}" style="background:${farbe}">
      <div class="bn">${esc(f ? f.name : titel(b))}</div>
      <div class="bs">${esc(f ? f.sub : (anzeigeName(b) ? b.adresse : b.gemeinde))}</div>
      <div class="bnr">${is.map(i => esc(B[i].nr)).join('\n')}</div></div>
      <div class="knopfe"><button class="knopf" id="d-alle">Alle Flächen</button>
      ${b.sq === 3 ? '' : '<a class="knopf" id="d-route" target="_blank" rel="noopener">Route zum Hof</a>'}
      <button class="knopf" id="d-link">Link</button><button class="knopf" id="d-zu" aria-label="Schliessen">✕</button></div>
      ${f && is.length < f.i.length ? `<div class="knopfe"><button class="knopf" id="d-ganz">Ganzer Betrieb ${esc(f.name)} (${f.i.length} Betriebsnummern)</button></div>` : ''}`;
    if (SEL.parzelle && SEL.parzelle.grob) {
      h += `<div class="parzelle" style="border-color:${farbe}"><b>${esc(GR[SEL.parzelle.g] ? GR[SEL.parzelle.g][0] : '')}</b><br><span class="hint">Für Angaben zur Fläche näher heranzoomen.</span></div>`;
    } else if (SEL.parzelle) {
      const p = SEL.parzelle;
      h += `<div class="parzelle" style="border-color:${farbe}"><b>${esc(META.lnf[p.k] || ('Code ' + p.k))}</b><br>
        <span class="hint">${zahl(p.m / 10000, 2)} ha · ${esc(META.gemeinden[p.gm] || '')} · ${esc(GR[p.g] ? GR[p.g][0] : '')}${p.b ? ' · Bio' : ''}</span></div>`;
    }
    if (f) {
      if (f.note) h += `<p class="hint">${esc(f.note)}</p>`;
      h += '<h3>Firmen</h3>' + f.teile.map(t => `<div class="row" style="cursor:default"><span class="farbe" style="background:${t.color}"></span><span class="txt"><div class="n">${esc(t.name)}</div><div class="s">${esc(t.bio)}</div></span></div>`).join('');
    }
    h += namenBlock(is);
    h += '<h3>Hof (Betriebsstandort)</h3>' + is.map(i => {
      const x = B[i];
      const weit = x.dist_flaeche_m > 3000 ? `<br><span class="tag warn">Standort ${zahl(x.dist_flaeche_m / 1000, 1)} km von den eigenen Flächen entfernt</span>` : '';
      const quelle = x.aq === 1 ? `<br><span class="hint">nächste amtliche Gebäudeadresse, ${x.ad} m vom Standort</span>` : '';
      const lage = STANDORT[x.sq] ? `<br><span class="tag warn">${STANDORT[x.sq]}</span>` : '';
      return `<div style="margin:4px 0">${x.adresse ? esc(x.adresse) : `<span class="unbekannt">keine Adresse am Standort (Gemeinde ${esc(x.gemeinde)})</span>`}${is.length > 1 ? ` <span class="nr">${esc(x.nr)}</span>` : ''}${quelle}${lage}${weit}</div>`;
    }).join('');
    h += `<div class="zahlen"><div><b>${n}</b><span>Flächen</span></div><div><b>${zahl(ha, 1)}</b><span>ha total</span></div><div><b>${bio > 0.05 ? zahl(bio, 1) : '–'}</b><span>ha Bio gemeldet</span></div></div>`;
    h += '<h3>Kulturen</h3>' + kulturBlock(haG);
    h += adrBlock(is);
    h += '<h3>Gemeinden der Flächen</h3>' + is.map(i => `<p style="margin:2px 0">${esc(B[i].gemeinden)}</p>`).join('');
    const ps = is.map(i => B[i].produktionsstaetten).filter(Boolean);
    if (ps.length) h += '<h3>Produktionsstätten</h3><p style="margin:2px 0">' + ps.map(esc).join('<br>') + '</p>';
    h += `<p class="hint">Kantonsdaten ${esc([...new Set(is.map(i => B[i].kt))].join(', '))}, Bezugsjahr ${esc([...new Set(is.map(i => B[i].jahr))].join(', '))}. Flächen ohne überlagernde Elemente.</p>`;
    P.innerHTML = h;
    P.scrollTop = 0; $('#panels').scrollTop = 0;
    $('#d-alle').onclick = () => zeigeAlle();
    if ($('#d-ganz')) $('#d-ganz').onclick = () => waehle(f.i, { fav: f.key, zoom: true });
    $('#d-zu').onclick = () => schliessen();
    const apple = /iPhone|iPad|Macintosh/.test(navigator.userAgent);
    if ($('#d-route')) $('#d-route').href = apple ? `https://maps.apple.com/?daddr=${b.lat},${b.lon}` : `https://www.google.com/maps/dir/?api=1&destination=${b.lat},${b.lon}`;
    $('#d-link').onclick = async () => {
      const url = location.href;
      try { if (navigator.share && SCHMAL()) await navigator.share({ title: f ? f.name : titel(b), url }); else { await navigator.clipboard.writeText(url); toast('Link kopiert'); } }
      catch (e) { /* abgebrochen */ }
    };
    P.querySelectorAll('[data-tab-link]').forEach(a => a.onclick = ev => { ev.preventDefault(); schliessen(); tab(a.dataset.tabLink); });
  }

  // ---------- Listen
  let filter = '';
  const passt = b => !filter || (filter === 'gemuese' ? b.gruppen_ha[0] >= 0.5 : filter === 'geschuetzt' ? b.gruppen_ha[1] >= 0.05 : b.ha_bio > 0 && b.ha_bio >= 0.5 * b.ha);
  function zeile(b) {
    const f = b.favorit ? FAV[b.favorit] : null;
    const name = titel(b);
    const unter = [b.nr, name === b.adresse ? b.gemeinde : (b.adresse || b.gemeinde)].filter(Boolean).join(' · ');
    return `<div class="row" data-i="${b.i}"><span class="farbe" style="background:${f ? f.color : 'var(--line)'}"></span><span class="txt"><div class="n">${esc(name)}</div><div class="s">${esc(unter)}</div></span><span class="ha">${zahl(b.ha, 1)} ha</span></div>`;
  }
  function favListe() {
    $('#favs').innerHTML = META.favoriten.map(f => {
      const ha = f.i.reduce((a, i) => a + B[i].ha, 0);
      return `<div class="row fav" data-fav="${f.key}"><span class="farbe" style="background:${f.color}"></span><span class="txt"><div class="n">${esc(f.name)}</div><div class="s">${esc(f.sub)}</div></span><span class="ha">${zahl(ha, 1)} ha</span></div>`;
    }).join('');
    $$('#favs .row').forEach(r => r.onclick = () => waehle(FAV[r.dataset.fav].i, { fav: r.dataset.fav, zoom: true }));
  }
  function liste() {
    const q = norm($('#q').value.trim());
    let treffer, titelText, mehr = '';
    if (q) {
      const woerter = q.split(/\s+/);
      const qk = q.replace(/\s+/g, '');
      treffer = B.filter(b => passt(b) && (woerter.every(w => b.such.includes(w)) || b.such.includes(qk)));
      treffer.sort((a, b) => (b.favorit ? 1 : 0) - (a.favorit ? 1 : 0) || b.ha - a.ha);
      titelText = `Suchergebnisse (${treffer.length})`;
    } else {
      const bb = map.getBounds();
      treffer = B.filter(b => passt(b) && bb.contains([b.lon, b.lat])).sort((a, b) => b.ha_gebiet - a.ha_gebiet);
      titelText = `Höfe im Kartenausschnitt (${treffer.length})`;
    }
    if (treffer.length > 80) { mehr = `${treffer.length - 80} weitere – näher zoomen oder suchen.`; treffer = treffer.slice(0, 80); }
    $('#liste-titel').textContent = titelText;
    $('#liste').innerHTML = treffer.length ? treffer.map(zeile).join('') : '<p class="hint">Keine Betriebe.</p>';
    $('#liste-mehr').textContent = mehr;
    $$('#liste .row').forEach(r => r.onclick = () => waehle([+r.dataset.i], { zoom: true }));
  }
  let lt; const listeSpaeter = () => { clearTimeout(lt); lt = setTimeout(liste, 150); };
  const sucheGross = () => { if (SCHMAL() && zustand() === 'peek') blatt('full'); };
  $('#q').addEventListener('focus', sucheGross);
  $('#q').addEventListener('input', () => { if ($('#side').classList.contains('detail')) schliessen(); tab('liste'); sucheGross(); listeSpaeter(); });
  $$('#filter button').forEach(b => b.onclick = () => { filter = b.dataset.f; $$('#filter button').forEach(x => x.classList.toggle('on', x === b)); liste(); });

  // ---------- Tabs, Panel (Handy)
  let aktiverTab = 'liste';
  function zeigePanel(name) { $$('.panel').forEach(p => p.classList.toggle('on', p.id === 'p-' + name)); }
  function tab(name) { aktiverTab = name; $$('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === name)); if (!SEL) zeigePanel(name); }
  $$('.tabs button').forEach(b => b.onclick = () => { tab(b.dataset.tab); if (SCHMAL() && zustand() === 'peek') blatt('half'); });
  function blatt(st) { $('#side').dataset.state = st; }
  (function ziehen() {
    const side = $('#side');
    let y0 = null, h0 = 0, bewegt = false;
    const start = e => { if (!SCHMAL() || (e.target.closest('input,button,a') && e.currentTarget.id !== 'grip')) return; y0 = e.clientY; h0 = side.getBoundingClientRect().height; bewegt = false; side.classList.add('ziehen'); };
    const zug = e => { if (y0 === null) return; const dy = y0 - e.clientY; if (Math.abs(dy) > 4) bewegt = true; side.style.height = Math.max(90, Math.min(innerHeight - 40, h0 + dy)) + 'px'; };
    const ende = () => {
      if (y0 === null) return; y0 = null; side.classList.remove('ziehen');
      const h = side.getBoundingClientRect().height; side.style.height = '';
      if (!bewegt) { blatt(zustand() === 'full' ? 'half' : zustand() === 'half' ? 'full' : 'half'); return; }
      blatt(Object.keys(HOEHE).sort((a, b) => Math.abs(HOEHE[a]() - h) - Math.abs(HOEHE[b]() - h))[0]);
    };
    for (const el of [$('#grip'), $('header.top')]) el.addEventListener('pointerdown', start);
    addEventListener('pointermove', zug); addEventListener('pointerup', ende); addEventListener('pointercancel', ende);
  })();
  if (SCHMAL()) blatt('peek');
  favListe();

  // ---------- Karte: Bedienung (wartet nur auf den Stil, nicht auf die Kacheln)
  await stilBereit;
  $$('#bg button').forEach(b => b.onclick = () => {
    for (const k of ['grau', 'farbe', 'luft']) map.setLayoutProperty('bg-' + k, 'visibility', k === b.dataset.bg ? 'visible' : 'none');
    $$('#bg button').forEach(x => x.classList.toggle('on', x === b)); merke('fk-bg', b.dataset.bg);
  });
  $$('#farbe button').forEach(b => b.onclick = () => { modus = b.dataset.m; merke('fk-modus', modus); farbeSetzen(); });
  $('#favon').onchange = e => { favSetzen(); merke('fk-fav', e.target.checked ? '1' : null); };
  $('#parz').onchange = e => { map.setLayoutProperty('parz', 'visibility', e.target.checked ? 'visible' : 'none'); if (e.target.checked && map.getZoom() < 17) toast('Parzellen erscheinen ab Zoom 17 (nur Kanton Zürich).'); };
  const tip = document.createElement('div');
  tip.style.cssText = 'position:fixed;z-index:20;pointer-events:none;background:rgba(20,28,24,.9);color:#fff;padding:4px 8px;border-radius:6px;font-size:13px;display:none';
  document.body.appendChild(tip);
  map.on('click', e => {
    if (e.originalEvent && e.originalEvent.target.closest && e.originalEvent.target.closest('.maplibregl-marker')) return;
    const fs = map.queryRenderedFeatures(e.point, { layers: zwei('f-fill') });
    if (!fs.length) { if (SEL) schliessen(); return; }
    const p = fs[0].properties;
    waehle([p.i], { px: e.point, parzelle: { p: p.p, k: p.k, m: p.m, gm: p.gm, g: p.g, b: p.b, grob: p.k === undefined } });
  });
  const MAUS = matchMedia('(hover: hover) and (pointer: fine)').matches;
  map.on('mousemove', zwei('f-fill'), e => {
    map.getCanvas().style.cursor = 'pointer';
    if (!MAUS) return;
    const b = B[e.features[0].properties.i];
    tip.textContent = titel(b) + ' · ' + zahl(b.ha, 1) + ' ha';
    tip.style.left = (e.originalEvent.clientX + 14) + 'px'; tip.style.top = (e.originalEvent.clientY + 12) + 'px'; tip.style.display = 'block';
  });
  map.on('mouseleave', zwei('f-fill'), () => { map.getCanvas().style.cursor = ''; tip.style.display = 'none'; });
  map.on('moveend', () => { if (!$('#q').value.trim()) listeSpaeter(); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && SEL) schliessen(); });

  // gespeicherte Einstellungen
  const bg = lies('fk-bg'); if (bg) { const b = $(`#bg button[data-bg="${bg}"]`); if (b) b.click(); }
  if (lies('fk-fav')) $('#favon').checked = true;
  farbeSetzen(); liste();

  // ---------- Link #b=… (vor dem internen Teil, damit geteilte Links sofort öffnen)
  function ausHash(ersetzen) {
    const m = location.hash.match(/^#b=(.+)$/);
    if (!m) { if (SEL) schliessen(true); return; }
    const k = decodeURIComponent(m[1]);
    if (FAV[k]) { waehle(FAV[k].i, { fav: k, zoom: true, ersetzen }); return; }
    const b = B.find(x => x.nr === k || nrKurz(x.nr) === nrKurz(k));
    if (b) waehle([b.i], { zoom: true, ersetzen }); else toast('Betrieb nicht gefunden: ' + k);
  }
  addEventListener('popstate', () => ausHash(true));
  ausHash(true);
  window.feldkarte = { map, waehle, B };   // für Tests und die Konsole

  // ---------- Info
  const nFl = B.reduce((a, b) => a + b.n, 0), haG = B.reduce((a, b) => a + b.ha_gebiet, 0);
  $('#info-text').innerHTML = `<h3>Was die Karte zeigt</h3>
    <p>Alle landwirtschaftlichen Nutzungsflächen der ${B.length.toLocaleString('de-CH')} Betriebe, die im Gebiet Flächen bewirtschaften (${nFl.toLocaleString('de-CH')} Flächen, davon ${zahl(haG, 0)} ha im Gebiet). Eine Fläche antippen: Alle Flächen desselben Betriebs leuchten auf, auch ausserhalb des Gebiets und in anderen Kantonen.</p>
    <p><b>Gebiet:</b> konvexe Hülle aller Flächen der Favoriten plus ${META.puffer_km} km, nur Schweiz. Betriebe aus ${META.kantone.length} Kantonen (${esc(META.kantone.join(', '))}).</p>
    <h3>Daten</h3>
    <p>Landwirtschaftliche Kulturflächen der Kantone (geodienste.ch), Bezugsjahr ${META.jahr} (GL, GR: 2026). Ohne überlagernde Elemente. Nicht frei erhältlich und deshalb nicht enthalten: Flächen von Betrieben aus NE, TI, NW, OW, VD.</p>
    <p><b>Hof:</b> Betriebsstandort der Kantonsdaten (fehlt er oder liegt er ausserhalb der Schweiz: Lage aus der Adresse bzw. der grössten Fläche). Adresse aus den Kantonsdaten (ohne Personenangaben), sonst die nächste amtliche Gebäudeadresse höchstens 60 m vom Standort (swisstopo). Ohne Passwort zeigt die Karte keine Namen. Die Adresse ist die des Betriebsstandorts und kann auch eine Wohnadresse sein. Wem eine Fläche gehört, zeigt nur die Eigentumsauskunft des Kantons.</p>
    <p><b>Bewirtschafter:</b> Namen (nur mit Passwort) sind abgeleitet (Handelsregister, Hofnamen, Bezeichnungen der Kantonsdaten) und je mit Quelle und Sicherheit angegeben.</p>
    <p>Karten © swisstopo · Parzellen © Kanton Zürich · Kartenbibliothek MapLibre, PMTiles · ${esc(META.stand)}</p>
    <p><a href="betriebe.html">Detailansicht der Favoriten</a> (Teilbetriebe, Bio, Kulturen)</p>`;

  // ---------- Interner Teil (verschlüsselt). Beim Start nur den Kopf der Datei lesen.
  const MERKEN_TAGE = 30;
  let blobVoll = null;
  async function internKopf() {
    try {
      const r = await fetch(mitV('intern.bin'), { headers: { Range: 'bytes=0-35' } });
      if (!r.ok) return false;
      const u = new Uint8Array(await r.arrayBuffer());
      if (r.status === 200) blobVoll = u;          // Server ohne Range: ganze Datei erhalten
      return u.length >= 36 && String.fromCharCode(...u.slice(0, 4)) === 'FKv2';
    } catch (e) { return false; }
  }
  async function internGanz() {
    if (!blobVoll) { const r = await fetch(mitV('intern.bin')); blobVoll = new Uint8Array(await r.arrayBuffer()); }
    return blobVoll;
  }
  const b64 = u => btoa(String.fromCharCode(...new Uint8Array(u)));
  const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  async function oeffnen(schluessel, blob) {
    if (!('DecompressionStream' in window)) throw new Error('alt');
    const klar = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: blob.slice(24, 36), additionalData: blob.slice(0, 8) }, schluessel, blob.slice(36));
    const text = await new Response(new Blob([klar]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
    INTERN = JSON.parse(text);
    suchtexte(); internAnzeigen(); liste(); if (SEL) detail();
  }
  // Schlüssel: standardmässig nur für diese Sitzung (sessionStorage); «merken» legt ihn mit Ablauf im Gerät ab
  const sitzung = { lies: k => { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    merke: (k, v) => { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch (e) { /* privat */ } } };
  async function mitPasswort(pw, geraet) {
    let blob;
    try { blob = await internGanz(); } catch (e) { toast('Interner Teil konnte nicht geladen werden.'); return; }
    const runden = new DataView(blob.buffer, blob.byteOffset + 4, 4).getUint32(0);
    const salz = blob.slice(8, 24);
    const basis = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: salz, iterations: runden, hash: 'SHA-256' }, basis, { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
    try { await oeffnen(key, blob); }
    catch (e) { toast(e && e.name === 'OperationError' ? 'Passwort falsch.' : 'Entschlüsseln ist in diesem Browser nicht möglich.'); return; }
    const wert = JSON.stringify({ salz: b64(salz), key: b64(await crypto.subtle.exportKey('raw', key)), bis: Date.now() + MERKEN_TAGE * 864e5 });
    sitzung.merke('fk-schluessel', wert);
    if (geraet) merke('fk-schluessel', wert);
    toast('Entsperrt: Namen und Regionen sind sichtbar.');
  }
  async function automatisch() {
    const s = sitzung.lies('fk-schluessel') || lies('fk-schluessel'); if (!s) return;
    let gespeichert;
    try { gespeichert = JSON.parse(s); } catch (e) { sperrenOhneNeuladen(); return; }
    if (!(gespeichert.bis > Date.now())) { sperrenOhneNeuladen(); return; }
    try {
      const blob = await internGanz();
      if (b64(blob.slice(8, 24)) !== gespeichert.salz) { sperrenOhneNeuladen(); return; }   // neue Datei: Passwort neu eingeben
      await oeffnen(await crypto.subtle.importKey('raw', unb64(gespeichert.key), 'AES-GCM', false, ['decrypt']), blob);
    } catch (e) { if (e && e.name === 'OperationError') sperrenOhneNeuladen(); }
  }
  function sperrenOhneNeuladen() { merke('fk-schluessel', null); sitzung.merke('fk-schluessel', null); }
  function sperren() { sperrenOhneNeuladen(); location.reload(); }
  function adrSchalten(an) {
    if (!(INTERN && INTERN.adr)) return;
    if (an && !map.getSource('adr')) {
      map.addSource('adr', { type: 'geojson', data: INTERN.adr.geojson });
      const farbe = ['match', ['get', 'r'], ...INTERN.adr.regionen.flatMap((_, j) => [j, ADR_FARBEN[j % ADR_FARBEN.length]]), '#666'];
      map.addLayer({ id: 'adr-fill', type: 'fill', source: 'adr', paint: { 'fill-color': farbe, 'fill-opacity': 0.07 } }, 'parz');
      map.addLayer({ id: 'adr-line', type: 'line', source: 'adr', paint: { 'line-color': farbe, 'line-width': 2.2, 'line-opacity': 0.85 } }, 'parz');
    }
    if (map.getLayer('adr-fill')) for (const l of ['adr-fill', 'adr-line']) map.setLayoutProperty(l, 'visibility', an ? 'visible' : 'none');
    legende(); if (SEL) detail();
  }
  function internAnzeigen() {
    const box = $('#intern-box'), lock = $('#lock');
    if (INTERN) {
      const nN = Object.keys(INTERN.namen).length;
      box.innerHTML = `<b>Entsperrt.</b> Namen zu ${nN.toLocaleString('de-CH')} Betrieben${INTERN.adr ? ', interne Regionen' : ''}.<br><button class="knopf" id="sperren" style="margin-top:8px">Sperren</button>`;
      $('#sperren').onclick = sperren;
      lock.textContent = '● intern'; lock.classList.add('offen');
      if (INTERN.adr && !$('#adr')) {
        const l = document.createElement('label');
        l.className = 'check'; l.innerHTML = '<input type="checkbox" id="adr"> Regionen (intern)';
        $('#legende').before(l);
        $('#adr').onchange = e => { adrSchalten(e.target.checked); merke('fk-adr', e.target.checked ? '1' : null); };
        if (lies('fk-adr')) { $('#adr').checked = true; adrSchalten(true); }
      }
    } else {
      box.innerHTML = `<b>Interner Teil</b> (Namen der Betriebe, interne Regionen): verschlüsselt, nur mit Passwort.
        <form id="pwform" style="margin-top:8px"><input type="text" name="username" value="feldkarte" autocomplete="username" hidden>
        <div style="display:flex;gap:6px"><input id="pw" type="password" autocomplete="current-password" placeholder="Passwort" style="flex:1;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel)"><button class="knopf">Entsperren</button></div>
        <label class="check" style="margin-top:8px"><input type="checkbox" id="pwmerken"> Auf diesem Gerät ${MERKEN_TAGE} Tage merken</label></form>`;
      $('#pwform').onsubmit = ev => { ev.preventDefault(); mitPasswort($('#pw').value, $('#pwmerken').checked); };
      lock.textContent = '○ gesperrt'; lock.classList.remove('offen');
    }
  }
  $('#lock').onclick = () => { if (SEL) schliessen(); tab('info'); if (SCHMAL()) blatt('half'); };
  internDa = await internKopf();
  if (internDa) { internAnzeigen(); automatisch(); }
  else { $('#lock').style.display = 'none'; $('#intern-box').style.display = 'none'; }
  if (SEL) detail();
})();
