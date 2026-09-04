---
name: playwright
description: Browser automation, end-to-end testing, test generation, and web scraping using Playwright. Two modes: (1) playwright-cli — live interactive browser control with snapshot-based element refs, Plan→Generate→Heal test authoring workflow; (2) @playwright/test — E2E test file writing, page object model, CI integration. Use for: "automate browser", "test this page", "write e2e tests", "take a screenshot", "fill this form", "debug a test", "generate tests", "scrape a page", "visual regression", "mock network requests".
allowed-tools: Bash(playwright-cli:*) Bash(npx:*) Bash(npm:*)
---

# Playwright — Browser Automation & Testing

Two complementary tools. Start with `playwright-cli` for live exploration and test generation; use `@playwright/test` for test file structure and CI.

## Installation

```bash
# playwright-cli (live browser control)
npm install -g @playwright/cli@latest
# or use locally without installing:
npx playwright cli <command>

# @playwright/test (test framework)
npm init playwright@latest
# or add to existing project:
npm install -D @playwright/test && npx playwright install
```

---

## Mode 1: playwright-cli (Live Browser Automation)

Interactive CLI that opens a real browser, takes accessibility snapshots with element refs (`e1`, `e2`, …), and generates Playwright TypeScript from every action.

### Quick Start

```bash
playwright-cli open https://example.com
playwright-cli snapshot          # see element refs
playwright-cli click e5
playwright-cli fill e3 "hello" --submit
playwright-cli screenshot
playwright-cli close
```

### Core Commands

```bash
# Navigation
playwright-cli open https://example.com
playwright-cli goto https://other.com
playwright-cli go-back / go-forward / reload

# Interactions (use refs from snapshot)
playwright-cli click e15
playwright-cli dblclick e7
playwright-cli fill e5 "user@example.com" --submit
playwright-cli type "search query"
playwright-cli press Enter / ArrowDown
playwright-cli hover e4
playwright-cli select e9 "option-value"
playwright-cli check e12 / uncheck e12
playwright-cli drag e2 e8
playwright-cli upload ./document.pdf
playwright-cli drop e4 --path=./image.png

# Snapshot & Search
playwright-cli snapshot
playwright-cli snapshot "#main"       # scope to element
playwright-cli snapshot --depth=4     # limit depth
playwright-cli find "Sign in"
playwright-cli find --regex "/sign (in|up)/i"

# Eval
playwright-cli eval "document.title"
playwright-cli eval "el => el.textContent" e5
playwright-cli eval "el => el.getAttribute('data-testid')" e5

# Dialogs
playwright-cli dialog-accept / dialog-dismiss

# Save
playwright-cli screenshot --filename=page.png --hires
playwright-cli pdf --filename=page.pdf
playwright-cli screenshot e5          # element screenshot
```

### Keyboard & Mouse

```bash
playwright-cli keydown Shift / keyup Shift
playwright-cli mousemove 150 300
playwright-cli mousedown / mouseup
playwright-cli mousewheel 0 100
```

### Tabs

```bash
playwright-cli tab-new https://example.com/other
playwright-cli tab-list / tab-select 0 / tab-close 2
```

### Storage

```bash
# Session state
playwright-cli state-save auth.json
playwright-cli state-load auth.json

# Cookies
playwright-cli cookie-list / cookie-get session_id
playwright-cli cookie-set session_id abc123 --httpOnly --secure
playwright-cli cookie-delete session_id / cookie-clear

# LocalStorage / SessionStorage
playwright-cli localstorage-set theme dark
playwright-cli localstorage-get theme
playwright-cli localstorage-clear
playwright-cli sessionstorage-set step 3
```

### Network

```bash
playwright-cli route "**/*.jpg" --status=404
playwright-cli route "https://api.example.com/**" --body='{"mock": true}'
playwright-cli route-list / unroute "**/*.jpg"
```

### DevTools

