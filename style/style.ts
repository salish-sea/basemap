// The basemap's MapLibre style: Protomaps' light flavour for land, roads and names, with
// our depth bands, isobaths and relief worked in around it.
//
// Order, bottom to top: the sea's colour, depth bands, land, inland water, relief,
// isobaths, ferry routes, roads, boundaries, labels. Land is drawn over the bands, so the coastline is
// OpenStreetMap's and not the depth grid's zero, whose vertical datum differs between
// sources (decision 073).

import { layers, namedFlavor, type Flavor } from '@protomaps/basemaps';
import type { LayerSpecification, StyleSpecification } from 'maplibre-gl';

/** How much of the relief shows by default: enough to give the seafloor shape, not so much that it competes with the depth tints. */
export const DEFAULT_RELIEF_STRENGTH = 0.25;

export interface Options {
  /** Where the archives are, ending in a slash, e.g. `https://tiles.salishsea.io/v1/`. */
  base: string;
  /** Whether to shade the seafloor and land. MapLibre shades them from elevation tiles. */
  relief?: boolean;
  /** How much of the relief shows, 0 to 1. */
  reliefStrength?: number;
}

/** Depth in metres (positive down) where each band starts, and its tint: darker is deeper. The last band runs to the seafloor's lowest point. */
export const DEPTH_TINTS: [number, string][] = [
  [0, '#dcedf7'], [5, '#d8ebf6'], [10, '#d3e8f5'], [20, '#cde5f3'], [30, '#c8e2f1'],
  [50, '#c3deeb'], [75, '#bcd9e8'], [100, '#b5d4e5'], [150, '#aecfe2'], [200, '#a6c9de'],
  [300, '#9fc3da'], [500, '#97bcd6'], [1000, '#8fb4d1'], [2000, '#86abcb'],
];

/** Isobaths that are labelled, and the zoom from which each appears. */
const ISOBATH_MINZOOM: [number, number][] = [
  [10, 11], [20, 10], [50, 9], [100, 8], [200, 7], [500, 6], [1000, 5], [2000, 5],
];

const SEA_LABEL = '#3d6d8f';
/** Ferry routes: slate rather than blue, so they don't read as isobaths (decisions/005). */
const FERRY = '#5d7282';

/** Ground that dries at low tide: mud, sand and rock between the tides (decisions/004). */
const DRYING = '#e3e1cf';
const ISOBATH_LINE = '#7aa3c2';
/**
 * Rivers and streams: a clear blue, so a salmon river reads at least as plainly as the
 * highway beside it. Protomaps draws them in its water colour, which here is the
 * shallowest depth tint and vanishes against the land.
 */
const RIVER = '#86b4d8';
/** Lakes and the rivers OpenStreetMap maps as areas: a step bluer than the shallowest sea, so the Fraser reads as plainly as its narrower tributaries. */
const INLAND_WATER = '#c9e1f1';
/** The international boundary at sea: grey, like Protomaps' boundary on land (decisions/006). */
const BOUNDARY = '#8f959b';

const flavor: Flavor = {
  ...namedFlavor('light'),
  background: DEPTH_TINTS[5][1],
  water: DEPTH_TINTS[0][1],
  earth: '#f4f2ec',
  ocean_label: SEA_LABEL,
};

// Kinds of Protomaps water polygon that are the sea. They are left out, so the depth
// bands beneath show through; lakes, rivers and docks are still drawn.
const MARINE_KINDS = ['ocean', 'bay', 'strait', 'sound', 'fjord', 'reef'];

// Land is one flat colour, shaped by the relief, as on Esri's ocean basemap: what covers
// it (forest, farmland, hospitals) says nothing about where whales are and competes with
// the sightings. Parks are the exception, faintly, because many are where people watch
// from shore, such as Lime Kiln Point. Nature reserves and protected areas are left out:
// some reach out over the sea, like Boundary Bay's, and the style can't clip them to
// the land. Piers are kept, as part of the shoreline (decisions/003).
const PARK_KINDS = ['park', 'national_park'];
const PARK = '#e4eadb';

function isLandCover(id: string): boolean {
  return id === 'landcover' || (id.startsWith('landuse_') && id !== 'landuse_pier' && id !== 'landuse_park');
}

