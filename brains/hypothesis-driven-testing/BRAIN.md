---
name: hypothesis-driven-testing
kind: brain
description: Use when an agent must test instead of guess: probing whether a vulnerability is real, validating a detection rule, debugging a flaky behavior, or running any experiment where the result should change what the agent believes. Provides hypothesis-driven reasoning: state a falsifiable prediction before acting, change one variable at a time, treat negative results as data, and update beliefs explicitly. Load this brain whenever actions produce observations, so testing stays scientific instead of random.
version: 1.0.0
provides:
  - Falsifiable hypothesis framing
  - One-variable-at-a-time experiment design
  - Negative results as data discipline
  - Explicit belief updating
  - Confirmation bias countermeasures
  - Reproducible test documentation
used_by: []
---

Most testing is just poking things and watching. That works until it does not: you change three things, something breaks, and now you know less than before. Hypothesis-driven testing is the fix: before you act, write down what you expect to happen and why. Then act, observe, and update. It matters for agents especially, because agents act fast and can burn through hundreds of actions. Without hypotheses, speed produces noise. With them, speed produces knowledge.

## Core mental models

**Hypothesis before action.** A hypothesis is a falsifiable prediction: "If this input reaches the database unescaped, the query will return extra rows." It names the mechanism, not just the hope. Writing it before you act does two things: it forces you to understand the system enough to predict it, and it makes the result interpretable. An observation without a prior prediction is trivia. An observation that confirms or kills a prediction is evidence.

**One variable at a time.** If you change the payload, the endpoint, and the headers together and something works, you learned almost nothing. You cannot say which change mattered, so you cannot repeat it or explain it. Change one thing, observe, record. It feels slow. It is the fastest way to actually converge, because every result is attributable.

**Negative results are data.** A failed exploit attempt is not a wasted attempt if it kills a hypothesis. "The WAF did not block this payload, so the filter is not regex-based" is progress. Agents tend to discard failures and try something shinier. Do the opposite: log what each negative result rules out. The set of ruled-out explanations is what narrows the search to the truth.

**Update beliefs explicitly.** After each observation, say what changed: "I now believe the filter blocks keywords, not patterns, because the obfuscated variant passed." This stops the agent from quietly drifting, holding five contradictory beliefs at once, or forgetting what it already proved. Beliefs are working notes, and working notes must be current.

## Operating checklist

1. State the question in one sentence: what are you trying to learn?
2. Write the hypothesis: a falsifiable prediction naming the mechanism.
3. Predict the observation: what exactly will you see if the hypothesis is true? If false?
4. Design the minimal test: smallest action that distinguishes true from false.
5. Change one variable relative to the last test. Record what changed.
6. Run it. Record the raw observation, not your interpretation.
7. Compare observation to prediction. Confirm, kill, or refine the hypothesis.
8. Log the negative result explicitly: what does this rule out?
9. Update your stated belief in one sentence.
10. Repeat until the belief is strong enough to act on, then act.

## Heuristics

- If you cannot say what would prove you wrong, you do not have a hypothesis, you have a hope.
- The smallest distinguishing test beats the biggest impressive one.
- When stuck, test the assumption, not the conclusion. The bug is usually upstream of where you look.
- Three killed hypotheses in a row means your mental model is wrong. Rebuild it, do not just try harder.
- Write it down before you run it. Memory edits history.
- A flaky result is a hypothesis about timing or state. Make flakiness the next hypothesis.
- Prefer tests that rule out whole classes, not single instances.
- Timebox the loop: if ten tests teach nothing, the question is wrong.

## Anti-patterns

- **Shotgun testing.** Firing payloads or changes at random with no prediction. Fast, loud, and uninformative.
- **Confirmation bias.** Only running tests that would confirm the pet theory, ignoring the ones that could kill it.
- **Moving three knobs.** Changing multiple variables and declaring victory when something works. Unrepeatable by definition.
- **Discarding negatives.** Treating failed tests as wasted time instead of ruled-out explanations.
- **Belief drift.** Quietly changing what you believe without noting the observation that caused it.

## Worked example

An agent tests whether a login form is vulnerable to SQL injection. Hypothesis 1: "A single quote in the username causes a database error, which means input reaches the query." Prediction: error message or timing change. Test: username `admin'`. Observation: generic "invalid credentials," no change. Negative result logged: either input is escaped or errors are suppressed. Hypothesis 2: "Errors are suppressed, so I will test with boolean logic instead." Prediction: `' OR '1'='1` changes the result vs `' OR '1'='2`. One variable changed (payload logic, same field). Observation: both return identical generic messages. Belief update: "This endpoint gives no oracle through messages; I need a time-based test or a different field." Two tests, two ruled-out classes, and the next step is chosen by evidence, not vibes.
