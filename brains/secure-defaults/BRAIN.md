---
name: secure-defaults
kind: brain
description: Use when an agent must choose defaults for a system, product, or configuration: shipping a new service, writing installation guides, reviewing a vendor's out-of-box settings, or deciding what happens when the user changes nothing. Provides secure-defaults reasoning: the default is the product because most users never change it, risk must be opt-in not opt-out, dangerous options require explicit deliberate action, and every default should be justifiable as the safe choice. Load this brain when designing anything with settings, so the lazy path is also the safe path.
version: 1.0.0
provides:
  - Default-is-the-product framing
  - Opt-in risk vs opt-out safety design
  - Explicit-action gating for dangerous options
  - Default audit and hardening checklists
  - Safe-configuration-as-shipped discipline
  - User-behavior-aware default selection
used_by: []
---

Most users never change defaults. Not because they are lazy, but because defaults look like recommendations from the maker. That makes the default the real product: whatever ships out of the box is what the world actually runs. Secure defaults is the discipline of making that out-of-box state the safe state, so doing nothing is safe and doing something dangerous requires deliberate effort. It matters because every breach that starts with "the default password," "the open S3 bucket," or "debug mode left on" is a defaults failure, not a user failure.

## Core mental models

**The default is the product.** Whatever you ship as the default is what 90 percent of deployments will run, forever. Design reviews should treat the default configuration as the primary configuration, because it is. If the secure setup requires fourteen manual steps, you do not have a secure product with insecure defaults. You have an insecure product.

**Risk is opt-in, safety is opt-out.** The user should have to take explicit action to become less safe, never to become safe. Authentication on by default, encryption on by default, verbose debug off by default. If someone wants the risky mode, make them ask for it clearly, and ideally warn them at the moment of choice. The safe path should be the path of least resistance.

**Dangerous options need friction.** Some options are inherently dangerous: disabling auth, binding to all interfaces, running as root. These should not be one checkbox away. Require explicit, deliberate action: a typed confirmation, a separate step, a warning that states the consequence plainly. Friction here is a feature. It converts accidents into decisions.

**Defaults are a promise.** Every default says "the maker thinks this is fine." Shipping an open-by-default database says you think open databases are fine. Users trust that promise, attackers exploit it. Audit your defaults the way you would audit a promise: is each one something you would defend publicly? If not, change it before someone else finds it.

## Operating checklist

1. List every default in the system: ports, credentials, permissions, features, logging, network binding.
2. For each default, ask: if the user never touches this, is the result safe? If not, change the default.
3. Authentication and encryption: on by default, no exceptions, no "simple mode" that skips them.
4. Network exposure: bind to localhost by default; listening on all interfaces requires explicit action.
5. Credentials: no default passwords, ever. Generate unique ones per install or force creation at setup.
6. Dangerous options (disable auth, debug mode, permissive CORS): gate behind explicit confirmation with a plain-language warning.
7. Debug, verbose, and development features: off in the shipped default. Dev mode must be chosen, not inherited.
8. Write the hardening guide for what remains, but assume most users will not read it. The defaults carry the weight.
9. Test the fresh install: deploy with zero changes and attack it. The default must survive.
10. Review defaults on every major release. New features bring new defaults, and new defaults bring new risk.

## Heuristics

- If the quickstart guide's first step is "disable the firewall," the defaults are wrong, not the user.
- No default credential survives contact with the internet. Generate or require, never ship.
- The most dangerous default is the one nobody remembers setting. Document every default visibly.
- Localhost first, internet later. Exposure should be a decision, not an accident.
- A warning the user must click through is cheaper than the breach the default would cause.
- Ship the hardened config as the only config. "Example insecure config" in docs becomes production weekly.
- Defaults decay: re-audit when features are added, dependencies change, or threats evolve.
- If you would be embarrassed explaining a default in a postmortem, change it now.

## Anti-patterns

- **Default credentials.** Admin/admin shipping in 2026. The internet scans for these in minutes.
- **Open by default.** Services binding to 0.0.0.0, buckets public, APIs unauthenticated until the user "hardens" them.
- **Debug in prod.** Verbose errors, stack traces, and debug endpoints on in the shipped build.
- **Insecure "simple mode."** A setup wizard that skips auth "to get you started quickly" and is never revisited.
- **Documented unsafety.** Knowing the default is unsafe and writing a hardening guide instead of fixing the default.

## Worked example

A team ships a self-hosted analytics tool. Old defaults: binds to 0.0.0.0, admin password "admin," no TLS, debug endpoints enabled. Every install guide starts with "change the password and set up TLS later." Secure-defaults redesign: binds to localhost only, with a setup step that generates a unique admin password and prints it once; TLS with a self-signed cert by default, proper cert as an explicit option; debug endpoints compiled out of the release build; exposing it to the network requires editing the bind address with a warning shown at startup ("you are exposing this to the network, ensure auth and TLS are configured"). Fresh-install test: deployed with zero changes, scanned from outside, nothing reachable, nothing with default creds. The lazy path is now the safe path. Support tickets about "I got hacked with a fresh install" drop to zero.
