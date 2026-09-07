import { expect, test } from '@playwright/test';

test('prepared regional operations journey exposes source and semantic labels', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Current NEM regional conditions' })).toBeVisible();
  await expect(page.getByText('Prepared non-live fixture')).toBeVisible();
  await expect(page.getByRole('table', { name: 'Regional dispatch price and demand' })).toBeVisible();
  await expect(page.getByText('NEMWEB publication')).toBeVisible();
  await expect(page.getByText('market-wide, AEMO source sign, MW')).toBeVisible();
  await expect(page.getByText(/No regional allocation or directional interpretation/)).toBeVisible();
  await expect(page.getByLabel('Decision')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Record investigation' })).toBeVisible();
});
