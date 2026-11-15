import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';

const viewports = [
  { name: '1920x1080', width: 1920, height: 1080 },
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1024x768', width: 1024, height: 768 },
  { name: '390x844', width: 390, height: 844 },
];

const pages = [
  { path: '/', heading: 'Operations overview', name: 'overview' },
  { path: '/planner', heading: 'Route planner', name: 'planner' },
  { path: '/map', heading: 'Live route map', name: 'map' },
  { path: '/traffic', heading: 'Traffic simulator', name: 'traffic' },
  { path: '/analytics', heading: 'Analytics', name: 'analytics' },
  { path: '/settings', heading: 'Settings', name: 'settings' },
];

const screenshotDir = path.join(process.cwd(), 'qa', 'redesign');
fs.mkdirSync(screenshotDir, { recursive: true });

test('all pages render without horizontal overflow at supported viewports', async ({ page }) => {
  const runtimeErrors = [];
  page.on('pageerror', (error) => runtimeErrors.push(error.message));

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    for (const route of pages) {
      await page.goto(`http://127.0.0.1:5173${route.path}`, { waitUntil: 'domcontentloaded' });
      await expect(page.getByRole('heading', { name: route.heading })).toBeVisible();
      if (route.name === 'map') {
        await expect(page.locator('.leaflet-container')).toBeVisible();
      }

      const fitsViewport = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(fitsViewport, `${route.name} overflows at ${viewport.name}`).toBe(true);

      await page.screenshot({
        path: path.join(screenshotDir, `${viewport.name}-${route.name}.png`),
        fullPage: true,
        animations: 'disabled',
      });
    }
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://127.0.0.1:5173/');
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await expect(page.locator('.app-sidebar')).toHaveClass(/mobile-open/);
  await page.getByRole('link', { name: 'Route Planner' }).click();
  await expect(page.getByRole('heading', { name: 'Route planner' })).toBeVisible();
  await expect(page.locator('.app-sidebar')).not.toHaveClass(/mobile-open/);

  expect(runtimeErrors).toEqual([]);
});
