---
name: typescript-basics
description: Use when writing, building, or reviewing TypeScript on an
  authorized engineering task. Covers strict tsconfig setup, type and
  interface modeling, unions and narrowing, generics, async and await
  patterns, DOM-free Node.js scripting, npm scripts, ESLint checks, and
  compiling to clean JavaScript. Use when starting a TypeScript CLI,
  automation script, or Node.js service, or when reviewing TypeScript for
  type safety gaps.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, code-reviewer]
tools:
  - name: TypeScript
    version: 5.6
  - name: Node.js
    version: 22
---

TypeScript is JavaScript with a type system that catches mistakes at
compile time instead of in production. This skill covers the working
basics: a strict configuration, modeling data with types and
interfaces, narrowing unions safely, generics, async patterns, and the
npm and ESLint workflow that keeps a project healthy. All examples
target TypeScript 5.6 on Node.js 22.

## Quick Workflow

1. Scaffold with `npm init` and install TypeScript locally, never
   globally for project work.
2. Create a strict `tsconfig.json` and keep `strict` on for the whole
   project.
3. Model data with `interface` and `type`; prefer `unknown` over
   `any` for anything from outside.
4. Narrow unions with type guards instead of casting.
5. Use `async`/`await` with `try`/`catch`; never leave a promise
   floating without handling rejection.
6. Define `npm` scripts for build, typecheck, lint, and test.
7. Run `tsc --noEmit`, ESLint, and tests before every commit.
8. Compile with `tsc` and ship the emitted JavaScript, not the
   TypeScript source.

## 1. Project setup and strict config

```bash
node --version
npm --version

mkdir ts-tool && cd ts-tool
npm init -y
npm install --save-dev typescript@5.6
npx tsc --version
```

```bash
cat > tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"]
}
EOF

mkdir -p src
cat > src/index.ts <<'EOF'
console.log("hello from TypeScript");
EOF

npx tsc
node dist/index.js
```

`strict: true` enables the checks that matter (no implicit any, strict
null checks). `noUncheckedIndexedAccess` makes `arr[i]` possibly
`undefined`, which kills a whole class of off-by-one crashes.

## 2. Interfaces, types, and unions

```typescript
// src/scan.ts
interface ScanTarget {
  host: string;
  ports: number[];
  timeoutMs?: number; // optional field
}

type ScanStatus = "open" | "closed" | "filtered"; // union of literals

interface ScanResult {
  host: string;
  port: number;
  status: ScanStatus;
}

export function summarize(results: ScanResult[]): string {
  const open = results.filter((r) => r.status === "open").length;
  return `${open}/${results.length} ports open`;
}
```

Use `interface` for object shapes that may be extended, `type` for
unions and aliases. Literal unions like `ScanStatus` restrict a field
to exactly the allowed values, which the compiler checks everywhere.

## 3. Narrowing instead of casting

```typescript
function parsePort(raw: unknown): number | null {
  // unknown forces you to check before use: any would not
  if (typeof raw === "number" && Number.isInteger(raw) && raw >= 1 && raw <= 65535) {
    return raw;
  }
  if (typeof raw === "string" && /^\d+$/.test(raw)) {
    const n = Number(raw);
    if (n >= 1 && n <= 65535) return n;
  }
  return null;
}

// Discriminated union: the "kind" field tells the compiler which shape it is
type ApiResponse =
  | { kind: "ok"; data: ScanResult[] }
  | { kind: "error"; message: string };

function handle(resp: ApiResponse): void {
  if (resp.kind === "ok") {
    console.log("results:", resp.data.length); // data is known here
  } else {
    console.error("failed:", resp.message); // message is known here
  }
}
```

Narrowing with `typeof`, `in`, and discriminant fields keeps the
compiler as the proof that every branch is handled. Reach for `as`
casts only when you know more than the compiler, and treat each one
as a place a runtime crash can hide.

## 4. Generics for reusable code

```typescript
function first<T>(items: T[]): T | undefined {
  return items[0];
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return (await res.json()) as T;
}

// Usage keeps full type information, no casts at the call site
const page = await fetchJson<Paginated<ScanResult>>("https://api.example/scans");
console.log(page.items.length, "of", page.total);
```

Generics preserve types through reusable helpers. Bound them when the
code needs a capability (`<T extends { id: string }>`) so misuse fails
at compile time.

## 5. Async patterns done right

```typescript
import { Socket } from "node:net";

function checkPort(host: string, port: number, timeoutMs = 2000): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new Socket();
    const done = (result: boolean): void => {
      socket.destroy();
      resolve(result);
    };
    socket.setTimeout(timeoutMs);
    socket.on("connect", () => done(true));
    socket.on("timeout", () => done(false));
    socket.on("error", () => done(false));
    socket.connect(port, host);
  });
}
```

