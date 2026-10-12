import { test, expect, Page } from '@playwright/test';

// Fail any test whose page throws or logs a console error.
function trackErrors(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  return errors;
}

async function noHorizontalScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test('portfolio home loads', async ({ page }) => {
  const errors = trackErrors(page);
  await page.goto('/');
  await expect(page).toHaveTitle(/Ram Shiri/i);
  await noHorizontalScroll(page);
  expect(errors).toEqual([]);
});

test.describe('CV bootcamp', () => {
  test('dashboard lists every topic and the CV skills block', async ({ page }) => {
    const errors = trackErrors(page);
    await page.goto('/cv-bootcamp/');
    await expect(page.locator('.card[href^="#t/"]')).toHaveCount(22);
    await expect(page.locator('.cv-text')).toContainText('Languages: Python, Java, SQL');
    await noHorizontalScroll(page);
    expect(errors).toEqual([]);
  });

  test('every topic page renders without overflow or errors', async ({ page }) => {
    const errors = trackErrors(page);
    await page.goto('/cv-bootcamp/');
    const hrefs = await page.locator('.card[href^="#t/"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')!));
    for (const href of hrefs) {
      await page.goto('/cv-bootcamp/' + href);
      await expect(page.locator('.quiz-choices button').first()).toBeVisible();
      await noHorizontalScroll(page);
    }
    expect(errors).toEqual([]);
  });

  test('finishing a quiz and dropping a skill removes it from the CV block', async ({ page }) => {
    await page.goto('/cv-bootcamp/#t/java');
    for (let i = 0; i < 20; i++) {
      const choice = page.locator('.quiz-choices button:not(:disabled)').first();
      if (!(await choice.count())) break;
      await choice.click();
      await page.locator('.quiz-actions .btn--primary').click();
    }
    await expect(page.locator('.quiz-result .big')).toHaveText(/\d+%/);
    await page.locator('.btn--drop').click();
    await page.goto('/cv-bootcamp/#');
    await expect(page.locator('.cv-text')).toContainText('Languages: Python, SQL');
  });

  test('targets page checklist persists', async ({ page }) => {
    await page.goto('/cv-bootcamp/#targets');
    const first = page.locator('.checklist input').first();
    await first.check();
    await page.reload();
    await expect(page.locator('.checklist input').first()).toBeChecked();
  });
});
