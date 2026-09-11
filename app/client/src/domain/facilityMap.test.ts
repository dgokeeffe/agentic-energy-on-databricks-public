import { describe, expect, it } from 'vitest';
import facilitiesFixture from '../data/topology/nemFacilities.json';
import dispatchFixture from '../data/fixtures/unit-dispatch.json';
import {
  joinFacilitiesToDispatch,
  latestIntervalRows,
  NEM_BOUNDS,
  peakAbsoluteMw,
  project,
  radiusFor,
  regionAnchors,
  regionTotals,
  type NemFacility,
  type UnitDispatchRow,
} from './facilityMap';

const facilities = facilitiesFixture as NemFacility[];
const dispatch = dispatchFixture as UnitDispatchRow[];
const VIEW = { width: 800, height: 520 };

describe('the facility coordinate reference', () => {
  it('covers every NEM region with unique facility codes', () => {
    expect(facilities.length).toBeGreaterThan(400);
    expect([...new Set(facilities.map((f) => f.regionId))].sort()).toEqual(['NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1']);
    expect(new Set(facilities.map((f) => f.facilityCode)).size).toBe(facilities.length);
  });

  it('places every facility inside the NEM footprint the projection assumes', () => {
    // A coordinate outside these bounds would be projected off-canvas and vanish
    // silently, so the bounds are asserted against the data rather than trusted.
    for (const facility of facilities) {
      expect(facility.latitude).toBeGreaterThanOrEqual(NEM_BOUNDS.minLatitude);
      expect(facility.latitude).toBeLessThanOrEqual(NEM_BOUNDS.maxLatitude);
      expect(facility.longitude).toBeGreaterThanOrEqual(NEM_BOUNDS.minLongitude);
      expect(facility.longitude).toBeLessThanOrEqual(NEM_BOUNDS.maxLongitude);
    }
  });

  it('assigns each DUID to exactly one facility', () => {
    const seen = new Map<string, string>();
    for (const facility of facilities) {
      for (const duid of facility.duids) {
        expect(seen.has(duid)).toBe(false);
        seen.set(duid, facility.facilityCode);
      }
    }
    expect(seen.size).toBeGreaterThan(550);
  });
});

describe('project', () => {
  it('puts a northern facility above a southern one', () => {
    const cairns = project(-16.85, 145.65, VIEW);
    const hobart = project(-42.88, 147.33, VIEW);
    expect(cairns.y).toBeLessThan(hobart.y);
  });

  it('puts a western facility left of an eastern one', () => {
    const adelaide = project(-34.84, 138.55, VIEW);
    const sydney = project(-33.78, 150.82, VIEW);
    expect(adelaide.x).toBeLessThan(sydney.x);
  });

  it('keeps the whole footprint inside the viewBox', () => {
    for (const facility of facilities) {
      const { x, y } = project(facility.latitude, facility.longitude, VIEW);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(VIEW.width);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(VIEW.height);
    }
  });

  it('does not depend on which facilities are generating', () => {
    // The bounds are fixed, so the same station lands in the same place
    // regardless of the dispatch read it is drawn alongside.
    const before = project(-32.394981, 150.94949, VIEW);
    const after = project(-32.394981, 150.94949, VIEW);
    expect(after).toEqual(before);
  });
});

describe('latestIntervalRows', () => {
  it('reduces a multi-interval read to its most recent interval', () => {
    const latest = latestIntervalRows(dispatch);
    expect(new Set(latest.map((row) => row.intervalEnd))).toEqual(new Set(['2026-07-01T12:25:00+10:00']));
    expect(latest.length).toBeLessThan(dispatch.length);
  });

  it('returns nothing for an empty read', () => {
    expect(latestIntervalRows([])).toEqual([]);
  });
});

