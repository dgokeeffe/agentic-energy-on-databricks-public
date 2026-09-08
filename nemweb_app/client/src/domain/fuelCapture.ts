/**
 * Fuel value capture derived from governed NEMWEB Gold observations.
 *
 * Every function here is pure and total. The screen must never compute a
 * commercial figure inline, because each of these quantities has a boundary that
 * has to be stated rather than assumed:
 *
 *  - Revenue is indicative energy value only: five-minute SCADA output times the
 *    regional reference price. It excludes FCAS, loss factors, contracts, and
 *    settlement adjustment, so it is not a settlement figure.
 *  - Capture rate is undefined, not zero, when a region's time-weighted price is
 *    zero or negative. Dividing by it would invert the sign and read as a good
 *    outcome.
 *  - Curtailment is not derivable. AEMO Current publishes no five-minute
 *    availability, so withheld output cannot be quantified from this data.
 */

/** Five-minute interval expressed as a fraction of an hour: MW × this = MWh. */
export const INTERVAL_HOURS = 5 / 60;

/** One governed observation of generation for a region and fuel at an interval. */
export interface FuelGenerationRow {
  intervalEnd: string;
  regionId: string;
  /** AEMO CO2E_ENERGY_SOURCE text, or 'UNKNOWN' when the dimension did not match. */
  fuelType: string;
  /** Signed sum. Negative means net consumption, such as a charging battery. */
  actualGenerationMw: number;
  facilityCount: number;
  /** Facilities missing region or fuel enrichment, retained rather than dropped. */
  partiallyEnrichedFacilityCount: number;
}

/** One governed observation of regional price for an interval. */
export interface RegionPriceRow {
  intervalEnd: string;
  regionId: string;
  rrpAudPerMwh: number;
  /** AEMO price re-run number. Greater than 1 means the price was restated. */
  priceSourceRunNo: number;
}

/**
 * Open Electricity fuel-technology tokens, restricted to those the AEMO fuel
 * field can actually justify.
 *
 * Deliberately absent: gas_ccgt and gas_ocgt. CO2E_ENERGY_SOURCE distinguishes
 * "Natural Gas" but not turbine technology, so splitting it would be a guess
 * rendered as fact in a colour.
 */
export type FuelToken =
  | 'coal_black'
  | 'coal_brown'
  | 'gas'
  | 'distillate'
  | 'hydro'
  | 'wind'
  | 'solar_utility'
  | 'battery_charging'
  | 'battery_discharging'
  | 'bioenergy_biomass'
  | 'unknown';

const FUEL_TOKEN_BY_SOURCE: Record<string, FuelToken> = {
  'black coal': 'coal_black',
  coal: 'coal_black',
  'brown coal': 'coal_brown',
  lignite: 'coal_brown',
  'natural gas': 'gas',
  gas: 'gas',
  'coal seam methane': 'gas',
  'gas other': 'gas',
  diesel: 'distillate',
  distillate: 'distillate',
  kerosene: 'distillate',
  hydro: 'hydro',
  water: 'hydro',
  wind: 'wind',
  solar: 'solar_utility',
  battery: 'battery_discharging',
  'battery storage': 'battery_discharging',
  bagasse: 'bioenergy_biomass',
  biomass: 'bioenergy_biomass',
  landfill: 'bioenergy_biomass',
  'landfill methane / landfill gas': 'bioenergy_biomass',
  biogas: 'bioenergy_biomass',
};

const FUEL_LABELS: Record<FuelToken, string> = {
  coal_black: 'Black coal',
  coal_brown: 'Brown coal',
  gas: 'Gas',
  distillate: 'Distillate',
  hydro: 'Hydro',
  wind: 'Wind',
  solar_utility: 'Solar (utility)',
  battery_charging: 'Battery charging',
  battery_discharging: 'Battery discharging',
  bioenergy_biomass: 'Bioenergy',
  unknown: 'Unattributed fuel',
};

/**
 * Map an AEMO fuel-source string to a display token.
 *
 * Unrecognised values become 'unknown' rather than being force-fitted to the
 * nearest token, so an unmapped fuel is visible as unattributed instead of
 * silently inflating a real category.
 */
export function fuelToken(fuelType: string): FuelToken {
  return FUEL_TOKEN_BY_SOURCE[fuelType.trim().toLowerCase()] ?? 'unknown';
}

export function fuelLabel(token: FuelToken): string {
  return FUEL_LABELS[token];
}

/**
 * Resolve the display token for one observation.
 *
 * Storage is the one case where the signed MW carries the meaning: a battery
 * consuming energy is charging, and calling that "generation" would misreport
 * both its volume and the sign of its revenue.
 */
export function observationToken(row: FuelGenerationRow): FuelToken {
  const token = fuelToken(row.fuelType);
  if (token === 'battery_discharging' && row.actualGenerationMw < 0) return 'battery_charging';
  return token;
}

