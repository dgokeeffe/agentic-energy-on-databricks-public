/**
 * Real NEM generator map: facility topology joined to governed per-unit output.
 *
 * Every function here is pure and total. Two boundaries are enforced by the
 * types rather than by convention:
 *
 *  - `actualGenerationMw` is metered output, never a dispatch target. AEMO
 *    Current publishes no five-minute unit availability, so nothing here
 *    supports a curtailment, availability, or withheld-output claim.
 *  - A facility whose DUIDs are absent from the dispatch read is reported as
 *    uncovered rather than drawn at zero. Drawing it at zero would be
 *    indistinguishable from a station that ran and produced nothing.
 *
 * Coordinates are static public reference data (see ATTRIBUTION.md in
 * ../data/topology). Output is governed. Nothing on this surface is synthetic.
 */

import { fuelToken, fuelLabel, type FuelToken } from './fuelCapture';

/** One facility from the static coordinate reference. */
export interface NemFacility {
  facilityCode: string;
  facilityName: string;
  regionId: string;
  latitude: number;
  longitude: number;
  /** DUIDs registered at this facility. Join key to unit dispatch. */
  duids: string[];
}

/** One governed observation of per-unit output at a five-minute interval. */
export interface UnitDispatchRow {
  intervalEnd: string;
  duid: string;
  /** Signed. Negative means net consumption, such as a charging battery. */
  actualGenerationMw: number;
  regionId: string;
  /** AEMO CO2E_ENERGY_SOURCE text, or 'UNKNOWN' when the dimension missed. */
  fuelType: string;
  registeredCapacityMw: number | null;
  /** 'MATCHED' or 'UNMATCHED' against the monthly facility dimension. */
  dimensionMatchStatus: string;
}

/** A facility positioned for drawing, with its governed output resolved. */
export interface MappedFacility {
  facilityCode: string;
  facilityName: string;
  regionId: string;
  latitude: number;
  longitude: number;
  /** viewBox coordinates produced by `project`. */
  x: number;
  y: number;
  /** Signed sum across the facility's covered DUIDs. */
  netGenerationMw: number;
  /** Dominant fuel by absolute output, for colour only. */
  token: FuelToken;
  label: string;
  /** Covered DUIDs, i.e. those actually present in the dispatch read. */
  duids: string[];
}

/**
 * What the map is and is not showing.
 *
 * Reported on screen rather than logged. The reference coordinate export and
 * the governed dispatch read are maintained independently, so the intersection
 * is the honest subject of the map and its size must be visible.
 */
export interface MapCoverage {
  /** Facilities drawn, i.e. with at least one DUID in the dispatch read. */
  facilitiesDrawn: number;
  /** Facilities in the reference data with no DUID in the dispatch read. */
  facilitiesWithoutOutput: number;
  /** DUIDs in the dispatch read matched to a known facility. */
  duidsMatched: number;
  /** DUIDs in the dispatch read with no coordinate. Absent from the map. */
  duidsWithoutCoordinates: string[];
  /** Output present in the read but not drawable, as an absolute sum. */
  unmappedAbsoluteMw: number;
}

/**
 * Fixed NEM footprint. Deliberately not derived from the data: a bounding box
 * computed from whichever facilities happen to be generating would reshape the
 * map between intervals, moving every other station on screen.
 */
export const NEM_BOUNDS = {
  minLatitude: -43.7,
  maxLatitude: -10.0,
  minLongitude: 128.5,
  maxLongitude: 154.5,
} as const;

export interface ViewBox {
  width: number;
  height: number;
}

/**
 * Equirectangular projection into viewBox coordinates.
 *
 * Longitude is scaled by cos(mean latitude) so the NEM footprint is not
 * horizontally stretched. This is a display projection for a workshop screen,
 * not a geodetic one: it is not equal-area and must not be used to measure
 * distance or to infer electrical distance between stations.
 */