function depthLayers(): { bands: LayerSpecification[]; isobaths: LayerSpecification[]; labels: LayerSpecification[] } {
  const tint: unknown[] = ['step', ['get', 'depth']];
  DEPTH_TINTS.forEach(([depth, colour], i) => {
    if (i === 0) tint.push(colour);
    else tint.push(depth, colour);
  });

  // One line layer and one label layer per zoom at which isobaths appear. Zoom is set
  // with each layer's `minzoom` rather than inside a filter, which not every renderer
  // (the image tiles are drawn on a server) accepts.
  const byZoom = new Map<number, number[]>();
  for (const [depth, zoom] of ISOBATH_MINZOOM) byZoom.set(zoom, [...(byZoom.get(zoom) ?? []), depth]);
  const labelled = ISOBATH_MINZOOM.map(([depth]) => depth);
  const isobaths: LayerSpecification[] = [];
  const labels: LayerSpecification[] = [];
  const groups: [number, unknown[]][] = [...byZoom].map(([zoom, depths]) => [zoom, ['in', ['get', 'depth'], ['literal', depths]]]);
  // The other isobaths appear unlabelled from z12, and labelled from z13.
  groups.push([12, ['!', ['in', ['get', 'depth'], ['literal', labelled]]]]);
  for (const [zoom, filter] of groups) {
    isobaths.push({
      id: `isobaths_z${zoom}`, type: 'line', source: 'depth', 'source-layer': 'isobaths',
      minzoom: zoom, filter: filter as never,
      paint: {
        'line-color': ISOBATH_LINE,
        'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.4, 12, 0.8, 15, 1.2],
        'line-opacity': 0.7,
      },
    });
    labels.push({
      id: `isobath_labels_z${zoom + 1}`, type: 'symbol', source: 'depth', 'source-layer': 'isobaths',
      minzoom: zoom + 1, filter: filter as never,
      layout: {
        'symbol-placement': 'line',
        'symbol-spacing': 400,
        'text-field': ['concat', ['to-string', ['get', 'depth']], ' m'],
        'text-font': ['Noto Sans Italic'],
        'text-size': 10,
        'text-max-angle': 30,
      },
      paint: { 'text-color': SEA_LABEL, 'text-halo-color': 'rgba(220,237,247,0.8)', 'text-halo-width': 1.2 },
    });
  }

  return {
    // Drying ground is drawn under the land, so only what OpenStreetMap leaves as water,
    // below its high-water coastline, shows.
    bands: [{
      id: 'depth_bands', type: 'fill', source: 'depth', 'source-layer': 'bands',
      paint: { 'fill-color': tint as never, 'fill-antialias': false },
    }, {
      id: 'drying', type: 'fill', source: 'depth', 'source-layer': 'drying',
      paint: { 'fill-color': DRYING, 'fill-antialias': false },
    }],
    isobaths,
    labels,
  };
}

// Many casual sightings are made from ferries, and reports place whales by the ferry
// lanes ("south of the Edmonds–Kingston ferry lanes"), so routes show from z9 and are
// named from z11. Up to z12, routes that share a channel are drawn as one line
// (`ferries`); from z13, each route as mapped (`ferry_routes`), which also carries the
// names (decisions/005).
function ferryLayers(): { lines: LayerSpecification[]; labels: LayerSpecification[] } {
  const paint = {
    'line-color': FERRY,
    'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.8, 11, 1.1, 15, 1.6],
    'line-dasharray': [4, 3],
    'line-opacity': 0.85,
  } as const;
  return {
    lines: [
      { id: 'ferries', type: 'line', source: 'osm', 'source-layer': 'ferries', minzoom: 9, maxzoom: 13, paint: paint as never },
      { id: 'ferry_routes', type: 'line', source: 'osm', 'source-layer': 'ferry_routes', minzoom: 13, paint: paint as never },
    ],
    labels: [{
      id: 'ferry_labels', type: 'symbol', source: 'osm', 'source-layer': 'ferry_routes', minzoom: 11,
      filter: ['has', 'name'],
      layout: {
        'symbol-placement': 'line',
        'symbol-spacing': 500,
        'text-field': ['get', 'name'],
        'text-font': ['Noto Sans Regular'],
        'text-size': 10,
        'text-max-angle': 25,
        'text-offset': [0, -0.7],
      },
      paint: { 'text-color': FERRY, 'text-halo-color': 'rgba(220,237,247,0.85)', 'text-halo-width': 1.2 },
    }],
  };
}