A cleaner, dependency-free concurrency pattern with a pool limit:

```typescript
async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (item: T) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  async function worker(): Promise<void> {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

// Scan 50 ports with at most 10 in flight
const ports = Array.from({ length: 50 }, (_, i) => 8000 + i);
const open = await mapLimit(ports, 10, async (p) => ({ port: p, ok: await probe(p) }));
console.log(open.filter((r) => r.ok).map((r) => r.port));
```

Always `await` promises or attach `.catch()`; an unhandled rejection
crashes modern Node.js. Use `Promise.allSettled` when one failure must
not cancel the rest.

## 6. npm scripts and project workflow

```bash
cat > package.json <<'EOF'
{
  "name": "ts-tool",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src --max-warnings 0",
    "test": "node --test dist/test/*.test.js",
    "start": "node dist/index.js"
  }
}
EOF

npm pkg set scripts.dev="tsx src/index.ts" 2>/dev/null || true
npm run typecheck
npm run build
```

Scripts are the project's control panel: one command per job, same
commands locally and in CI.

## 7. ESLint and tests

```bash
npm install --save-dev eslint @eslint/js typescript-eslint
cat > eslint.config.mjs <<'EOF'
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-floating-promises": "error",
      "no-console": "off"
    }
  }
);
EOF

npx eslint src --max-warnings 0
```

```bash
# Node's built-in test runner needs no framework for unit tests
mkdir -p src/test
cat > src/test/ports.test.ts <<'EOF'
import test from "node:test";
import assert from "node:assert/strict";
import { parsePort } from "../ports.js";

test("parsePort accepts valid numbers", () => {
  assert.equal(parsePort(443), 443);
  assert.equal(parsePort("8080"), 8080);
});

test("parsePort rejects garbage", () => {
  assert.equal(parsePort(0), null);
  assert.equal(parsePort("abc"), null);
  assert.equal(parsePort(null), null);
});
EOF

npm run build && npm test
```

`no-floating-promises` is the lint rule that pays for itself: it flags
every promise you forgot to await or catch.

## Edge cases

- `tsc` reports hundreds of errors after enabling `strict` on an
  existing project. Fix file by file with `// @ts-nocheck` as a
  temporary marker on unmigrated files, and remove markers as you
  convert them. Never ship with the markers.
- `moduleResolution` mismatch causes "cannot find module" for
  perfectly valid imports. Keep `module` and `moduleResolution`
  paired (`NodeNext` with `NodeNext`); mixing `CommonJS` with
  `Bundler` resolution breaks ESM imports.
- Third-party library has no types. Install `@types/<pkg>` first;
  only write a local `.d.ts` declaration when no types package
  exists, and keep it minimal.
- `fetch` in Node 22 works, but old tutorials use `node-fetch`.
  Prefer the built-in `fetch` and `AbortController` for timeouts;
  fewer dependencies is fewer supply-chain risks.
- Tests import from `../ports.js` with a `.js` extension even though
  the file is `.ts`. This is correct under `NodeNext`: TypeScript
  rewrites the extension at compile time.
- `npm install` is slow or flaky in CI. Commit `package-lock.json`,
  use `npm ci` instead of `npm install` in CI, and cache
  `~/.npm` between runs.
- Enum vs union debate. Prefer string literal unions over `enum`
  for new code: they are simpler, tree-shake better, and serialize
  to JSON without surprises.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. TypeScript misconfiguration shows up as `strict:
false` in shipped projects, `any` types on data from the network,
and `// @ts-ignore` comments hiding real errors in security paths.
Detect it by running `tsc --noEmit` and ESLint in CI and failing the
build on any error. Prototype pollution (`obj[key] = value` with
attacker-controlled keys) and `eval` on user input survive
compilation untouched, so audit dynamic property access and code
generation calls regardless of types. A `node_modules` directory
with thousands of packages for a small tool is a supply-chain
surface: run `npm audit`, pin versions with the lockfile, and review
`npm diff` output on dependency updates.

## Key references

- TypeScript 5.6 documentation: https://www.typescriptlang.org/docs/
- tsconfig reference: https://www.typescriptlang.org/tsconfig/
- Node.js 22 documentation: https://nodejs.org/docs/latest-v22.x/api/
- typescript-eslint: https://typescript-eslint.io/
- npm CLI docs: https://docs.npmjs.com/cli/
- CWE-20 (Improper Input Validation): validate with `unknown`
  narrowing before use.
- CWE-95 (Improper Neutralization of Directives in Dynamically
  Evaluated Code): `eval` and `new Function` on untrusted input.
- CWE-1321 (Improperly Controlled Modification of Object Prototype
  Attributes): prototype pollution in dynamic property writes.