export interface FuelCapture {
  token: FuelToken;
  label: string;
  /** Signed energy over the window. Negative for net consumption. */
  energyMwh: number;
  /** Indicative energy value: Σ MW × interval hours × RRP. Never a settlement figure. */
  revenueAud: number;
  /**
   * Volume-weighted market price across this fuel's own volume, or null when
   * energy is zero.
   *
   * For a net generator this is the price received. For a net consumer such as a
   * charging battery it is the price paid, so a negative value means the fuel was
   * paid to consume.
   */
  volumeWeightedPriceAudPerMwh: number | null;
  /**
   * Volume-weighted price ÷ regional time-weighted price.
   *
   * Null whenever the ratio would not be meaningful:
   *  - zero energy, so there is no weighted price;
   *  - a regional time-weighted price at or below zero, where dividing inverts
   *    the sign and would display a loss as outperformance;
   *  - net consumption, because capture rate measures what a seller received and
   *    a buyer paying little is a good outcome that the same ratio would score as
   *    a bad one.
   */
  captureRate: number | null;
  /**
   * Value accrued during intervals priced below zero.
   *
   * Negative means value destroyed: generating while the price was negative.
   * Positive means value earned: consuming while the price was negative, which is
   * a battery being paid to charge.
   */
  negativePriceCostAud: number;
  negativePriceIntervalCount: number;
  intervalCount: number;
  facilityCountHigh: number;
  partiallyEnrichedFacilityCount: number;
}

export interface RegionCapture {
  regionId: string;
  /** Simple mean of interval prices: the price a passive participant would see. */
  timeWeightedPriceAudPerMwh: number;
  intervalCount: number;
  negativePriceIntervalCount: number;
  restatedIntervalCount: number;
  totalEnergyMwh: number;
  totalRevenueAud: number;
  totalNegativePriceCostAud: number;
  fuels: FuelCapture[];
  earliestIntervalEnd: string;
  latestIntervalEnd: string;
}

function priceKey(regionId: string, intervalEnd: string) {
  return `${regionId}|${intervalEnd}`;
}

interface FuelAccumulator {
  energyMwh: number;
  revenueAud: number;
  negativePriceCostAud: number;
  negativePriceIntervalCount: number;
  intervalCount: number;
  facilityCountHigh: number;
  partiallyEnrichedFacilityCount: number;
}

function emptyAccumulator(): FuelAccumulator {
  return {
    energyMwh: 0,
    revenueAud: 0,
    negativePriceCostAud: 0,
    negativePriceIntervalCount: 0,
    intervalCount: 0,
    facilityCountHigh: 0,
    partiallyEnrichedFacilityCount: 0,
  };
}

/**
 * Compute per-fuel value capture for one region.
 *
 * Generation rows without a matching price row are skipped: revenue requires
 * both, and substituting a nearby or default price would fabricate value.
 */