```bash
playwright-cli console / console warning
playwright-cli requests / request 5
playwright-cli tracing-start / tracing-stop
playwright-cli video-start video.webm
playwright-cli video-chapter "Login" --duration=2000
playwright-cli video-stop
playwright-cli run-code "async page => await page.context().grantPermissions(['geolocation'])"
```

### Browser Sessions

```bash
# Named sessions for isolation
playwright-cli -s=auth open https://app.com/login
playwright-cli -s=guest open https://app.com
playwright-cli -s=auth fill e1 "user@example.com"
playwright-cli -s=guest snapshot

playwright-cli list           # list all sessions
playwright-cli close-all      # stop all
playwright-cli kill-all       # force-kill zombie processes
```

### Open Options

```bash
playwright-cli open --browser=firefox / --browser=webkit / --browser=msedge
playwright-cli open --mobile / --device="iPhone 15"
playwright-cli open --persistent / --profile=/path/to/profile
playwright-cli attach --cdp=chrome    # attach to running Chrome
playwright-cli attach --extension     # attach via Playwright extension
```

### Raw / JSON Output

```bash
playwright-cli --raw eval "document.title"   # strip status/snapshot sections
playwright-cli --raw snapshot > before.yml
playwright-cli --json list                   # structured JSON output
TOKEN=$(playwright-cli --raw cookie-get session_id)
```

### UI Review Mode

```bash
# Opens live browser for user annotation — returns annotated screenshot + notes
playwright-cli open https://example.com
playwright-cli show --annotate
```

### Locator Generation

```bash
playwright-cli generate-locator e5 --raw   # → getByRole('button', { name: 'Submit' })
playwright-cli highlight e5                 # persistent element highlight overlay
playwright-cli highlight --hide             # hide all highlights
```

---

## Mode 2: @playwright/test (Test Files)

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('logs in with valid credentials', async ({ page }) => {
    await page.fill('[name="email"]', 'user@example.com');
    await page.fill('[name="password"]', 'pass123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });
});
```

### Page Object Model

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}
  async goto() { await this.page.goto('/login'); }
  async login(email: string, password: string) {
    await this.page.fill('[name="email"]', email);
    await this.page.fill('[name="password"]', password);
    await this.page.click('button[type="submit"]');
  }
}
```

### playwright.config.ts

```typescript
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### CI (GitHub Actions)

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps chromium
- name: Run tests
  run: npx playwright test
- uses: actions/upload-artifact@v4
  if: failure()
  with: { name: playwright-report, path: playwright-report/ }
```

---

## Plan → Generate → Heal Workflow

Full test authoring workflow using `playwright-cli` + `@playwright/test` together.

**Plan**: Explore the app with `playwright-cli`, write a spec file (`specs/<feature>.plan.md`) enumerating scenarios.

**Generate**: For each scenario, launch `npx playwright test <seed> --debug=cli`, attach with `playwright-cli attach tw-XXXX`, walk the steps, collect generated TypeScript, write the test file.

**Heal**: Run tests, debug failures with `--debug=cli`, fix locators, reconcile spec with reality.

See `references/test-generation.md` for the full workflow.

---

## Reference Map (Lazy Load)

| Scope | Reference |
|---|---|
| Running and debugging `@playwright/test` with `--debug=cli` | `references/playwright-tests.md` |
| Network request mocking and interception | `references/request-mocking.md` |
| Running arbitrary JS/TS in the browser context | `references/running-code.md` |
| Named browser sessions, attach/detach, CDP | `references/session-management.md` |
| Cookies, localStorage, sessionStorage, state files | `references/storage-state.md` |
| Plan → Generate → Heal test authoring workflow | `references/test-generation.md` |
| Playwright trace viewer and trace files | `references/tracing.md` |
| Video recording with chapters and action callouts | `references/video-recording.md` |
| Reading element attributes, IDs, data-* via eval | `references/element-attributes.md` |

---

## Byblos CRM Test Priorities

1. Login and session management flows
2. Customer CRUD operations
3. Contract creation and status transitions
4. Intervention report generation and PDF export
5. Role-based access control (manager vs. technician views)
6. RTL layout correctness for Arabic interface
