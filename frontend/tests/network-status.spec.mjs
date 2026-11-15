import { test, expect } from '@playwright/test';

test('planner reports the loaded network and prevents optimizing a different city', async ({ page }) => {
  let optimizationRequests = 0;
  page.on('request', (request) => {
    if (request.url().endsWith('/api/routes/optimize') && request.method() === 'POST') {
      optimizationRequests += 1;
    }
  });

  await page.goto('http://127.0.0.1:5173/planner', { waitUntil: 'networkidle' });
  const cityInput = page.getByPlaceholder('Operating city');
  await page.getByRole('button', { name: 'Load network' }).click();
  await expect(page.getByRole('status')).toContainText('Loaded offline fallback network for Agra');
  await expect(page.getByRole('status')).toContainText('16 nodes');
  await expect(page.getByRole('status')).toContainText('48 road segments');

  await cityInput.fill('Delhi, India');
  await page.getByRole('button', { name: 'Optimize Delivery Route' }).click();
  await expect(page.getByRole('alert')).toContainText(
    'Load the road network for the selected city before optimizing.',
  );
  expect(optimizationRequests).toBe(0);

  await page.getByRole('button', { name: 'Load network' }).click();
  await expect(
    page.getByRole('alert').filter({
      hasText: 'The offline fallback network is available only for Agra, Uttar Pradesh, India.',
    }),
  ).toBeVisible();
});
