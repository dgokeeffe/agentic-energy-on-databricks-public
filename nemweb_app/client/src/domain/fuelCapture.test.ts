import { describe, expect, it } from 'vitest';
import {
  capturedRegions,
  mostExposedRegion,
  formatAud,
  formatCaptureRate,
  formatMwh,
  formatPrice,
  fuelToken,
  observationToken,
  regionCapture,
  weakestCapture,
  type FuelGenerationRow,
  type RegionPriceRow,
} from './fuelCapture';

const generation = (overrides: Partial<FuelGenerationRow> = {}): FuelGenerationRow => ({
  intervalEnd: '2026-07-01T12:05:00+10:00',
  regionId: 'NSW1',
  fuelType: 'Black coal',
  actualGenerationMw: 1200,
  facilityCount: 4,
  partiallyEnrichedFacilityCount: 0,
  ...overrides,
});

const price = (overrides: Partial<RegionPriceRow> = {}): RegionPriceRow => ({
  intervalEnd: '2026-07-01T12:05:00+10:00',
  regionId: 'NSW1',
  rrpAudPerMwh: 100,
  priceSourceRunNo: 1,
  ...overrides,
});

describe('fuelToken', () => {
  it('maps AEMO fuel sources to Open Electricity tokens, case and space insensitively', () => {
    expect(fuelToken('Black coal')).toBe('coal_black');
    expect(fuelToken('  BROWN COAL ')).toBe('coal_brown');
    expect(fuelToken('Wind')).toBe('wind');
    expect(fuelToken('Solar')).toBe('solar_utility');
    expect(fuelToken('Bagasse')).toBe('bioenergy_biomass');
  });

  it('collapses every gas variant to one token rather than guessing turbine technology', () => {
    // CO2E_ENERGY_SOURCE cannot distinguish CCGT from OCGT, so inventing the
    // split would render a guess as a fact in a colour.
    expect(fuelToken('Natural Gas')).toBe('gas');
    expect(fuelToken('Coal seam methane')).toBe('gas');
  });

  it('returns unknown for unmapped and empty fuels instead of a nearest match', () => {
    expect(fuelToken('Geothermal')).toBe('unknown');
    expect(fuelToken('')).toBe('unknown');
    expect(fuelToken('UNKNOWN')).toBe('unknown');
  });

  it('maps every CO2E_ENERGY_SOURCE value observed in the deployed workspace', () => {
    // Read from silver_nem_facility_dimension.fuel_type_raw on 2026-09-08. The
    // first version of the mapping was written from guessed strings and sent
    // "Natural Gas (Pipeline)" and "Diesel oil" to the unknown bucket, so their
    // generation displayed as "Unattributed fuel". Only running it revealed that.
    const observed: Record<string, string> = {
      'Battery Storage': 'battery_discharging',
      'Coal seam methane': 'gas',
      'Diesel oil': 'distillate',
      Hydro: 'hydro',
      'Natural Gas (Pipeline)': 'gas',
      Solar: 'solar_utility',
      Wind: 'wind',
    };
    for (const [raw, expected] of Object.entries(observed)) {
      expect(fuelToken(raw), `${raw} must not fall through to unknown`).toBe(expected);
    }
  });

  it('maps the canonical initcap forms as well as the raw AEMO casing', () => {
    // gold_nem_scada_generation_5min carries the canonicalised fuel_type, which
    // differs in case from fuel_type_raw. Both must resolve identically.
    expect(fuelToken('Coal Seam Methane')).toBe(fuelToken('Coal seam methane'));
    expect(fuelToken('Natural Gas (pipeline)')).toBe(fuelToken('Natural Gas (Pipeline)'));
    expect(fuelToken('Diesel Oil')).toBe(fuelToken('Diesel oil'));
  });
});

describe('observationToken', () => {
  it('separates a charging battery from a discharging one using the signed MW', () => {
    expect(observationToken(generation({ fuelType: 'Battery', actualGenerationMw: 50 }))).toBe('battery_discharging');
    expect(observationToken(generation({ fuelType: 'Battery', actualGenerationMw: -50 }))).toBe('battery_charging');
  });

  it('does not reinterpret a negative reading for a non-storage fuel', () => {
    // Auxiliary load can make a thermal unit briefly negative. That is not
    // storage and must not be relabelled as charging.
    expect(observationToken(generation({ fuelType: 'Black coal', actualGenerationMw: -3 }))).toBe('coal_black');
  });
});

