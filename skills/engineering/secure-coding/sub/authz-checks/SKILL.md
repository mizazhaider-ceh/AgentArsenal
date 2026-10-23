---
name: authz-checks
description: Use when writing or reviewing code that decides who may do
  what, and you need authorization enforced correctly. Covers ownership
  checks, role checks, deny-by-default design, and testing authorization.
  Use when building access-controlled features, when fixing IDOR or
  privilege escalation, when reviewing permission logic, or when the
  threat model includes malicious legitimate users.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
parent: secure-coding
requires: [secure-coding]
extends: []
relates: [code-reviewer, input-validation-patterns]
tools:
  - name: Python
    version: 3.12
  - name: Bandit
    version: 1.7
---

Authorization decides whether this authenticated user may touch this
object or use this function. This skill covers implementing it
correctly: server-side checks on every access, ownership verification,
role enforcement, and deny-by-default design. Authentication without
authorization is the IDOR factory; this skill closes it.

## Quick Workflow

1. List every object access and every privileged function.
2. Define the authorization rule for each: who may do what to which.
3. Enforce server-side, on every request, with no client trust.
4. Check ownership for object access; check role for functions.
5. Deny by default: unknown cases fail closed.
6. Test with multiple accounts: the A/B/admin matrix.
7. Log authorization failures for attack detection.

## 1. Ownership and role checks

```python
#!/usr/bin/env python3
"""Authorization patterns: check on the server, every time."""

def get_order(current_user, order_id: int):
    order = db.get_order(order_id)
    if order is None:
        raise NotFound()
    # Ownership check: the object belongs to the requester
    if order.owner_id != current_user.id and not current_user.is_admin:
        log_authz_failure(current_user.id, f"order:{order_id}")
        raise Forbidden()
    return order

def delete_user(current_user, target_id: int):
    # Role check: the FUNCTION requires admin, regardless of object
    if not current_user.is_admin:
        log_authz_failure(current_user.id, "delete_user")
        raise Forbidden()
    # Ownership still applies: admins follow their own rules where defined
    return db.delete_user(target_id)

# Deny by default: no rule matched means no access
def authorize(current_user, action, resource) -> bool:
    rule = POLICY.get((action, resource.type))
    if rule is None:
        return False
    return rule(current_user, resource)
```

The check lives in the data access layer or a single authorization
module, not scattered through handlers. Scattered checks get skipped;
central checks get tested.

## 2. Common failure patterns

```python
#!/usr/bin/env python3
"""Patterns to delete on sight."""

# 1. Client-side only: the UI hides the button, the API allows it
#    FIX: enforce in the API handler (shown above)

# 2. Check on read, not on write:
def bad_update(current_user, order_id, data):
    order = db.get_order(order_id)
    # missing ownership check here: any user updates any order
    return db.update_order(order_id, data)

# 3. ID in the URL trusted without verification:
#    /api/users/123 where 123 is used directly as the target
#    FIX: compare the URL id against the session's user id or ownership

# 4. Role from the client: role = request.json["role"]
#    FIX: roles come from the session/server, never the request
```

Review every handler for the pattern "fetches object, acts on object,
never checks ownership." That single missing line is the most common
authorization bug in existence.

## 3. Testing authorization

```python
#!/usr/bin/env python3
"""The A/B/admin test matrix, automated."""

def test_authz_matrix(client):
    # A reads A's object: allowed
    assert client.get("/orders/1001", token=TOKEN_A).status_code == 200
    # B reads A's object: denied
    assert client.get("/orders/1001", token=TOKEN_B).status_code == 403
    # A reads admin function: denied
    assert client.get("/admin/users", token=TOKEN_A).status_code == 403
    # Admin reads admin function: allowed
    assert client.get("/admin/users", token=TOKEN_ADMIN).status_code == 200
    # No token at all: denied
    assert client.get("/orders/1001").status_code == 401
    print("authz matrix passed")
```

Run the matrix in CI for every permission-sensitive endpoint. Manual
pentests find these bugs; automated matrices prevent their return.

## Edge cases

- Shared resources (team objects, public links). Define the sharing
  model explicitly: who shares, what the link grants, how it revokes.
- Performance: authorization checks add queries. Cache the user's
  roles per request, not per check, and keep ownership checks indexed.
- Admin override paths. Document which admin actions bypass ownership
  and log them; unlogged override is a backdoor by another name.
- Object creation: the creator owns it, but creation itself may need
  a quota or role check; do not forget the create path.

## Escalation

- The permission model is unclear: stop and define it with the product
  owner; code cannot enforce a policy nobody wrote down.
- Legacy code has no central check: add the authorization module and
  migrate handlers one by one, with the matrix test guarding each.
- A bypass is found in production: fix, add the regression test, and
  review the logs for exploitation of the same pattern elsewhere.

## Detection and defender view

Authorization failures are high-signal logs: legitimate users rarely
trigger them, attackers trigger them constantly. Alert on bursts per
user and on any failure against admin endpoints. The engineering view:
every 403 in the logs is a prevented incident; make sure the 403s are
actually being enforced and not just returned by accident.

## Key references

- CWE-862 (Missing Authorization).
- CWE-639 (Authorization Bypass Through User-Controlled Key).
- OWASP Authorization Cheat Sheet.
- OWASP API Security Top 10: broken object and function level
  authorization.