export function project(
  latitude: number,
  longitude: number,
  view: ViewBox,
  bounds: typeof NEM_BOUNDS = NEM_BOUNDS
): { x: number; y: number } {
  const meanLatitude = (bounds.minLatitude + bounds.maxLatitude) / 2;
  const lonScale = Math.cos((meanLatitude * Math.PI) / 180);

  const spanLon = (bounds.maxLongitude - bounds.minLongitude) * lonScale;
  const spanLat = bounds.maxLatitude - bounds.minLatitude;

  const xFraction = ((longitude - bounds.minLongitude) * lonScale) / spanLon;
  // Screen y grows downward while latitude grows northward, so this inverts.
  const yFraction = (bounds.maxLatitude - latitude) / spanLat;

  return { x: xFraction * view.width, y: yFraction * view.height };
}

/**
 * Reduce a dispatch read to its most recent interval.
 *
 * The governed query returns a bounded trailing window across all units, so a
 * map drawn from the whole result would overlay several intervals at once.
 */
export function latestIntervalRows(rows: UnitDispatchRow[]): UnitDispatchRow[] {
  if (rows.length === 0) return [];
  // The length guard above already establishes the first element, so no non-null
  // assertion is needed or permitted here.
  let latest = rows[0].intervalEnd;
  for (const row of rows) {
    if (Date.parse(row.intervalEnd) > Date.parse(latest)) latest = row.intervalEnd;
  }
  return rows.filter((row) => row.intervalEnd === latest);
}

/**
 * Resolve the display token for one unit observation.
 *
 * Mirrors `observationToken` in fuelCapture.ts deliberately: the battery sign
 * rule must hold identically for a per-unit row, which is a different shape
 * from the per-region row that function accepts.
 */
function unitToken(row: UnitDispatchRow): FuelToken {
  const token = fuelToken(row.fuelType);
  if (token === 'battery_discharging' && row.actualGenerationMw < 0) return 'battery_charging';
  return token;
}

/**
 * Join static facility coordinates to a governed dispatch read.
 *
 * Returns only facilities with at least one covered DUID, plus the coverage
 * that explains everything omitted.
 */
