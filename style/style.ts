// The basemap's MapLibre style: Protomaps' light flavour for land, roads and names, with
// our depth bands, isobaths and relief worked in around it.
//
// Order, bottom to top: the sea's colour, depth bands, land, inland water, relief,
// isobaths, roads, labels. Land is drawn over the bands, so the coastline is
// OpenStreetMap's and not the depth grid's zero, whose vertical datum differs between
// sources (decision 073).

import { layers, namedFlavor, type Flavor } from '@protomaps/basemaps';
import type { LayerSpecification, StyleSpecification } from 'maplibre-gl';

/** How the seafloor and land are shaded. */
export type Relief = 'baked' | 'live' | 'none';

export interface Options {
  /** Where the archives are, ending in a slash, e.g. `https://tiles.salishsea.io/v1/`. */
  base: string;
  relief: Relief;
  /** How much of the relief shows, 0 to 1. Decision 073 starts at about a half. */
  reliefStrength?: number;
}

/** Depth in metres (positive down) where each band starts, and its tint: darker is deeper. */
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
const ISOBATH_LINE = '#7aa3c2';

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

function depthLayers(): { bands: LayerSpecification[]; isobaths: LayerSpecification[]; labels: LayerSpecification[] } {
  const tint: unknown[] = ['step', ['get', 'depth']];
  DEPTH_TINTS.forEach(([depth, colour], i) => {
    if (i === 0) tint.push(colour);
    else tint.push(depth, colour);
  });
  const minzoom: unknown[] = ['match', ['get', 'depth']];
  for (const [depth, zoom] of ISOBATH_MINZOOM) minzoom.push(depth, zoom);
  minzoom.push(12); // the others, unlabelled until z13

  return {
    bands: [{
      id: 'depth_bands', type: 'fill', source: 'depth', 'source-layer': 'bands',
      paint: { 'fill-color': tint as never, 'fill-antialias': false },
    }],
    isobaths: [{
      id: 'isobaths', type: 'line', source: 'depth', 'source-layer': 'isobaths',
      filter: ['>=', ['zoom'], minzoom] as never,
      paint: {
        'line-color': ISOBATH_LINE,
        'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.4, 12, 0.8, 15, 1.2],
        'line-opacity': 0.7,
      },
    }],
    labels: [{
      id: 'isobath_labels', type: 'symbol', source: 'depth', 'source-layer': 'isobaths',
      filter: ['>=', ['zoom'], ['+', minzoom, 1]] as never,
      layout: {
        'symbol-placement': 'line',
        'symbol-spacing': 400,
        'text-field': ['concat', ['to-string', ['get', 'depth']], ' m'],
        'text-font': ['Noto Sans Italic'],
        'text-size': 10,
        'text-max-angle': 30,
      },
      paint: { 'text-color': SEA_LABEL, 'text-halo-color': 'rgba(220,237,247,0.8)', 'text-halo-width': 1.2 },
    }],
  };
}

function reliefLayers(relief: Relief, strength: number): LayerSpecification[] {
  if (relief === 'baked') {
    return [{
      id: 'relief', type: 'raster', source: 'shade',
      paint: {
        'raster-opacity': ['interpolate', ['linear'], ['zoom'], 11.5, strength, 13, 0] as never,
        'raster-fade-duration': 0,
      },
    }];
  }
  if (relief === 'live') {
    return [{
      id: 'relief', type: 'hillshade', source: 'elevation',
      paint: {
        'hillshade-method': 'standard',
        'hillshade-exaggeration': strength,
        'hillshade-shadow-color': '#000000',
        'hillshade-highlight-color': '#ffffff',
        'hillshade-accent-color': '#000000',
      },
    }];
  }
  return [];
}

export function basemapStyle({ base, relief, reliefStrength = 0.5 }: Options): StyleSpecification {
  const protomaps = layers('protomaps', flavor) as LayerSpecification[];
  const depth = depthLayers();
  const out: LayerSpecification[] = [];
  for (const layer of protomaps) {
    if (layer.id === 'earth') out.push(...depth.bands);
    if (layer.id === 'water') {
      out.push({ ...layer, filter: ['all', ('filter' in layer && layer.filter) || true, ['!', ['in', ['get', 'kind'], ['literal', MARINE_KINDS]]]] } as LayerSpecification);
      continue;
    }
    if (layer.id === 'roads_tunnels_other_casing') out.push(...reliefLayers(relief, reliefStrength), ...depth.isobaths);
    if (layer.id === 'water_label_ocean') out.push(...depth.labels);
    out.push(layer);
  }

  const sources: StyleSpecification['sources'] = {
    protomaps: {
      type: 'vector', url: `pmtiles://${base}protomaps.pmtiles`,
      attribution: '<a href="https://protomaps.com">Protomaps</a> © <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
    },
    depth: {
      type: 'vector', url: `pmtiles://${base}depth.pmtiles`,
      attribution: 'Depths: NOAA NCEI, Natural Resources Canada. Not for navigation',
    },
  };
  if (relief === 'baked') sources.shade = { type: 'raster', url: `pmtiles://${base}shade.pmtiles`, tileSize: 512 };
  if (relief === 'live') sources.elevation = { type: 'raster-dem', url: `pmtiles://${base}elevation.pmtiles`, tileSize: 512, encoding: 'terrarium' };

  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sprite: 'https://protomaps.github.io/basemaps-assets/sprites/v4/light',
    sources,
    layers: out,
  };
}
