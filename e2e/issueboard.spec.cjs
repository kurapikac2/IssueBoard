const { test, expect } = require('@playwright/test');

test.use({
  baseURL: 'http://127.0.0.1:8000',
  viewport: { width: 1440, height: 900 },
});

test('a user can register, manage an issue and use mobile layout', async ({ page }, testInfo) => {
  const username = 'portfolio_' + Date.now().toString(36);
  const password = 'example-local-password-123';

  await page.goto('/');
  await expect(page.locator('#auth-view')).toBeVisible();

  await page.locator('#auth-switch').click();
  await expect(page.locator('#auth-heading')).toHaveText('Создать аккаунт');
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#auth-submit').click();

  await expect(page.locator('#auth-heading')).toHaveText('Войти в IssueBoard');
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#auth-submit').click();
  await expect(page.locator('#board-view')).toBeVisible();

  await page.locator('#first-project').click();
  await page.locator('#new-project-name').fill('Portfolio website');
  await page.locator('#new-project-description').fill('Disposable browser test project');
  await page.locator('#project-form [type="submit"]').click();
  await expect(page.locator('#project-name')).toHaveText('Portfolio website');

  await page.locator('#add-issue').click();
  await page.locator('#issue-title').fill('Fix mobile navigation');
  await page.locator('#issue-description').fill('Check that navigation works on narrow screens');
  await page.locator('#issue-priority').selectOption('high');
  await page.locator('#issue-form [type="submit"]').click();

  await expect(page.locator('#issues-list .issue-title')).toHaveText('Fix mobile navigation');
  await expect(page.locator('#metric-total')).toHaveText('1');
  await expect(page.locator('#metric-open')).toHaveText('1');

  // Regression: the "open" filter must be an actual HTML option.
  await page.locator('#filter-status').selectOption('open');
  await page.locator('#filter-priority').selectOption('high');
  await page.locator('#search').fill('mobile');
  await expect(page.locator('#results-count')).toHaveText('Найдено: 1');
  await expect(page.locator('#issues-list .issue-title')).toHaveText('Fix mobile navigation');
  await page.locator('#search').fill('');
  await page.locator('#filter-status').selectOption('');
  await page.locator('#filter-priority').selectOption('');

  await page.locator('#issues-list .issue-title').click();
  await page.locator('#issue-status').selectOption('done');
  await page.locator('#issue-form [type="submit"]').click();
  await expect(page.locator('#metric-done')).toHaveText('1');
  await expect(page.locator('#metric-open')).toHaveText('0');

  await page.locator('#issues-list .issue-title').click();
  await expect(page.locator('#history li')).toHaveCount(2);
  await page.locator('#issue-dialog .close-dialog').first().click();

  // Capture the settled interface after the actual notification dismisses itself.
  await expect(page.locator('#notice')).toBeHidden({ timeout: 7000 });
  await page.screenshot({ path: testInfo.outputPath('issueboard-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#project-name')).toBeVisible();
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
  );
  expect(horizontalOverflow, 'Page should not overflow horizontally on mobile').toBe(false);
  await page.screenshot({ path: testInfo.outputPath('issueboard-mobile.png'), fullPage: true });

  await page.locator('#logout').click();
  await expect(page.locator('#auth-view')).toBeVisible();
});
