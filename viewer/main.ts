// Two maps side by side, moving together, each drawing one version of the basemap.
// The URL holds the view (`#zoom/lat/lon`) and the choices (`?left=ours&right=esri`),
// so a view can be shared or screenshotted. `?picture` shows the left map alone, with
// no controls, and `?sightings=off` hides the stand-in sightings: the README's pictures
// are drawn that way (scripts/pictures.ts).

import { addProtocol, Map, setWorkerUrl, type StyleSpecification } from 'maplibre-gl';
import maplibreWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Protocol } from 'pmtiles';
import { ASSETS_PATH, basemapStyle, DEFAULT_RELIEF_STRENGTH } from '../style/style.ts';

setWorkerUrl(maplibreWorker);
addProtocol('pmtiles', new Protocol().tile);

const VARIANTS = {
  ours: 'Ours',
  flat: 'Ours, without relief',
  esri: 'Esri ocean (today)',
} as const;
type Variant = keyof typeof VARIANTS;

const params = new URLSearchParams(location.search);
// Where the archives are: /window/ while developing, or ?base=/coast/. A published viewer
// is given its version's archive URLs when it is built (scripts/publish.sh).
const base = new URL(params.get('base') ?? '/window/', location.href).href;
const archives = params.has('base') ? {} : JSON.parse(import.meta.env.VITE_TILES_ARCHIVES ?? '{}');
// A local build's fonts and icons are in build/ too (make assets); a published viewer's
// are on tiles.salishsea.io, the style's default.
const assets = params.has('base') ? new URL(`/${ASSETS_PATH}`, location.href).href : undefined;
// Hillshade exaggeration runs from 0 to 1 in MapLibre's style spec.
const requested = Number(params.get('strength') ?? DEFAULT_RELIEF_STRENGTH);
let strength = Number.isFinite(requested) ? Math.min(1, Math.max(0, requested)) : DEFAULT_RELIEF_STRENGTH;

// The app's Okabe–Ito group colours (salishsea-io src/symbology.ts).
const SIGHTING_COLOURS = ['#1a1a1a', '#0072B2', '#5B2C8D', '#56B4E9', '#009E73', '#E69F00', '#D55E00', '#CC79A7'];

function standInSightings(): GeoJSON.FeatureCollection {
  // A fixed scatter over Haro Strait and the San Juans, the same on every load.
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const features: GeoJSON.Feature[] = [];
  for (let i = 0; i < 16; i++) {
    features.push({
      type: 'Feature',
      properties: { colour: SIGHTING_COLOURS[i % SIGHTING_COLOURS.length] },
      geometry: { type: 'Point', coordinates: [-123.35 + rand() * 0.55, 48.35 + rand() * 0.45] },
    });
  }
  return { type: 'FeatureCollection', features };
}

function esriStyle(): StyleSpecification {
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sources: {
      'esri-base': {
        type: 'raster', tileSize: 256, attribution: 'Esri, GEBCO, NOAA, National Geographic, DeLorme, HERE, Geonames.org, and other contributors',
        tiles: ['https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}'],
      },
      'esri-reference': {
        type: 'raster', tileSize: 256,
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}'],
      },
    },
    layers: [
      { id: 'esri-base', type: 'raster', source: 'esri-base' },
      { id: 'esri-reference', type: 'raster', source: 'esri-reference' },
    ],
  };
}

function styleFor(variant: Variant): StyleSpecification {
  return variant === 'esri' ? esriStyle() : basemapStyle({ base, archives, assets, relief: variant === 'ours', reliefStrength: strength });
}

function addSightings(map: Map) {
  if (map.getSource('sightings')) return;
  map.addSource('sightings', { type: 'geojson', data: standInSightings() });
  map.addLayer({
    id: 'sightings', type: 'circle', source: 'sightings',
    layout: { visibility: (document.getElementById('sightings') as HTMLInputElement).checked ? 'visible' : 'none' },
    paint: { 'circle-radius': 6, 'circle-color': ['get', 'colour'], 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.5 },
  });
}

function pane(side: 'left' | 'right', initial: Variant, hash: boolean) {
  const select = document.getElementById(`${side}-variant`) as HTMLSelectElement;
  for (const [value, label] of Object.entries(VARIANTS)) select.add(new Option(label, value));
  select.value = initial;
  const map = new Map({
    container: side, style: styleFor(initial), hash,
    center: [-123.1, 48.5], zoom: 9, maxZoom: 17,
    attributionControl: { compact: true },
  });
  map.on('style.load', () => addSightings(map));
  select.addEventListener('change', () => {
    params.set(side, select.value);
    history.replaceState(null, '', `?${params}${location.hash}`);
    // No diff: a full reload fires `style.load`, which adds the stand-in sightings back.
    map.setStyle(styleFor(select.value as Variant), { diff: false });
  });
  return { map, select };
}

function variantParam(key: string, fallback: Variant): Variant {
  const value = params.get(key);
  return value !== null && value in VARIANTS ? (value as Variant) : fallback;
}

if (params.has('picture')) document.body.classList.add('picture');
if (params.get('sightings') === 'off') (document.getElementById('sightings') as HTMLInputElement).checked = false;

const left = pane('left', variantParam('left', 'ours'), true);
const right = pane('right', variantParam('right', 'esri'), false);

// Move together: whichever map the person is moving leads.
let syncing = false;
function follow(leader: Map, follower: Map) {
  leader.on('move', () => {
    if (syncing) return;
    syncing = true;
    follower.jumpTo({ center: leader.getCenter(), zoom: leader.getZoom(), bearing: leader.getBearing(), pitch: leader.getPitch() });
    syncing = false;
    document.getElementById('zoom')!.textContent = `MapLibre zoom ${leader.getZoom().toFixed(2)}`;
  });
}
follow(left.map, right.map);
follow(right.map, left.map);
right.map.jumpTo({ center: left.map.getCenter(), zoom: left.map.getZoom() });

const slider = document.getElementById('strength') as HTMLInputElement;
slider.value = String(strength);
document.getElementById('strength-value')!.textContent = String(strength);
slider.addEventListener('input', () => {
  strength = Number(slider.value);
  document.getElementById('strength-value')!.textContent = slider.value;
  params.set('strength', slider.value);
  history.replaceState(null, '', `?${params}${location.hash}`);
  for (const { map, select } of [left, right]) {
    if (select.value !== 'esri') // No diff: a full reload fires `style.load`, which adds the stand-in sightings back.
    map.setStyle(styleFor(select.value as Variant), { diff: false });
  }
});

document.getElementById('sightings')!.addEventListener('change', (e) => {
  const visible = (e.target as HTMLInputElement).checked ? 'visible' : 'none';
  for (const { map } of [left, right]) if (map.getLayer('sightings')) map.setLayoutProperty('sightings', 'visibility', visible);
});

Object.assign(window, { maps: { left: left.map, right: right.map } });