describe('regionCapture', () => {
  it('computes energy, indicative revenue, and capture rate against the regional time-weighted price', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ intervalEnd: '2026-07-01T12:05:00+10:00', actualGenerationMw: 1200 }),
        generation({ intervalEnd: '2026-07-01T12:10:00+10:00', actualGenerationMw: 1200 }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 50 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 150 }),
      ]
    );

    expect(capture).not.toBeNull();
    // 1200 MW × (5/60) h = 100 MWh per interval, twice.
    expect(capture!.totalEnergyMwh).toBeCloseTo(200, 6);
    // 100 MWh × $50 + 100 MWh × $150 = $20,000.
    expect(capture!.totalRevenueAud).toBeCloseTo(20_000, 6);
    expect(capture!.timeWeightedPriceAudPerMwh).toBeCloseTo(100, 6);
    // Flat output across both prices captures exactly the time-weighted price.
    expect(capture!.fuels[0].captureRate).toBeCloseTo(1, 6);
  });

  it('penalises output concentrated in the cheaper interval', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ intervalEnd: '2026-07-01T12:05:00+10:00', actualGenerationMw: 1800 }),
        generation({ intervalEnd: '2026-07-01T12:10:00+10:00', actualGenerationMw: 600 }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 50 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 150 }),
      ]
    );

    // Weighted price = (150×50 + 50×150) / 200 = $75/MWh against a $100 mean.
    expect(capture!.fuels[0].volumeWeightedPriceAudPerMwh).toBeCloseTo(75, 6);
    expect(capture!.fuels[0].captureRate).toBeCloseTo(0.75, 6);
  });

  it('reports negative-price cost separately and only for intervals priced below zero', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ intervalEnd: '2026-07-01T12:05:00+10:00', fuelType: 'Solar', actualGenerationMw: 1200 }),
        generation({ intervalEnd: '2026-07-01T12:10:00+10:00', fuelType: 'Solar', actualGenerationMw: 1200 }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: -40 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 60 }),
      ]
    );

    // Only the −$40 interval contributes: 100 MWh × −40 = −$4,000.
    expect(capture!.totalNegativePriceCostAud).toBeCloseTo(-4_000, 6);
    expect(capture!.fuels[0].negativePriceIntervalCount).toBe(1);
    expect(capture!.negativePriceIntervalCount).toBe(1);
  });

  it('treats a zero price as not negative, holding the boundary explicitly', () => {
    const capture = regionCapture('NSW1', [generation({ actualGenerationMw: 1200 })], [price({ rrpAudPerMwh: 0 })]);
    expect(capture!.negativePriceIntervalCount).toBe(0);
    expect(capture!.totalNegativePriceCostAud).toBeCloseTo(0, 6);
  });

  it('refuses a capture rate when the regional time-weighted price is not positive', () => {
    // Dividing by a negative mean inverts the sign, so a badly exposed fuel
    // would display as though it had outperformed.
    const capture = regionCapture(
      'NSW1',
      [
        generation({ intervalEnd: '2026-07-01T12:05:00+10:00', actualGenerationMw: 1200 }),
        generation({ intervalEnd: '2026-07-01T12:10:00+10:00', actualGenerationMw: 1200 }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: -60 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: -20 }),
      ]
    );

    expect(capture!.timeWeightedPriceAudPerMwh).toBeCloseTo(-40, 6);
    expect(capture!.fuels[0].captureRate).toBeNull();
    // The revenue loss is still reported; only the ratio is withheld.
    expect(capture!.totalRevenueAud).toBeLessThan(0);
  });

  it('keeps a charging battery as negative energy with its own token', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Battery', actualGenerationMw: -300, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Battery', actualGenerationMw: 300, intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 20 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 300 }),
      ]
    );

    const charging = capture!.fuels.find((fuel) => fuel.token === 'battery_charging');
    const discharging = capture!.fuels.find((fuel) => fuel.token === 'battery_discharging');
    expect(charging!.energyMwh).toBeCloseTo(-25, 6);
    expect(charging!.revenueAud).toBeCloseTo(-500, 6);
    expect(discharging!.revenueAud).toBeCloseTo(7_500, 6);
  });

  it('withholds a capture rate for a net consumer', () => {
    // Capture rate measures what a seller received. Applied to a buyer, cheap
    // energy — the good outcome — would score as the worst capture on the page,
    // and a negative charging price would produce a negative ratio.
    const capture = regionCapture(
      'NSW1',
      [generation({ fuelType: 'Battery', actualGenerationMw: -600 })],
      [price({ rrpAudPerMwh: 100 })]
    );
    const charging = capture!.fuels.find((fuel) => fuel.token === 'battery_charging');
    expect(charging!.energyMwh).toBeLessThan(0);
    expect(charging!.captureRate).toBeNull();
    // The price paid is still reported, so the buying decision stays visible.
    expect(charging!.volumeWeightedPriceAudPerMwh).toBeCloseTo(100, 6);
  });

  it('reports being paid to charge as a positive negative-interval value', () => {
    // A battery consuming at a negative price earns money. The same field must
    // therefore be able to carry a benefit, not only a cost.
    const capture = regionCapture(
      'NSW1',
      [generation({ fuelType: 'Battery', actualGenerationMw: -600 })],
      [price({ rrpAudPerMwh: -30 })]
    );
    const charging = capture!.fuels.find((fuel) => fuel.token === 'battery_charging');
    // −50 MWh × −$30 = +$1,500 earned for consuming.
    expect(charging!.negativePriceCostAud).toBeCloseTo(1_500, 6);
    expect(capture!.totalNegativePriceCostAud).toBeGreaterThan(0);
  });

  it('withholds a volume-weighted price when a fuel nets to zero energy', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Battery', actualGenerationMw: -300, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Battery', actualGenerationMw: 300, intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [
        // Equal prices, so charge and discharge net to exactly zero energy.
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 100 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 100 }),
      ]
    );

    // Signs split the tokens, so neither nets to zero here; assert the guard
    // directly on a single fuel that genuinely cancels.
    const cancelling = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Black coal', actualGenerationMw: -600, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Black coal', actualGenerationMw: 600, intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 100 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 100 }),
      ]
    );
    expect(capture!.fuels).toHaveLength(2);
    expect(cancelling!.fuels[0].energyMwh).toBeCloseTo(0, 6);
    expect(cancelling!.fuels[0].volumeWeightedPriceAudPerMwh).toBeNull();
    expect(cancelling!.fuels[0].captureRate).toBeNull();
  });

  it('skips generation with no matching price rather than substituting one', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [price({ intervalEnd: '2026-07-01T12:05:00+10:00' })]
    );

    // One priced interval only: 100 MWh, not 200.
    expect(capture!.totalEnergyMwh).toBeCloseTo(100, 6);
    expect(capture!.fuels[0].intervalCount).toBe(1);
  });

  it('ignores other regions and returns null when the region has no prices', () => {
    const rows = [generation({ regionId: 'VIC1', actualGenerationMw: 9999 }), generation()];
    const capture = regionCapture('NSW1', rows, [price()]);
    expect(capture!.fuels).toHaveLength(1);
    expect(capture!.totalEnergyMwh).toBeCloseTo(100, 6);
    expect(regionCapture('SA1', rows, [price()])).toBeNull();
  });

  it('counts restated intervals and surfaces partial enrichment', () => {
    const capture = regionCapture(
      'NSW1',
      [generation({ partiallyEnrichedFacilityCount: 2 })],
      [price({ priceSourceRunNo: 3 })]
    );
    expect(capture!.restatedIntervalCount).toBe(1);
    expect(capture!.fuels[0].partiallyEnrichedFacilityCount).toBe(2);
  });

  it('orders fuels by absolute energy so a large charging load is not buried', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Wind', actualGenerationMw: 200 }),
        generation({ fuelType: 'Battery', actualGenerationMw: -900 }),
        generation({ fuelType: 'Black coal', actualGenerationMw: 500 }),
      ],
      [price()]
    );
    expect(capture!.fuels.map((fuel) => fuel.token)).toEqual(['battery_charging', 'coal_black', 'wind']);
  });
});