// Names of bays, straits, channels and points from the two countries' gazetteers, and
// the boundary between them through the water (decisions/006). The names script
// (scripts/names.py) gives each name the zoom it first appears at, `minzoom`; there
// is one layer per such zoom, as for the isobaths, and the earlier a name appears, the
// higher its layer, so that it wins a place before later ones.
const WATER_NAME_ZOOMS = [6, 7, 8, 9, 10, 11, 12, 13, 14];
const POINT_NAME_ZOOMS = [10, 11, 12, 13];

/** A water body's name size in pixels at the zoom it first appears. The names script assumes 12 when it fits them. */
function waterNameSize(zoom: number): number {
  return zoom <= 8 ? 14 : zoom <= 10 ? 13 : 12;
}

// Names that appear by this zoom, which are straits, sounds, inlets and the biggest
// bays, are placed before Protomaps' island names, so that an island's name gives way
// to the strait's beside it. Later ones give way to the islands.
const LEADING_WATER_ZOOM = 9;

function marineLayers(): { boundary: LayerSpecification[]; labels: LayerSpecification[]; leading: LayerSpecification[] } {
  const halo = { 'text-color': SEA_LABEL, 'text-halo-color': 'rgba(220,237,247,0.8)', 'text-halo-width': 1.2 };
  const points: LayerSpecification[] = POINT_NAME_ZOOMS.map((zoom) => ({
    id: `point_names_z${zoom}`, type: 'symbol', source: 'marine', 'source-layer': 'names', minzoom: zoom,
    filter: ['all', ['==', ['get', 'kind'], 'point'], ['==', ['get', 'minzoom'], zoom]],
    layout: {
      'text-field': ['get', 'name'],
      'text-font': ['Noto Sans Italic'],
      'text-size': ['interpolate', ['linear'], ['zoom'], zoom, 10, zoom + 3, 12],
      // Beside the point rather than over it, on whichever side has room.
      'text-variable-anchor': ['left', 'right', 'top', 'bottom'],
      'text-radial-offset': 0.3,
      'text-max-width': 8,
      'symbol-sort-key': ['get', 'rank'],
    },
    paint: { ...halo, 'text-opacity': 0.9 },
  }));
  // A water body's label is turned to run along it, as the names script measured. The
  // earlier a name appears, the bigger it starts, and each grows a little in the three
  // zooms after it appears.
  const water: LayerSpecification[] = WATER_NAME_ZOOMS.map((zoom) => ({
    id: `water_names_z${zoom}`, type: 'symbol', source: 'marine', 'source-layer': 'names', minzoom: zoom,
    filter: ['all', ['==', ['get', 'kind'], 'water'], ['==', ['get', 'minzoom'], zoom]],
    layout: {
      'text-field': ['get', 'name'],
      'text-font': ['Noto Sans Italic'],
      'text-size': ['interpolate', ['linear'], ['zoom'], zoom, waterNameSize(zoom), zoom + 3, waterNameSize(zoom) + 3],
      'text-letter-spacing': 0.08,
      'text-rotate': ['get', 'angle'],
      'text-rotation-alignment': 'map',
      // One line: the script fitted each name as a single line.
      'text-max-width': 40,
      'symbol-sort-key': ['get', 'rank'],
    },
    paint: halo,
  }));
  return {
    boundary: [{
      id: 'boundary_at_sea', type: 'line', source: 'marine', 'source-layer': 'boundary',
      paint: {
        'line-color': BOUNDARY,
        'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.9, 12, 1.5],
        // Dash and dot, the usual mark of an international boundary, and unlike the
        // ferry routes' plain dashes.
        'line-dasharray': [5, 2, 1, 2],
      },
    }],
    labels: [...points, ...water.filter((l) => l.minzoom! > LEADING_WATER_ZOOM).reverse()],
    leading: water.filter((l) => l.minzoom! <= LEADING_WATER_ZOOM).reverse(),
  };
}

