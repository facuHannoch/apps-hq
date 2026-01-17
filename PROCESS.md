This is a document explaining common processes for building applications and systems.

There will be a submodule, which will contain documents, guides and pipelines to streamline the whole app process from idea to launch and marketing. Common documents include
- `ops/`: A directory containing scripts to do tasks like generate and resize icons, launch new agents, etc.
- `guides/`: A directory containing guides or documents explaining certain topics
- `PROCESS.md`: This file. It will act both as a document for explaining the processes, and a guide for how to do certain things, like initializing common libraries like `Jest`.
- `AGENTS.md`: A document containing instructions for agents to follow. This will be the system prompt for each new agent.

Each app will contain:
- `DESIGN.md`: This will explain the application, it's objective, architecture, etc. Contains
  - user flows (behavioral)
  - architecture & tech stack
  - routing / paths
  - data / persistence model
  - invariants
  - test expectations
  - out-of-scope constraints
  This file answers _How does this system behave and why?_
- `UI_DESIGN.md`: aesthetic & interaction constraints. It is declarative, not descriptive. Contains:
  - color scheme (tokens, not prose)
  - typography rules
  - spacing / density philosophy
  - component style constraints
  - interaction patterns (animations, feedback)
  - responsive intent (not breakpoints, but intent)
  - examples of what not to do
  - This file answers:
  - “How should this feel and look, and what must stay consistent?”
  Agents read this before touching UI files.
  
## Project Structure

Each app will have a single repository, where 

```
app/
  apps-hq/ <-- this git submodule
    ...
  web/
    ...
  DESIGN.md
  README.md

```




## Auth sanity check

ssh -T git@github.com



## Set up project

Read `DESIGN.md` and understand what this app needs to have set up. Do not just do everything that is said here (for example, don't set up cloudflare if the website is not going to be deployed on Cloudflare).

### Web

Search on `DESIGN.md` for Project Name (human readable), project-name (for building or identifiers) and URL domain

> This must be done not on root, but where thenextjs application is located, for example `/web`

#### 1. Create Nextjs app

```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```
Would you like to use React Compiler? » No / Yes -> No

#### 2. Setting up linter

??

1. Add script command to `package.json`

`{`
`"script": {`
```json
"lint": "eslint",
```

#### 3. Setting up testing frameworks

Official documentation:
- https://nextjs.org/docs/app/guides/testing/jest
- https://nextjs.org/docs/app/guides/testing/playwright

##### Jest

1. Install packages
```sh
npm install -D jest jest-environment-jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom ts-node @types/jest
```

2. Update `jest.config.ts`

```ts
import type { Config } from 'jest'
import nextJest from 'next/jest.js'
 
const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})
 
const config: Config = {
  collectCoverage: true,
  coverageDirectory: "coverage",
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testPathIgnorePatterns: ['/node_modules/', '/e2e/'],
}
 
export default createJestConfig(config)
```

3. Create `jest.setup.ts`

```ts
import '@testing-library/jest-dom'
```

4. Add scripts to `package.json`

`{`
`"script": {`
```json
"test": "jest",
"test:watch": "jest --watch"
```

5. Create directory at root: `/__tests__`

6. Create initial tests

For each page, create a simple test that ensures that page is rendered correctly.

For example, for the `/` page. You would create a `__tests__/page.test.tsx` with the following contents:

```ts
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import Page from '../app/page'

test('Renders page', () => {
  render(<Page />)
  expect(true).toBe(true)
})
```

7. Run test, ensure it passes

---

##### Playwright

1. Install package
```bash
npm install -D @playwright/test
```

2. Update `playwright.config.ts`
```ts
import { defineConfig, devices } from '@playwright/test';

// import dotenv from 'dotenv';
// import path from 'path';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

const portRange = { min: 10000, max: 30000 };
const PORT = process.env.CI
  ? Math.floor(Math.random() * (portRange.max - portRange.min) + portRange.min)
  : 8088;

const BASE_URL = `http://localhost:${PORT}`

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('')`. */
    baseURL: BASE_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: `set PORT=${PORT} && npm run dev`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});

```

3. Install brosers
```bash
npx playwright install
```

4. Add scripts to `package.json`

`{`
`"script": {`
```json
"test:e2e": "npx playwright test",
"test:e2e:ui": "npx playwright test --ui",
"test:e2e:debug": "npx playwright test --debug"
```

5. Create a basic test `e2e/basic.spec.ts`

```ts
import { test, expect } from '@playwright/test'

test('homepage loads', async ({ page }) => {
    await page.goto('/')  // Uses baseURL automatically
    expect(page).toBeDefined()
})
```

6. Run test, ensure it passes


#### 4. Deployment

##### Cloudflare Pages deployment

> awd

> wrangler (Cloudflare's CLI tool) should be installed and authenticated
```bash
npm install -g wrangler
```

1. Create a `wrangler.toml` file

```toml
name = ""
compatibility_flags = ["nodejs_compat"]
compatibility_date = "2026-01-04"
pages_build_output_dir = ".vercel/output/static"
```

2. Add deployment scripts to `package.json`

```json
    "pages:build": "wsl npx @cloudflare/next-on-pages",
    "pages:deploy": "npm run pages:build && npx wrangler pages deploy .vercel/output/static --project-name=PROJECT_NAME",
    "pages:dev": "wsl npx @cloudflare/next-on-pages --watch"
```


#### 5. Stage changes

1. Stage changes
2. git commit -m "Initialized Nextjs webapp with <things installed>"
