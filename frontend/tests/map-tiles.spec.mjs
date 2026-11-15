import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';

const screenshotDir = path.join(process.cwd(), 'qa', 'redesign');
fs.mkdirSync(screenshotDir, { recursive: true });

test('OpenStreetMap tiles render after navigation and responsive resizing', async ({ page }) => {
  const tileResponses = [];
  const tileFailures = [];
  const runtimeErrors = [];
  let contentSecurityPolicy = null;

  page.on('response', (response) => {
    if (response.url().includes('tile.openstreetmap.org')) {
      tileResponses.push({
        status: response.status(),
        contentType: response.headers()['content-type'],
      });
    }
  });
  page.on('requestfailed', (request) => {
    if (request.url().includes('tile.openstreetmap.org')) {
      tileFailures.push({
        url: request.url(),
        error: request.failure()?.errorText || 'unknown error',
      });
    }
  });
  page.on('pageerror', (error) => runtimeErrors.push(error.message));

  await page.setViewportSize({ width: 1440, height: 900 });
  const documentResponse = await page.goto('http://127.0.0.1:5173/planner', { waitUntil: 'domcontentloaded' });
  expect(documentResponse?.status()).toBe(200);
  contentSecurityPolicy = (await documentResponse?.allHeaders())?.['content-security-policy'] || null;
  await expect(page.getByRole('heading', { name: 'Route planner' })).toBeVisible();
  await page.getByRole('button', { name: 'Load network' }).click();
  await page.getByRole('button', { name: 'Optimize Delivery Route' }).click();
  await expect(page.getByText('Route optimized successfully.', { exact: true })).toBeVisible({ timeout: 60000 });

  const waitForLoadedTiles = async () => {
    let previousState = '';
    let stableReads = 0;
    await expect.poll(async () => {
      const state = await page.locator('.leaflet-container').evaluate((map) => {
        const mapBounds = map.getBoundingClientRect();
        const visibleTiles = Array.from(map.querySelectorAll('img.leaflet-tile')).filter((tile) => {
          const bounds = tile.getBoundingClientRect();
          return bounds.width > 0 && bounds.height > 0
            && bounds.right > mapBounds.left && bounds.left < mapBounds.right
            && bounds.bottom > mapBounds.top && bounds.top < mapBounds.bottom;
        });
        return {
          visible: visibleTiles.length,
          loaded: visibleTiles.filter((tile) => tile.complete && tile.naturalWidth > 0).length,
        };
      });
      const signature = `${state.visible}:${state.loaded}`;
      if (state.visible > 0 && state.loaded === state.visible && signature === previousState) {
        stableReads += 1;
      } else {
        stableReads = 0;
      }
      previousState = signature;
      return stableReads >= 2;
    }, { timeout: 30000, intervals: [100, 200, 300] }).toBe(true);
    return page.locator('.leaflet-container').evaluate((map) => {
      const mapBounds = map.getBoundingClientRect();
      const visibleTiles = Array.from(map.querySelectorAll('img.leaflet-tile')).filter((tile) => {
        const bounds = tile.getBoundingClientRect();
        return bounds.width > 0 && bounds.height > 0
          && bounds.right > mapBounds.left && bounds.left < mapBounds.right
          && bounds.bottom > mapBounds.top && bounds.top < mapBounds.bottom;
      });
      return {
        visible: visibleTiles.length,
        loaded: visibleTiles.filter((tile) => tile.complete && tile.naturalWidth > 0).length,
      };
    });
  };

  await page.getByRole('link', { name: 'Live Map' }).click();
  await expect(page.getByRole('heading', { name: 'Live route map' })).toBeVisible();
  await expect(page.getByText('Active route', { exact: true })).toBeVisible();
  await expect(page.getByText(/road geometry points/)).toBeVisible();
  const desktopLoadedTiles = await waitForLoadedTiles();
  expect(await page.locator('.leaflet-marker-icon').count()).toBeGreaterThan(0);
  expect(await page.locator('.leaflet-overlay-pane path').count()).toBeGreaterThan(0);

  const desktopMap = await page.locator('.leaflet-container').boundingBox();
  expect(desktopMap?.width).toBeGreaterThan(0);
  expect(desktopMap?.height).toBeGreaterThan(0);
  await page.screenshot({ path: path.join(screenshotDir, 'map-live-desktop.png'), fullPage: true });

  await page.getByRole('link', { name: 'Route Planner' }).click();
  await expect(page.getByRole('heading', { name: 'Route planner' })).toBeVisible();
  await page.getByRole('link', { name: 'Live Map' }).click();
  await expect(page.getByText('Active route', { exact: true })).toBeVisible();
  await expect(page.getByText(/road geometry points/)).toBeVisible();
  await waitForLoadedTiles();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  const mobileLoadedTiles = await waitForLoadedTiles();
  const mobileMap = await page.locator('.leaflet-container').boundingBox();
  expect(mobileMap?.width).toBeGreaterThan(0);
  expect(mobileMap?.height).toBeGreaterThan(0);
  await page.screenshot({ path: path.join(screenshotDir, 'map-live-mobile.png'), fullPage: true });

  expect(tileResponses.length).toBeGreaterThan(0);
  expect(tileResponses.every((response) => response.status === 200 && response.contentType?.startsWith('image/'))).toBe(true);
  const nonCancellationFailures = tileFailures.filter(({ error }) => !error.includes('ERR_ABORTED'));
  expect(nonCancellationFailures).toEqual([]);
  expect(runtimeErrors).toEqual([]);
  fs.writeFileSync(path.join(screenshotDir, 'map-tile-results.json'), JSON.stringify({
    documentStatus: documentResponse?.status(),
    contentSecurityPolicy,
    tileResponses,
    tileFailures,
    nonCancellationFailures,
    desktopMap,
    desktopLoadedTiles,
    mobileMap,
    mobileLoadedTiles,
    runtimeErrors,
    screenshots: ['map-live-desktop.png', 'map-live-mobile.png'],
  }, null, 2));
});
