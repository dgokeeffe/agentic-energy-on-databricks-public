import { expect, test } from '@playwright/test';

test('prepared value-capture journey keeps region focus and journal context aligned', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('navigation', { name: 'Primary navigation' })).toBeVisible();

  // The screen opens on the region with the weakest capture, which in the
  // prepared fixture is SA1 solar at 0.20x, not the first region alphabetically.
  await expect(
    page.getByRole('heading', { name: /Solar \(utility\) captured 0\.20× of the SA1 average price/ })
  ).toBeVisible();
  await expect(page.getByText('Prepared non-live fixture')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'What each fuel earned in SA1' })).toBeVisible();

  // Governed boundaries must be on the page, not only in documentation.
  await expect(page.getByRole('heading', { name: 'What it cannot tell you' })).toBeVisible();
  // Stated twice by design: once in the purpose card and once in the footer.
  await expect(page.getByText(/no five-minute availability/).first()).toBeVisible();
  await expect(
    page.getByText(/excluding FCAS, loss factors, contracts, and settlement adjustment/).first()
  ).toBeVisible();
  await expect(page.getByText(/MIT licensed/)).toBeVisible();

  await expect(page.getByRole('region', { name: 'Value capture summary' })).toBeVisible();
  await expect(page.getByText('Negative-price exposure')).toBeVisible();
  await expect(page.getByText('Regional time-weighted price')).toBeVisible();

  // A charging battery is a distinct fuel with negative energy and no capture rate.
  await expect(page.getByText('Battery charging')).toBeVisible();
  await expect(page.getByText('Not comparable').first()).toBeVisible();

  // Staleness is stated for the fixture without the live-mode alarm.
  await expect(page.getByText(/as expected for a prepared fixture/)).toBeVisible();
  await expect(page.getByText(/Do not treat these values as current/)).toBeVisible();

  await page.getByRole('combobox', { name: 'Region' }).click();
  await page.getByRole('option', { name: 'VIC1' }).click();
  await expect(page.getByRole('heading', { name: 'What each fuel earned in VIC1' })).toBeVisible();
  await expect(page.getByText('Brown coal')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Source and freshness · VIC1' })).toBeVisible();

  const vicLatest = page.getByRole('row', { name: /VIC1 01 July 2026, 12:25 AEST/ });
  const nswLatest = page.getByRole('row', { name: /NSW1 01 July 2026, 12:25 AEST/ });
  await expect(vicLatest).toHaveAttribute('data-focused', 'true');
  await expect(nswLatest).toHaveAttribute('data-focused', 'false');

  await expect(page.getByRole('heading', { name: 'Underlying five-minute prices' })).toBeVisible();
  // Negative prices remain valid and are rendered with an explicit minus sign.
  await expect(page.getByRole('cell', { name: '−A$5.50/MWh' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Market-wide context' })).toBeVisible();
  await expect(page.getByText(/No regional allocation or directional interpretation/)).toBeVisible();

  const cta = page.getByRole('button', { name: 'Open investigation journal' });
  await cta.focus();
  await cta.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  // Scoped to the dialog: the call-to-action names the same region and interval.
  await expect(page.getByRole('dialog').getByText(/VIC1 at 01 July 2026, 12:25 AEST/)).toBeVisible();
  await expect(page.getByLabel('Decision')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Record investigation' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(cta).toBeFocused();

  const navTrigger = page.getByRole('button', { name: 'Investigate' });
  await navTrigger.focus();
  await navTrigger.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(navTrigger).toBeFocused();
});

test('the light theme survives a reviewer whose operating system prefers dark', async ({ browser }) => {
  // AppKit ships a prefers-color-scheme dark override on :root:not(.light). Without
  // the explicit opt-out this light-only palette rendered as near-black with
  // unreadable text, so the guard is asserted rather than assumed.
  const context = await browser.newContext({ colorScheme: 'dark' });
  const page = await context.newPage();
  await page.goto('/');

  const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  const [r, g, b] = background.match(/\d+(\.\d+)?/g)!.map(Number);
  // Light warm grey, not the dark fallback.
  expect(r).toBeGreaterThan(200);
  expect(g).toBeGreaterThan(200);
  expect(b).toBeGreaterThan(200);
  await expect(page.getByRole('heading', { name: /captured .* of the .* average price/ })).toBeVisible();
  await context.close();
});

test('mobile layout keeps focus controls and journal usable without page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)
  ).toBe(true);
  await expect(page.getByRole('combobox', { name: 'Region' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Investigate' })).toBeVisible();

  await page.getByRole('combobox', { name: 'Region' }).click();
  await page.getByRole('option', { name: 'VIC1' }).click();
  await expect(page.getByRole('row', { name: /VIC1 01 July 2026, 12:25 AEST/ })).toHaveAttribute(
    'data-focused',
    'true'
  );

  await page.getByRole('button', { name: 'Investigate' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByLabel('Decision')).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)
  ).toBe(true);
});
