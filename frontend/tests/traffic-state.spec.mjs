import { test, expect } from '@playwright/test';

test('traffic badge stays synchronized and completed deliveries persist after replans and reset', async ({ page }) => {
  const consoleErrors = [];
  const failedRequests = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(error.message));
  page.on('requestfailed', (request) => failedRequests.push(request.url()));

  await page.goto('http://127.0.0.1:5173/planner', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Load network' }).click();
  await page.getByRole('button', { name: /Optimize Delivery Route/i }).click();
  await expect(page.getByText('Route optimized successfully.')).toBeVisible({ timeout: 60000 });

  await page.goto('http://127.0.0.1:5173/traffic', { waitUntil: 'networkidle' });
  const checkboxes = page.locator('input[type="checkbox"]');
  await expect(checkboxes).toHaveCount(3);
  const completedNames = await checkboxes.evaluateAll((elements) =>
    elements.slice(0, 2).map((element) => element.getAttribute('aria-label')),
  );
  await checkboxes.nth(0).check();
  await checkboxes.nth(1).check();

  await page.locator('select').selectOption('heavy');
  await page.locator('input[type="number"]').fill('1');
  await page.getByRole('button', { name: /Apply Traffic Changes & Recalculate Route/i }).click();

  await expect(page.getByText('Simulated · heavy traffic')).toBeVisible();
  await expect(page.getByText('Replanned route comparison')).toBeVisible();
  await expect(page.getByText('Previous route', { exact: true })).toBeVisible();
  await expect(page.getByText('Updated route', { exact: true })).toBeVisible();
  await expect(page.getByText('2 completed deliveries excluded')).toBeVisible();
  for (const name of completedNames) {
    const checkbox = page.getByRole('checkbox', { name });
    await expect(checkbox).toBeChecked();
    await expect(checkbox).toBeDisabled();
    await expect(checkbox.locator('..')).toContainText('Completed');
  }
  await page.screenshot({ path: 'qa/audit/traffic-heavy-completed.png', fullPage: true });

  await page.getByRole('button', { name: /Reset/i }).click();
  await expect(page.getByText('Simulated · normal traffic')).toBeVisible();
  for (const name of completedNames) {
    await expect(page.getByRole('checkbox', { name })).toBeChecked();
    await expect(page.getByRole('checkbox', { name })).toBeDisabled();
  }

  await page.reload({ waitUntil: 'networkidle' });
  await expect(page.getByText('Simulated · normal traffic')).toBeVisible();
  for (const name of completedNames) {
    await expect(page.getByRole('checkbox', { name })).toBeChecked();
    await expect(page.getByRole('checkbox', { name })).toBeDisabled();
  }

  await page.goto('http://127.0.0.1:5173/analytics', { waitUntil: 'networkidle' });
  await expect(page.getByText('Stored route scenarios')).toBeVisible();
  await expect(page.getByText('Original complete route')).toBeVisible();
  await expect(page.getByText('Active remaining route')).toBeVisible();
  await expect(page.getByText('Normal traffic baseline')).toBeVisible();
  await expect(page.getByText('Simulated congestion scenario')).toBeVisible();
  await expect(page.getByText('heavy', { exact: true })).toBeVisible();

  await page.screenshot({ path: 'qa/audit/traffic-state-persistence.png', fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});