describe('weakestCapture', () => {
  it('names the lowest measured capture rate among net generators', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Black coal', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Solar', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Black coal', actualGenerationMw: 1200, intervalEnd: '2026-07-01T12:10:00+10:00' }),
        generation({ fuelType: 'Solar', actualGenerationMw: 0, intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 20 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 180 }),
      ]
    );
    // Solar generated only in the cheap interval, so it captured least.
    expect(weakestCapture(capture!)!.token).toBe('solar_utility');
  });

  it('excludes net consumers, since buying cheaply is not weak capture', () => {
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Battery', actualGenerationMw: -600 }),
        generation({ fuelType: 'Wind', actualGenerationMw: 600 }),
      ],
      [price()]
    );
    expect(weakestCapture(capture!)!.token).toBe('wind');
  });

  it('never returns a fuel with a negative capture rate', () => {
    // Regression guard: a charging battery at a negative price once produced a
    // negative ratio, which ranked as the weakest capture and read as nonsense.
    const capture = regionCapture(
      'NSW1',
      [
        generation({ fuelType: 'Battery', actualGenerationMw: -600, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Wind', actualGenerationMw: 600, intervalEnd: '2026-07-01T12:05:00+10:00' }),
        generation({ fuelType: 'Wind', actualGenerationMw: 600, intervalEnd: '2026-07-01T12:10:00+10:00' }),
      ],
      [
        price({ intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: -30 }),
        price({ intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 200 }),
      ]
    );
    for (const fuel of capture!.fuels) {
      expect(fuel.captureRate === null || fuel.captureRate >= 0).toBe(true);
    }
    expect(weakestCapture(capture!)!.token).toBe('wind');
  });

  it('returns null when no fuel has a comparable rate', () => {
    const capture = regionCapture('NSW1', [generation()], [price({ rrpAudPerMwh: -50 })]);
    expect(weakestCapture(capture!)).toBeNull();
  });
});

