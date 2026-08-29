---
name: playwright
description: Browser automation, end-to-end testing, and web scraping using Playwright. Use for writing Playwright tests, debugging test failures, setting up Playwright in a project, running tests in CI, page object model design, intercepting network requests, testing auth flows, visual regression testing, PDF generation, and browser automation scripts. Triggers: "playwright", "e2e test", "browser test", "automate browser", "write tests for this page", "test this flow".
---

# Playwright CLI & Testing

## Setup

```bash
# Install
npm init playwright@latest
# or add to existing project
npm install -D @playwright/test

# Install browsers (default: chromium, firefox, webkit)
npx playwright install

# In CCR remote environment — browsers pre-installed at /opt/pw-browsers
# Set executablePath: '/opt/pw-browsers/chromium' — do NOT run playwright install
```

## Core CLI Commands

```bash
# Run all tests
npx playwright test

# Run specific file
npx playwright test tests/login.spec.ts

# Run with UI mode (interactive debugger)
npx playwright test --ui

# Run headed (see browser)
npx playwright test --headed

# Run in specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Debug mode (pauses at each step)
npx playwright test --debug

# Generate tests by recording user actions
npx playwright codegen https://example.com

# Show test report
npx playwright show-report

# Run tests in CI (no interactivity)
npx playwright test --reporter=github

# Update snapshots
npx playwright test --update-snapshots
```

## Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('logs in with valid credentials', async ({ page }) => {
    await page.fill('[name="email"]', 'user@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('shows error on invalid credentials', async ({ page }) => {
    await page.fill('[name="email"]', 'wrong@example.com');
    await page.fill('[name="password"]', 'wrongpass');
    await page.click('button[type="submit"]');
    await expect(page.locator('.error-message')).toBeVisible();
  });
});
```

## Page Object Model

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.page.fill('[name="email"]', email);
    await this.page.fill('[name="password"]', password);
    await this.page.click('button[type="submit"]');
  }

  async errorMessage() {
    return this.page.locator('.error-message');
  }
}

// tests/login.spec.ts
test('logs in', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('user@example.com', 'pass');
  await expect(page).toHaveURL('/dashboard');
});
```

## Common Patterns

**Wait strategies (prefer these over sleep):**
```typescript
await page.waitForURL('/dashboard');
await page.waitForSelector('.loaded');
await expect(locator).toBeVisible({ timeout: 5000 });
await page.waitForLoadState('networkidle');
```

**Network interception:**
```typescript
await page.route('**/api/users', route => {
  route.fulfill({ json: { users: [] } });
});
```

**Authentication — save session state:**
```typescript
// playwright.config.ts
export default { use: { storageState: 'auth.json' } };

// setup/auth.ts (global setup)
await page.goto('/login');
await page.fill('[name="email"]', process.env.TEST_USER!);
await page.fill('[name="password"]', process.env.TEST_PASS!);
await page.click('[type="submit"]');
await page.context().storageState({ path: 'auth.json' });
```

**Screenshot on failure:**
```typescript
// playwright.config.ts
export default { use: { screenshot: 'only-on-failure' } };
```

**PDF generation:**
```typescript
await page.goto('https://example.com');
await page.pdf({ path: 'output.pdf', format: 'A4' });
```

## playwright.config.ts Defaults

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

## CI Integration (GitHub Actions)

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps chromium
- name: Run tests
  run: npx playwright test
- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: playwright-report
    path: playwright-report/
```

## Byblos CRM Test Priorities

1. Login and session management flows
2. Customer CRUD operations
3. Contract creation and status transitions
4. Intervention report generation and PDF export
5. Role-based access control (manager vs. technician views)
6. RTL layout correctness for Arabic interface