export function regionCapture(
  regionId: string,
  generation: FuelGenerationRow[],
  prices: RegionPriceRow[]
): RegionCapture | null {
  const regionPrices = prices.filter((price) => price.regionId === regionId);
  if (regionPrices.length === 0) return null;

  const priceByInterval = new Map<string, RegionPriceRow>();
  for (const price of regionPrices) priceByInterval.set(priceKey(price.regionId, price.intervalEnd), price);

  const intervalEnds = [...new Set(regionPrices.map((price) => price.intervalEnd))].sort();
  const timeWeightedPrice = regionPrices.reduce((total, price) => total + price.rrpAudPerMwh, 0) / regionPrices.length;

  const accumulators = new Map<FuelToken, FuelAccumulator>();
  for (const row of generation) {
    if (row.regionId !== regionId) continue;
    const price = priceByInterval.get(priceKey(row.regionId, row.intervalEnd));
    if (!price) continue;

    const token = observationToken(row);
    const accumulator = accumulators.get(token) ?? emptyAccumulator();
    const energyMwh = row.actualGenerationMw * INTERVAL_HOURS;
    const revenueAud = energyMwh * price.rrpAudPerMwh;

    accumulator.energyMwh += energyMwh;
    accumulator.revenueAud += revenueAud;
    accumulator.intervalCount += 1;
    accumulator.facilityCountHigh = Math.max(accumulator.facilityCountHigh, row.facilityCount);
    accumulator.partiallyEnrichedFacilityCount = Math.max(
      accumulator.partiallyEnrichedFacilityCount,
      row.partiallyEnrichedFacilityCount
    );
    if (price.rrpAudPerMwh < 0) {
      accumulator.negativePriceCostAud += revenueAud;
      accumulator.negativePriceIntervalCount += 1;
    }
    accumulators.set(token, accumulator);
  }

  const comparable = timeWeightedPrice > 0;
  const fuels: FuelCapture[] = [...accumulators.entries()]
    .map(([token, accumulator]) => {
      const volumeWeightedPrice = accumulator.energyMwh === 0 ? null : accumulator.revenueAud / accumulator.energyMwh;
      const rateApplies = volumeWeightedPrice !== null && comparable && accumulator.energyMwh > 0;
      return {
        token,
        label: fuelLabel(token),
        energyMwh: accumulator.energyMwh,
        revenueAud: accumulator.revenueAud,
        volumeWeightedPriceAudPerMwh: volumeWeightedPrice,
        captureRate: rateApplies ? volumeWeightedPrice / timeWeightedPrice : null,
        negativePriceCostAud: accumulator.negativePriceCostAud,
        negativePriceIntervalCount: accumulator.negativePriceIntervalCount,
        intervalCount: accumulator.intervalCount,
        facilityCountHigh: accumulator.facilityCountHigh,
        partiallyEnrichedFacilityCount: accumulator.partiallyEnrichedFacilityCount,
      };
    })
    // Largest absolute energy first: a heavily charging battery is as
    // significant to the reader as a heavily generating coal unit.
    .sort((left, right) => Math.abs(right.energyMwh) - Math.abs(left.energyMwh));

  return {
    regionId,
    timeWeightedPriceAudPerMwh: timeWeightedPrice,
    intervalCount: intervalEnds.length,
    negativePriceIntervalCount: regionPrices.filter((price) => price.rrpAudPerMwh < 0).length,
    restatedIntervalCount: regionPrices.filter((price) => price.priceSourceRunNo > 1).length,
    totalEnergyMwh: fuels.reduce((total, fuel) => total + fuel.energyMwh, 0),
    totalRevenueAud: fuels.reduce((total, fuel) => total + fuel.revenueAud, 0),
    totalNegativePriceCostAud: fuels.reduce((total, fuel) => total + fuel.negativePriceCostAud, 0),
    fuels,
    earliestIntervalEnd: intervalEnds[0],
    latestIntervalEnd: intervalEnds[intervalEnds.length - 1],
  };
}

/** Regions present in the price observations, ordered for stable display. */
export function capturedRegions(prices: RegionPriceRow[]): string[] {
  return [...new Set(prices.map((price) => price.regionId))].sort();
}

/**
 * The region where the value question is most urgent: the one whose weakest fuel
 * captured the least.
 *
 * This is a starting point, not a claim that other regions are healthy. An
 * alphabetical default lands on whichever region sorts first, which is arbitrary
 * and routinely the least interesting; an analyst opening this screen wants the
 * exposure that most needs explaining. Every region stays selectable.
 *
 * Falls back to the first region alphabetically when no capture rate is
 * comparable anywhere, so the choice is always defined.
 */
export function mostExposedRegion(generation: FuelGenerationRow[] | null, prices: RegionPriceRow[]): string | null {
  const regions = capturedRegions(prices);
  if (regions.length === 0) return null;
  if (!generation) return regions[0];

  let chosen: string | null = null;
  let lowestRate = Number.POSITIVE_INFINITY;
  for (const region of regions) {
    const capture = regionCapture(region, generation, prices);
    if (!capture) continue;
    const weakest = weakestCapture(capture);
    if (weakest?.captureRate === null || weakest?.captureRate === undefined) continue;
    if (weakest.captureRate < lowestRate) {
      lowestRate = weakest.captureRate;
      chosen = region;
    }
  }
  return chosen ?? regions[0];
}

/**
 * The fuel that gave away the most value: lowest capture rate.
 *
 * Fuels with an undefined capture rate are excluded, since "unknown" is not a
 * worse outcome than a measured one. That exclusion already covers net consumers,
 * because regionCapture withholds a rate for them.
 */
export function weakestCapture(capture: RegionCapture): FuelCapture | null {
  const ranked = capture.fuels.filter((fuel) => fuel.captureRate !== null);
  if (ranked.length === 0) return null;
  return ranked.reduce((weakest, fuel) => ((fuel.captureRate ?? 0) < (weakest.captureRate ?? 0) ? fuel : weakest));
}

export function formatAud(value: number): string {
  const rounded = Math.round(value);
  const sign = rounded < 0 ? '−' : '';
  return `${sign}A$${Math.abs(rounded).toLocaleString('en-AU')}`;
}

export function formatMwh(value: number): string {
  const sign = value < 0 ? '−' : '';
  return `${sign}${Math.abs(value).toLocaleString('en-AU', { maximumFractionDigits: 1 })} MWh`;
}

export function formatCaptureRate(rate: number | null): string {
  return rate === null ? 'Not comparable' : `${rate.toFixed(2)}×`;
}

export function formatPrice(value: number | null): string {
  if (value === null) return 'Unavailable';
  const sign = value < 0 ? '−' : '';
  return `${sign}A$${Math.abs(value).toFixed(2)}/MWh`;
}