// Rivers are in the tiles from z9 and streams from z13, where Protomaps would wait
// until z14 to draw them. They are drawn under lakes and the rivers OpenStreetMap maps
// as areas, so they show on land and not as a line down the middle of the Fraser.
function riverLayers(protomaps: LayerSpecification[]): LayerSpecification[] {
  const like = (id: string) => protomaps.find((l) => l.id === id)!;
  return [
    {
      ...like('water_stream'), minzoom: 13,
      paint: { 'line-color': RIVER, 'line-width': ['interpolate', ['linear'], ['zoom'], 13, 0.6, 16, 1.2] },
    } as LayerSpecification,
    {
      ...like('water_river'),
      paint: { 'line-color': RIVER, 'line-width': ['interpolate', ['exponential', 1.6], ['zoom'], 9, 0.7, 12, 1.4, 15, 3, 18, 10] },
    } as LayerSpecification,
  ];
}

function reliefLayers(strength: number): LayerSpecification[] {
  return [{
    id: 'relief', type: 'hillshade', source: 'elevation',
    paint: {
      'hillshade-method': 'standard',
      // Fades out from z11.5 to z13: past z12 the 30 m grid is only being interpolated.
      'hillshade-exaggeration': ['interpolate', ['linear'], ['zoom'], 11.5, strength, 13, 0] as never,
      'hillshade-shadow-color': '#000000',
      'hillshade-highlight-color': '#ffffff',
      'hillshade-accent-color': '#000000',
    },
  }];
}

export function basemapStyle({ base, relief = true, reliefStrength = DEFAULT_RELIEF_STRENGTH }: Options): StyleSpecification {
  // `lang` adds the label layers; Protomaps' type definitions leave it out.
  const protomaps = layers('protomaps', flavor, { lang: 'en' } as { labelsOnly?: boolean }) as LayerSpecification[];
  const depth = depthLayers();
  const ferries = ferryLayers();
  const marine = marineLayers();
  const out: LayerSpecification[] = [];
  for (const layer of protomaps) {
    if (isLandCover(layer.id)) continue;
    if (layer.id === 'landuse_park') {
      out.push({
        ...layer,
        filter: ['in', ['get', 'kind'], ['literal', PARK_KINDS]],
        paint: { 'fill-color': PARK, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 8, 0, 10, 1] },
      } as LayerSpecification);
      continue;
    }
    if (layer.id === 'earth') out.push(...depth.bands);
    if (layer.id === 'water') {
      out.push(...riverLayers(protomaps), {
        ...layer,
        filter: ['all', ['==', ['geometry-type'], 'Polygon'], ['!', ['in', ['get', 'kind'], ['literal', MARINE_KINDS]]]],
        paint: { 'fill-color': INLAND_WATER },
      } as LayerSpecification);
      continue;
    }
    if (layer.id === 'water_river' || layer.id === 'water_stream') continue;
    if (layer.id === 'roads_tunnels_other_casing') out.push(...(relief ? reliefLayers(reliefStrength) : []), ...depth.isobaths, ...ferries.lines);
    if (layer.id === 'boundaries_country') out.push(...marine.boundary);
    if (layer.id === 'water_label_lakes') out.push(...marine.leading);
    if (layer.id === 'water_label_ocean') {
      out.push(...depth.labels, ...ferries.labels, ...marine.labels);
      // Our names replace Protomaps' for bays, straits and fjords; its names for the
      // ocean and seas stay, placed from OpenStreetMap's outlines (decisions/006).
      out.push({ ...layer, filter: ['in', 'kind', 'sea', 'ocean'] } as LayerSpecification);
      continue;
    }
    out.push(layer);
  }

  const sources: StyleSpecification['sources'] = {
    protomaps: {
      type: 'vector', url: `pmtiles://${base}protomaps.pmtiles`,
      attribution: '<a href="https://protomaps.com">Protomaps</a> © <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
    },
    osm: {
      type: 'vector', url: `pmtiles://${base}osm.pmtiles`,
      attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
    },
    marine: {
      type: 'vector', url: `pmtiles://${base}marine.pmtiles`,
      attribution: 'Names: USGS GNIS, Natural Resources Canada. Boundary: NOAA',
    },
    depth: {
      type: 'vector', url: `pmtiles://${base}depth.pmtiles`,
      attribution: 'Depths: NOAA NCEI, Natural Resources Canada, GEBCO. Not for navigation',
    },
  };
  if (relief) sources.elevation = { type: 'raster-dem', url: `pmtiles://${base}elevation.pmtiles`, tileSize: 512, encoding: 'terrarium' };

  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources,
    layers: out,
  };
}
