---
name: reviewer-xss-patterns
description: Use when reviewing code for cross-site scripting
  vulnerabilities. Covers unsafe template usage, dangerous DOM sinks,
  framework bypasses, and verifying context-correct encoding. Use when
  reviewing frontend or template code, when auditing a new codebase, when
  the scanner flags a possible XSS, or when teaching the team what XSS
  looks like in code.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: code-reviewer
requires: [code-reviewer]
extends: []
relates: [secure-coding, web-xss]
tools:
  - name: Python
    version: 3.12
---

Code review catches XSS where it is introduced: the template that skips
escaping, the JavaScript that writes innerHTML, the `| safe` that nobody
justified. This skill covers the review patterns across server templates
and client JavaScript: the dangerous constructs, how to verify encoding
is context-correct, and the framework-specific bypasses. Review the
render point, not the data.

## Quick Workflow

1. Find every render point: templates, DOM writes, URL builders.
2. For each, identify the sink context (HTML, attribute, JS, URL).
3. Verify the encoding matches the context, or that the framework
   auto-escapes it.
4. Flag every escaping bypass (`safe`, `bypassSecurity`, innerHTML)
   and demand justification.
5. Check the dangerous sinks list below for each JavaScript file.
6. Write findings with file, line, context, and the safe pattern.

## 1. Template patterns

```html
<!-- Jinja2 / Django: auto-escape is ON by default; these break it -->
{{ user_input }}              <!-- SAFE: escaped -->
{{ user_input | safe }}       <!-- REVIEW: why is this trusted? -->
{% autoescape off %}...{% endautoescape %}  <!-- REVIEW: whole block unescaped -->

<!-- React: escaped by default; this is the bypass -->
<div>{userInput}</div>                          <!-- SAFE -->
<div dangerouslySetInnerHTML={{__html: userInput}} />  <!-- REVIEW -->

<!-- Angular: interpolation is safe; this bypasses it -->
<p>{{ userInput }}</p>                        <!-- SAFE -->
<div [innerHTML]="userInput"></div>           <!-- REVIEW -->
<div [innerHTML]="sanitizer.bypassSecurityTrustHtml(x)"></div>  <!-- REVIEW HARD -->
```

Every bypass needs a comment explaining the trust basis, and "from our
API" is not a trust basis (the API serves user input). No justification,
no bypass: that is the review rule.

## 2. JavaScript sink review

```javascript
// Reviewer red list: search every JS file for these
element.innerHTML = x;        // REVIEW: use textContent
element.outerHTML = x;        // REVIEW
document.write(x);            // REVIEW: remove
eval(x);                      // VULN: never eval untrusted input
setTimeout(x, 100);           // REVIEW if x is a string: use a function
location.href = x;            // REVIEW: allow-list the destination
new Function(x);              // VULN: eval by another name

// jQuery: .html() is a sink, .text() is not
$("#out").html(userInput);    // REVIEW
$("#out").text(userInput);    // SAFE

// URL building: javascript: URLs execute
a.href = userInput;           // REVIEW: validate scheme allow-list first
```

Grep the red list on every review; it takes seconds and catches the
majority of DOM XSS. Then read the surrounding code for the ones that
need context to judge.

## 3. Context verification

```html
<!-- The encoder must match the context: review each render point -->
<script>var name = "{{ user_input }}";</script>
<!-- REVIEW: HTML-escaping in a JS string context is WRONG.
     Need: var name = {{ user_input | tojson }}; -->

<a href="{{ user_url }}">link</a>
<!-- REVIEW: URL context needs scheme validation, not just escaping.
     javascript: URLs survive HTML-escaping. -->

<div title="{{ user_title }}">x</div>
<!-- SAFE if attribute is quoted and value is HTML-escaped -->
```

The most common review miss: correct escaping, wrong context. HTML
encoding does not neutralize a JavaScript string breakout, and URL
encoding does not stop `javascript:`. Check the context first, the
encoder second.

## Edge cases

- The data is "trusted" (admin-entered, from a partner API). Stored
  XSS comes from trusted roles too; encode by context regardless of
  source trust.
- The bypass is load-bearing (rich text editor). Require the sanitizer
  (DOMPurify or equivalent) with its config reviewed, plus tests
  against the bypass corpus.
- Legacy code disables auto-escape globally. Flag it as systemic;
  the fix is enabling it and fixing breakages, not leaving it off.
- The scanner flags safe code. Verify and note the false positive
  pattern so future reviews skip it faster.

## Escalation

- Systemic missing encoding: propose the framework default fix
  (enable auto-escape, ban innerHTML) with the instance list.
- A bypass is genuinely needed: require the sanitizer, the config
  review, and the regression tests as the acceptance criteria.
- Continuous protection: add the dangerous-sink grep and the hostile
  render tests to CI.

## Detection and defender view

For defenders, review is the leftmost XSS control: every finding fixed
in review is an incident that never happens. Complement with DAST
against staging and CSP reporting in production (blocked inline scripts
reveal the misses). The defender's metric is XSS findings per review
hour trending down as the team learns the patterns.

## Key references

- CWE-79 (Cross-site Scripting).
- OWASP XSS Prevention Cheat Sheet.
- OWASP Code Review Guide: XSS sections.