describe('formatting', () => {
  it('uses an explicit minus sign and Australian grouping for money and energy', () => {
    expect(formatAud(1_234_567)).toBe('A$1,234,567');
    expect(formatAud(-4_000)).toBe('−A$4,000');
    expect(formatMwh(-25.5)).toBe('−25.5 MWh');
    expect(formatPrice(-40)).toBe('−A$40.00/MWh');
  });

  it('labels an incomparable capture rate rather than printing a number', () => {
    expect(formatCaptureRate(null)).toBe('Not comparable');
    expect(formatCaptureRate(0.874)).toBe('0.87×');
  });
});

describe('mostExposedRegion', () => {
  const prices = [
    // NSW1 is flat, so every fuel captures about 1.00x.
    price({ regionId: 'NSW1', intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 100 }),
    price({ regionId: 'NSW1', intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 100 }),
    // SA1 collapses, so a fuel generating into the trough captures poorly.
    price({ regionId: 'SA1', intervalEnd: '2026-07-01T12:05:00+10:00', rrpAudPerMwh: 10 }),
    price({ regionId: 'SA1', intervalEnd: '2026-07-01T12:10:00+10:00', rrpAudPerMwh: 190 }),
  ];
  const generation = [
    {
      intervalEnd: '2026-07-01T12:05:00+10:00',
      regionId: 'NSW1',
      fuelType: 'Black coal',
      actualGenerationMw: 1000,
      facilityCount: 1,
      partiallyEnrichedFacilityCount: 0,
    },
    {
      intervalEnd: '2026-07-01T12:10:00+10:00',
      regionId: 'NSW1',
      fuelType: 'Black coal',
      actualGenerationMw: 1000,
      facilityCount: 1,
      partiallyEnrichedFacilityCount: 0,
    },
    {
      intervalEnd: '2026-07-01T12:05:00+10:00',
      regionId: 'SA1',
      fuelType: 'Solar',
      actualGenerationMw: 1000,
      facilityCount: 1,
      partiallyEnrichedFacilityCount: 0,
    },
    {
      intervalEnd: '2026-07-01T12:10:00+10:00',
      regionId: 'SA1',
      fuelType: 'Solar',
      actualGenerationMw: 0,
      facilityCount: 1,
      partiallyEnrichedFacilityCount: 0,
    },
  ];

  it('chooses the region whose weakest fuel captured least, not the first alphabetically', () => {
    expect(capturedRegions(prices)[0]).toBe('NSW1');
    expect(mostExposedRegion(generation, prices)).toBe('SA1');
  });

  it('falls back to the first region when generation is unavailable or incomparable', () => {
    expect(mostExposedRegion(null, prices)).toBe('NSW1');
    const negativePrices = [
      price({ regionId: 'NSW1', rrpAudPerMwh: -50 }),
      price({ regionId: 'SA1', rrpAudPerMwh: -90 }),
    ];
    expect(mostExposedRegion(generation, negativePrices)).toBe('NSW1');
    expect(mostExposedRegion(generation, [])).toBeNull();
  });
});

describe('capturedRegions', () => {
  it('returns sorted unique regions from the price observations', () => {
    expect(capturedRegions([price({ regionId: 'VIC1' }), price(), price({ regionId: 'VIC1' })])).toEqual([
      'NSW1',
      'VIC1',
    ]);
  });
});