export function joinFacilitiesToDispatch(
  facilities: NemFacility[],
  rows: UnitDispatchRow[],
  view: ViewBox
): { facilities: MappedFacility[]; coverage: MapCoverage } {
  const byDuid = new Map<string, UnitDispatchRow>();
  for (const row of rows) byDuid.set(row.duid, row);

  const mapped: MappedFacility[] = [];
  const matchedDuids = new Set<string>();
  let facilitiesWithoutOutput = 0;

  for (const facility of facilities) {
    const covered = facility.duids.filter((duid) => byDuid.has(duid));
    if (covered.length === 0) {
      facilitiesWithoutOutput += 1;
      continue;
    }

    let net = 0;
    // Dominant fuel is decided by absolute output, so a charging battery at a
    // mixed site still colours the dot rather than being cancelled out.
    const weightByToken = new Map<FuelToken, number>();
    for (const duid of covered) {
      matchedDuids.add(duid);
      const row = byDuid.get(duid)!;
      net += row.actualGenerationMw;
      const token = unitToken(row);
      weightByToken.set(token, (weightByToken.get(token) ?? 0) + Math.abs(row.actualGenerationMw));
    }

    let token: FuelToken = 'unknown';
    let best = -1;
    // Ties resolve by token name so the colour is stable between renders.
    for (const [candidate, weight] of [...weightByToken.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      if (weight > best) {
        best = weight;
        token = candidate;
      }
    }

    const { x, y } = project(facility.latitude, facility.longitude, view);
    mapped.push({
      facilityCode: facility.facilityCode,
      facilityName: facility.facilityName,
      regionId: facility.regionId,
      latitude: facility.latitude,
      longitude: facility.longitude,
      x,
      y,
      netGenerationMw: net,
      token,
      label: fuelLabel(token),
      duids: covered,
    });
  }

  const duidsWithoutCoordinates: string[] = [];
  let unmappedAbsoluteMw = 0;
  for (const row of rows) {
    if (matchedDuids.has(row.duid)) continue;
    duidsWithoutCoordinates.push(row.duid);
    unmappedAbsoluteMw += Math.abs(row.actualGenerationMw);
  }
  duidsWithoutCoordinates.sort();

  // Largest last so smaller dots are not hidden underneath larger ones.
  mapped.sort((a, b) => Math.abs(a.netGenerationMw) - Math.abs(b.netGenerationMw));

  return {
    facilities: mapped,
    coverage: {
      facilitiesDrawn: mapped.length,
      facilitiesWithoutOutput,
      duidsMatched: matchedDuids.size,
      duidsWithoutCoordinates,
      unmappedAbsoluteMw,
    },
  };
}

/**
 * Dot radius with area proportional to output, so a 2,000 MW station does not
 * read as ten times a 200 MW one.
 */
export function radiusFor(generationMw: number, maxAbsoluteMw: number, minRadius = 3, maxRadius = 15): number {
  const magnitude = Math.abs(generationMw);
  if (maxAbsoluteMw <= 0 || magnitude <= 0) return minRadius;
  const fraction = Math.sqrt(magnitude) / Math.sqrt(maxAbsoluteMw);
  return minRadius + fraction * (maxRadius - minRadius);
}

/** Largest absolute output on the map, for radius scaling. */
export function peakAbsoluteMw(facilities: MappedFacility[]): number {
  return facilities.reduce((peak, facility) => Math.max(peak, Math.abs(facility.netGenerationMw)), 0);
}

/** Where a region's label and shading belong, derived from its facilities. */
export interface RegionAnchor {
  regionId: string;
  /** Centroid of the region's facilities, in viewBox coordinates. */
  x: number;
  y: number;
  /** Top of the region's extent, so a label clears its own stations. */
  labelY: number;
  /** Radius covering the region's spread, for background shading. */
  radius: number;
}

/**
 * Region label and shading positions computed from the coordinate reference.
 *
 * Derived rather than hand-placed. An earlier version positioned these by eye
 * and put every label in the wrong place — NSW1 about 100 units above its own
 * stations, and TAS1's label over Victoria. Computing them from the same
 * projection the dots use cannot drift from the dots.
 *
 * Takes the full facility reference, not the drawn subset, so labels stay put
 * between intervals as individual stations start and stop generating.
 */
export function regionAnchors(facilities: NemFacility[], view: ViewBox): RegionAnchor[] {
  const points = new Map<string, { x: number; y: number }[]>();
  for (const facility of facilities) {
    const projected = project(facility.latitude, facility.longitude, view);
    const list = points.get(facility.regionId);
    if (list) list.push(projected);
    else points.set(facility.regionId, [projected]);
  }

  return [...points.entries()]
    .map(([regionId, list]) => {
      const xs = list.map((point) => point.x);
      const ys = list.map((point) => point.y);
      const x = xs.reduce((total, value) => total + value, 0) / xs.length;
      const y = ys.reduce((total, value) => total + value, 0) / ys.length;
      const halfWidth = (Math.max(...xs) - Math.min(...xs)) / 2;
      const halfHeight = (Math.max(...ys) - Math.min(...ys)) / 2;
      return {
        regionId,
        x,
        y,
        // Above the northernmost station, with room for two lines of text.
        labelY: Math.max(Math.min(...ys) - 14, 12),
        // Covers the region's own spread rather than a fixed radius, so a
        // compact region such as TAS1 does not wash over its neighbours.
        radius: Math.max(Math.hypot(halfWidth, halfHeight), 28),
      };
    })
    .sort((a, b) => a.regionId.localeCompare(b.regionId));
}

/** Regional totals, summed only over facilities actually drawn. */
export function regionTotals(facilities: MappedFacility[]): { regionId: string; netGenerationMw: number }[] {
  const totals = new Map<string, number>();
  for (const facility of facilities) {
    totals.set(facility.regionId, (totals.get(facility.regionId) ?? 0) + facility.netGenerationMw);
  }
  return [...totals.entries()]
    .map(([regionId, netGenerationMw]) => ({ regionId, netGenerationMw }))
    .sort((a, b) => a.regionId.localeCompare(b.regionId));
}
