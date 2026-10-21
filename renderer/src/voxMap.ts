/**
 * Phase 59 (ENH-041): the VOX world map -- Natural Earth countries (public-domain data from the `world-atlas`
 * package, bundled for offline renders) decoded from TopoJSON here, without another dependency, and drawn with an
 * equirectangular projection cropped around the places the narration names.
 */
import world from "world-atlas/countries-110m.json";

type Position = [number, number];
type Topology = {
  transform: { scale: [number, number]; translate: [number, number] };
  arcs: Position[][];
  objects: { countries: { geometries: { type: string; arcs: number[][] | number[][][]; properties: { name: string } }[] } };
};
export type Country = { name: string; rings: Position[][] };
export type MapView = { west: number; east: number; south: number; north: number };

/** Decode the delta-encoded, quantized arcs into longitude/latitude points. */
export function decodeArcs(topology: Topology): Position[][] {
  const [sx, sy] = topology.transform.scale, [tx, ty] = topology.transform.translate;
  return topology.arcs.map((arc) => {
    let x = 0, y = 0;
    return arc.map(([dx, dy]) => {
      x += dx; y += dy;
      return [x * sx + tx, y * sy + ty] as Position;
    });
  });
}

/** One ring from arc indexes; a negative index (~i) is arc i reversed. Shared points are not repeated. */
export function ring(indexes: number[], arcs: Position[][]): Position[] {
  const points: Position[] = [];
  indexes.forEach((index) => {
    const arc = index < 0 ? [...arcs[~index]].reverse() : arcs[index];
    arc.forEach((point, i) => { if (i > 0 || points.length === 0) points.push(point); });
  });
  return points;
}

export function decodeCountries(topology: Topology): Country[] {
  const arcs = decodeArcs(topology);
  return topology.objects.countries.geometries.flatMap((geometry) => {
    const polygons = (geometry.type === "Polygon" ? [geometry.arcs] : geometry.type === "MultiPolygon" ? geometry.arcs : []) as number[][][];
    if (!polygons.length) return [];
    return [{ name: geometry.properties.name, rings: polygons.flatMap((polygon) => polygon.map((indexes) => ring(indexes, arcs))) }];
  });
}

let cache: Country[] | null = null;
export function countries(): Country[] {
  cache ??= decodeCountries(world as unknown as Topology);
  return cache;
}

const ALIASES: Record<string, string> = {
  usa: "United States of America", us: "United States of America", "united states": "United States of America",
  america: "United States of America", uk: "United Kingdom", britain: "United Kingdom", "great britain": "United Kingdom",
  england: "United Kingdom", korea: "South Korea", "viet nam": "Vietnam", russia: "Russia", "czech republic": "Czechia",
  holland: "Netherlands",
};

/** The Natural Earth name for a country the narration names ("USA", "Viet Nam", "Japan"…), or null. */
export function countryName(name: string): string | null {
  const key = name.trim().toLowerCase();
  const wanted = ALIASES[key] ?? name.trim();
  return countries().find((country) => country.name.toLowerCase() === wanted.toLowerCase())?.name ?? null;
}

/** A view around the places, at least 40° × 24° wide, padded, with the board's width/height ratio. */
export function viewFor(places: { lat: number; lon: number }[], ratio: number): MapView {
  const lons = places.map((place) => place.lon), lats = places.map((place) => place.lat);
  let west = Math.min(...lons), east = Math.max(...lons), south = Math.min(...lats), north = Math.max(...lats);
  const cx = (west + east) / 2, cy = (south + north) / 2;
  let width = Math.max(40, (east - west) * 1.5), height = Math.max(24, (north - south) * 1.5);
  if (width / height < ratio) width = height * ratio; else height = width / ratio;
  width = Math.min(width, 360); height = Math.min(height, 170);
  west = cx - width / 2; east = cx + width / 2; south = cy - height / 2; north = cy + height / 2;
  if (west < -180) { east -= west + 180; west = -180; }
  if (east > 180) { west -= east - 180; east = 180; }
  if (south < -85) { north -= south + 85; south = -85; }
  if (north > 85) { south -= north - 85; north = 85; }
  return { west, east, south, north };
}

export function project([lon, lat]: Position, view: MapView, width: number, height: number): Position {
  return [((lon - view.west) / (view.east - view.west)) * width, ((view.north - lat) / (view.north - view.south)) * height];
}

/** SVG path data of one country in the view (rings entirely outside it are skipped). */
export function countryPath(country: Country, view: MapView, width: number, height: number): string {
  return country.rings
    .filter((points) => points.some(([lon, lat]) => lon >= view.west - 20 && lon <= view.east + 20 && lat >= view.south - 20 && lat <= view.north + 20))
    .map((points) => "M" + points.map((point) => project(point, view, width, height).map((v) => v.toFixed(1)).join(",")).join("L") + "Z")
    .join("");
}