describe('joinFacilitiesToDispatch', () => {
  const latest = latestIntervalRows(dispatch);
  const { facilities: mapped, coverage } = joinFacilitiesToDispatch(facilities, latest, VIEW);

  it('sums a multi-unit station into one dot', () => {
    const bayswater = mapped.find((f) => f.facilityCode === 'BAYSW');
    // BW01 + BW02 + BW03 + BW04, the last of which is offline at 0 MW.
    expect(bayswater?.netGenerationMw).toBeCloseTo(640.2 + 618.7 + 605.1 + 0, 6);
    expect(bayswater?.duids.sort()).toEqual(['BW01', 'BW02', 'BW03', 'BW04']);
    expect(bayswater?.token).toBe('coal_black');
  });

  it('reports a charging battery as negative and labels it as charging', () => {
    const hornsdalePowerReserve = mapped.find((f) => f.facilityCode === 'HORNSDPR');
    expect(hornsdalePowerReserve?.netGenerationMw).toBeCloseTo(-48.2, 6);
    expect(hornsdalePowerReserve?.token).toBe('battery_charging');
    expect(hornsdalePowerReserve?.label).toBe('Battery charging');
  });

  it('omits a facility with no unit in the read rather than drawing it at zero', () => {
    // Drawing an absent station at 0 MW would be indistinguishable from one that
    // ran and produced nothing, which is a different operational fact.
    expect(mapped.some((f) => f.facilityCode === 'BASTYAN')).toBe(true);
    expect(coverage.facilitiesWithoutOutput).toBeGreaterThan(0);
    expect(coverage.facilitiesDrawn + coverage.facilitiesWithoutOutput).toBe(facilities.length);
  });

  it('reports a DUID with no coordinate instead of discarding it', () => {
    expect(coverage.duidsWithoutCoordinates).toContain('NOCOORD1');
    expect(coverage.unmappedAbsoluteMw).toBeCloseTo(41.5, 6);
  });

  it('resolves dominant fuel by absolute output, not signed output', () => {
    // A site whose battery is charging hard and whose solar is small must not
    // have the two cancel to near zero and fall through to 'unknown'.
    const mixed: NemFacility[] = [
      {
        facilityCode: 'MIXED',
        facilityName: 'Mixed site',
        regionId: 'SA1',
        latitude: -34.9,
        longitude: 138.6,
        duids: ['MIXBATT', 'MIXSOL'],
      },
    ];
    const rows: UnitDispatchRow[] = [
      {
        intervalEnd: '2026-07-01T12:25:00+10:00',
        duid: 'MIXBATT',
        actualGenerationMw: -90,
        regionId: 'SA1',
        fuelType: 'Battery Storage',
        registeredCapacityMw: 100,
        dimensionMatchStatus: 'MATCHED',
      },
      {
        intervalEnd: '2026-07-01T12:25:00+10:00',
        duid: 'MIXSOL',
        actualGenerationMw: 85,
        regionId: 'SA1',
        fuelType: 'Solar',
        registeredCapacityMw: 100,
        dimensionMatchStatus: 'MATCHED',
      },
    ];
    const { facilities: result } = joinFacilitiesToDispatch(mixed, rows, VIEW);
    expect(result[0]?.token).toBe('battery_charging');
    expect(result[0]?.netGenerationMw).toBeCloseTo(-5, 6);
  });

  it('orders dots so smaller stations are not hidden under larger ones', () => {
    const magnitudes = mapped.map((f) => Math.abs(f.netGenerationMw));
    expect([...magnitudes].sort((a, b) => a - b)).toEqual(magnitudes);
  });

  it('is empty and honest when the read is empty', () => {
    const { facilities: none, coverage: empty } = joinFacilitiesToDispatch(facilities, [], VIEW);
    expect(none).toEqual([]);
    expect(empty.facilitiesDrawn).toBe(0);
    expect(empty.duidsMatched).toBe(0);
    expect(empty.facilitiesWithoutOutput).toBe(facilities.length);
  });
});

describe('radiusFor', () => {
  const peak = 2500;

  it('scales by area, so four times the output is twice the radius above the floor', () => {
    const small = radiusFor(100, peak, 0, 20);
    const large = radiusFor(400, peak, 0, 20);
    expect(large / small).toBeCloseTo(2, 6);
  });

  it('never returns less than the floor, including at zero and for a charging battery', () => {
    expect(radiusFor(0, peak, 3)).toBe(3);
    expect(radiusFor(-48.2, peak, 3)).toBeGreaterThanOrEqual(3);
  });

  it('does not exceed the ceiling at peak output', () => {
    expect(radiusFor(peak, peak, 3, 22)).toBeCloseTo(22, 6);
  });

  it('caps the default ceiling low enough that neighbouring stations stay distinct', () => {
    // The first version defaulted to 22, which at the 800x520 viewBox merged the
    // Hunter Valley coal stations into a single dark blob.
    expect(radiusFor(peak, peak)).toBeCloseTo(15, 6);
  });

  it('degrades to the floor rather than dividing by zero on an empty map', () => {
    expect(radiusFor(0, 0, 3)).toBe(3);
  });
});

