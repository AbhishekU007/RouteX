import fs from 'fs';
import path from 'path';
import { test, expect } from '@playwright/test';

const screenshotDir = path.join(process.cwd(), 'qa', 'screenshots');
fs.mkdirSync(screenshotDir, { recursive: true });

test('RouteX end-to-end browser QA', async ({ page }) => {
  const consoleErrors = [];
  const failedNetwork = [];

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });

  page.on('pageerror', (error) => {
    consoleErrors.push(error.message);
  });

  page.on('requestfailed', (request) => {
    const errorText = request.failure()?.errorText || 'unknown error';
    if (errorText !== 'net::ERR_ABORTED') {
      failedNetwork.push(`${request.url()} :: ${errorText}`);
    }
  });

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await expect(page.getByRole('heading', { name: 'Operations overview' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'overview.png'), fullPage: true });

  await page.getByRole('link', { name: 'Route Planner' }).click();
  await expect(page.getByRole('heading', { name: 'Route planner' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'planner.png'), fullPage: true });

  await page.getByRole('button', { name: 'Load network' }).click();
  await page.getByRole('button', { name: /Optimize Delivery Route/i }).click();
  await expect(page.getByText('Route optimized successfully.', { exact: true })).toBeVisible({ timeout: 60000 });
  await page.screenshot({ path: path.join(screenshotDir, 'planner-result.png'), fullPage: true });

  await page.getByRole('link', { name: 'Live Map' }).click();
  await expect(page.getByRole('heading', { name: 'Live route map' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'map.png'), fullPage: true });

  await page.getByRole('link', { name: 'Traffic Simulator' }).click();
  await expect(page.getByRole('heading', { name: 'Traffic simulator' })).toBeVisible();
  await page.locator('select').first().selectOption('heavy');
  await page.getByRole('button', { name: /Apply Traffic Changes & Recalculate Route/i }).click();
  await expect(page.getByRole('main').getByText('heavy', { exact: true })).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: path.join(screenshotDir, 'traffic.png'), fullPage: true });

  await page.getByRole('link', { name: 'Analytics' }).click();
  await expect(page.getByRole('heading', { name: 'Analytics' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'analytics.png'), fullPage: true });

  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotDir, 'settings.png'), fullPage: true });

  const summary = {
    consoleErrors,
    failedNetwork,
    screenshots: fs.readdirSync(screenshotDir).sort(),
  };
  fs.writeFileSync(path.join(process.cwd(), 'qa', 'browser-qa-results.json'), JSON.stringify(summary, null, 2));

  expect(consoleErrors).toEqual([]);
  expect(failedNetwork).toEqual([]);
});
