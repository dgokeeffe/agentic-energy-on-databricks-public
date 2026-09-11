import { expect, test } from '@playwright/test';
import regions from '../client/src/data/fixtures/region-status.json' with { type: 'json' };
import fuels from '../client/src/data/fixtures/fuel-generation.json' with { type: 'json' };
import units from '../client/src/data/fixtures/unit-dispatch.json' with { type: 'json' };

const apiRows = (rows: object[]) => rows.map((row) => Object.fromEntries(
  Object.entries(row).map(([key, value]) => [key.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`), value])
));

test('integration client reads all three Lakebase APIs', async ({ page }) => {
  await page.route('**/api/region-status', (route) => route.fulfill({ json: apiRows(regions) }));
  await page.route('**/api/fuel-generation', (route) => route.fulfill({ json: apiRows(fuels) }));
  await page.route('**/api/unit-dispatch', (route) => route.fulfill({ json: apiRows(units) }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Underlying five-minute prices' })).toBeVisible();
  await expect(page.getByText('Generation read unavailable', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Per-unit read unavailable', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'What each fuel earned in SA1' })).toBeVisible();
});

test('fuel failure and malformed units preserve regional data and investigations', async ({ page }) => {
  await page.route('**/api/region-status', (route) => route.fulfill({ json: apiRows(regions) }));
  await page.route('**/api/fuel-generation', (route) => route.fulfill({ status: 503, json: { error: 'Unavailable' } }));
  await page.route('**/api/unit-dispatch', (route) => route.fulfill({ json: [{ duid: 'missing-fields' }] }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Underlying five-minute prices' })).toBeVisible();
  await expect(page.getByText('Generation read unavailable', { exact: true })).toBeVisible();
  await expect(page.getByText('Per-unit read unavailable', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Investigate observation' }).click();
  await expect(page.getByRole('dialog').getByLabel('Investigation note')).toBeVisible();
});