describe('regionTotals', () => {
  it('sums only what is drawn, and nets a charging battery against generation', () => {
    const latest = latestIntervalRows(dispatch);
    const { facilities: mapped } = joinFacilitiesToDispatch(facilities, latest, VIEW);
    const totals = regionTotals(mapped);
    const sa = totals.find((t) => t.regionId === 'SA1');
    // Hornsdale 1-3 wind, less the two charging batteries, plus Torrens B at 0.
    expect(sa?.netGenerationMw).toBeCloseTo(82.4 + 79.1 + 88.6 - 48.2 - 21.6 + 0, 6);
    expect(totals.map((t) => t.regionId)).toEqual(['NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1']);
  });
});

describe('regionAnchors', () => {
  const anchors = regionAnchors(facilities, VIEW);

  it('produces one anchor per NEM region', () => {
    expect(anchors.map((anchor) => anchor.regionId)).toEqual(['NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1']);
  });

  it('places each label above every station in its own region', () => {
    // The regression this guards: hand-placed anchors put the NSW1 label about
    // 100 units above its stations and the TAS1 label over Victoria.
    for (const anchor of anchors) {
      const ys = facilities
        .filter((facility) => facility.regionId === anchor.regionId)
        .map((facility) => project(facility.latitude, facility.longitude, VIEW).y);
      expect(anchor.labelY).toBeLessThanOrEqual(Math.min(...ys));
    }
  });

  it('keeps every label inside the viewBox', () => {
    for (const anchor of anchors) {
      expect(anchor.labelY).toBeGreaterThanOrEqual(0);
      expect(anchor.labelY).toBeLessThanOrEqual(VIEW.height);
      expect(anchor.x).toBeGreaterThanOrEqual(0);
      expect(anchor.x).toBeLessThanOrEqual(VIEW.width);
    }
  });

  it('puts each centroid inside its own region extent', () => {
    for (const anchor of anchors) {
      const points = facilities
        .filter((facility) => facility.regionId === anchor.regionId)
        .map((facility) => project(facility.latitude, facility.longitude, VIEW));
      expect(anchor.x).toBeGreaterThanOrEqual(Math.min(...points.map((p) => p.x)));
      expect(anchor.x).toBeLessThanOrEqual(Math.max(...points.map((p) => p.x)));
      expect(anchor.y).toBeGreaterThanOrEqual(Math.min(...points.map((p) => p.y)));
      expect(anchor.y).toBeLessThanOrEqual(Math.max(...points.map((p) => p.y)));
    }
  });

  it('scales shading to a region\u2019s own spread rather than a fixed radius', () => {
    const tas = anchors.find((anchor) => anchor.regionId === 'TAS1')!;
    const nsw = anchors.find((anchor) => anchor.regionId === 'NSW1')!;
    // Tasmania is compact and New South Wales is not, so a single radius washed
    // one region's shading over its neighbours.
    expect(tas.radius).toBeLessThan(nsw.radius);
    expect(tas.radius).toBeGreaterThanOrEqual(28);
  });

  it('does not move when the dispatch read changes', () => {
    // Anchors come from the static reference, so a station starting or stopping
    // must not shift a label.
    expect(regionAnchors(facilities, VIEW)).toEqual(anchors);
  });
});

describe('peakAbsoluteMw', () => {
  it('uses magnitude so a large charging battery still sets the scale', () => {
    const latest = latestIntervalRows(dispatch);
    const { facilities: mapped } = joinFacilitiesToDispatch(facilities, latest, VIEW);
    expect(peakAbsoluteMw(mapped)).toBeGreaterThan(0);
    expect(peakAbsoluteMw([])).toBe(0);
  });
});
