---
name: webapp-assessment
kind: playbook
description: Use when you need a deep security assessment of a web application and its APIs, from threat modeling through manual and automated testing to remediation-ready findings. Covers auth and session flaws, injection classes, file handling, API and GraphQL issues, and business logic abuse. Load this playbook when a client gives you test credentials and in-scope URLs and you need task order, owners, skills, brains, and decision gates for a complete web and API assessment.
version: 1.0.0
---

# Web Application Assessment Playbook

Authorized work only. Test only the URLs, APIs, and accounts named in the rules of engagement. Never attack production data, other tenants, or out-of-scope endpoints.

## Objective

Assess the security of a web application and its APIs by mapping the attack surface, testing each vulnerability class with validated proof, and delivering findings that developers can reproduce and fix. Success is a complete coverage map, zero untested in-scope endpoints, and findings with working reproduction steps.

## Phase table

| phase | owner agent | skills used | brains used | decision gates | exit criteria |
|-------|-------------|-------------|-------------|----------------|---------------|
| 1. Scope and threat model | api-security-agent | api-security-testing, webapp-pentest-methodology, technical-writing | threat-modeling, cost-of-attack | GO_NO_GO_GATES | App map, trust boundaries, test accounts, agreed windows |
| 2. Recon and mapping | recon-agent | recon-passive, recon-active, webapp-pentest-methodology, graphql-security, websocket-security | attacker-mindset, hypothesis-driven-testing | GO_NO_GO_GATES | Full endpoint and parameter inventory, auth flows documented |
| 3. Authentication and session testing | web-exploitation-agent | auth-attacks, jwt-attacks, oauth-attacks, password-attacks, open-redirect | hypothesis-driven-testing, root-cause-analysis | RISK_MATRIX | All auth flows tested, session handling validated |
| 4. Injection and data handling | web-exploitation-agent | web-sqli, web-xss, nosql-injection, xxe, ssti, lfi-rfi, file-upload-attacks, ssrf | hypothesis-driven-testing, evidence-chain | RISK_MATRIX | Every injection class tested per input vector, findings validated |
| 5. API and business logic | api-security-agent | api-security-testing, jwt-attacks, graphql-security, rest-api-design, csrf, cors-misconfig, cache-poisoning, http-request-smuggling | root-cause-analysis, attacker-mindset | ESCALATION_POLICY | All API endpoints tested for authorization and logic flaws |
| 6. Reporting and retest | pentest-reporter-agent | technical-writing, testing-strategies | evidence-chain, root-cause-analysis | COST_BENEFIT | Developer-ready report with reproduction steps, retest window set |

## Detailed phases

### Phase 1. Scope and threat model

Steps:
1. Collect in-scope URLs, API base paths, test credentials, and the data classification of the application.
2. Draw the trust boundary map: user input, authentication service, backend APIs, third-party integrations, storage.
3. List the crown jewels: what data or function would hurt most if compromised. Rank test priority by this.
4. Confirm the test window, rate limits, and the client's definition of a stop condition (for example, account lockout thresholds).

Evidence to collect: scope document, trust boundary diagram, asset priority list, test credentials vault entry, rate limit agreement.

### Phase 2. Recon and mapping

Steps:
1. Spider the application as an unauthenticated user, then repeat as each test role.
2. Inventory every endpoint, parameter, header, and WebSocket or GraphQL operation. Mark which require authentication.
3. Document authentication flows: login, password reset, MFA, OAuth grants, token refresh, logout.
4. Identify technology stack, WAF presence, and rate limiting behavior from responses.

Commands (where relevant):
```bash
mkdir -p ~/engagements/<client>/webapp/map
# store spider output, then build endpoints.md: method, path, auth required, parameters
```

Evidence to collect: spider archives, endpoint inventory with auth requirements, auth flow diagrams, stack fingerprint notes.

### Phase 3. Authentication and session testing

Steps:
1. Test credential handling: lockout, password reset poisoning, username enumeration, MFA bypass attempts within the risk matrix.
2. Test session management: token randomness, fixation, timeout, concurrent session control, logout effectiveness.
3. Test JWT and OAuth flows: algorithm confusion, none algorithm, weak secrets, redirect URI validation, scope tampering.
4. Test open redirects only where they chain into credential theft, and only within approved impact.

Evidence to collect: auth test matrix (flow, test, result), token samples with weak points highlighted, session test logs.

### Phase 4. Injection and data handling

Steps:
1. Test SQL injection per parameter with time-based and boolean payloads. Confirm with database version or sleep responses, never with data dumps.
2. Test stored, reflected, and DOM XSS with unique canary strings. Prove execution context, not just reflection.
3. Test NoSQL injection, XXE, SSTI, and LFI or RFI where the stack suggests them. Use out-of-band or local file reads that stay in scope.
4. Test file upload: extension bypass, content type confusion, and where the file lands. Test SSRF with internal metadata endpoints blocked by the risk matrix unless explicitly approved.

Commands (where relevant):
```bash
# canary-based validation example pattern
curl -s -b session=<token> "<url>?q=<canary>" | grep -c "<canary>"
```

Evidence to collect: request and response pairs per finding, canary proof, payload logs, false-positive notes.

### Phase 5. API and business logic

Steps:
1. Test broken object level authorization: swap IDs across users and roles for every endpoint that takes an object reference.
2. Test mass assignment, excessive data exposure, and rate limit or quota bypass.
3. Test GraphQL introspection, nested query depth, and batching abuse.
4. Test business logic: price or quantity tampering, workflow step skipping, race conditions on limited resources, with safe single-account tests first.

Evidence to collect: authorization test matrix, business logic test cases with expected versus actual behavior, rate limit observations.

### Phase 6. Reporting and retest

Steps:
1. Write each finding with title, severity, affected endpoint, reproduction steps, request and response proof, impact, and fix guidance.
2. Group findings by root cause so one fix can close a class of issues.
3. Deliver the draft, hold the developer walkthrough, then finalize.
4. Schedule the retest and define what counts as fixed (code deployed, config changed, retest passes).

Evidence to collect: draft and final report, walkthrough notes, retest checklist, client sign-off.

## Decision gates

- **GO_NO_GO_GATES** (decisions/GO_NO_GO_GATES.md): must pass before Phase 1 and Phase 2. Checks: written authorization, in-scope URL list, test accounts working, test window agreed, production safety rules confirmed. Missing any item blocks testing.
- **RISK_MATRIX** (decisions/RISK_MATRIX.md): used in Phases 3 and 4. Payloads are scored before sending. Anything that risks data corruption, lockout of real users, or service disruption needs explicit written approval.
- **ESCALATION_POLICY** (decisions/ESCALATION_POLICY.md): used in Phase 5. Business logic tests that touch money, inventory, or other users data stop and escalate for written approval before proceeding.
- **COST_BENEFIT** (decisions/COST_BENEFIT.md): used in Phase 6. Findings are ordered by fix cost versus risk reduction so the development team patches the highest-value items first.

## Deliverables

1. Scope document and threat model with trust boundaries.
2. Endpoint and parameter inventory with authentication requirements.
3. Auth, injection, API, and business logic test matrices.
4. Validated findings with reproduction steps and proof pairs.
5. Developer-ready report with severity, impact, and remediation guidance.
6. Retest checklist and schedule.
