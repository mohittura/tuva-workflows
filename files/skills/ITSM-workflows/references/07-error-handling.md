# Error Handling

Error handling in the workflow engine operates at multiple levels — from standardized error codes returned by backend systems, to node-level routing decisions, to user-facing feedback messages. Each layer plays a specific role in keeping workflows resilient and user experiences graceful.

---

## Standardized Error Codes

All API responses in this system must include an `error_code` field. The workflow engine uses this code to determine how to proceed after an API call node executes.

| Code | Meaning | Typical Cause |
|---|---|---|
| `200` | Success | Operation completed as expected |
| `500` | Server Error | Backend system unavailable, unhandled exception, or internal failure |
| `701` | Validation Error | The submitted data failed backend validation rules |
| `702` | Authentication Error | The provided credentials are invalid or have expired |
| `704` | Not Found / Invalid | The requested resource does not exist |
| `706` | Permission Denied | The user does not have the rights to perform this operation |
| `708` | Business Logic Error | The operation was rejected due to a business rule violation |

All responses must also include an `llm_feedback` field — a natural language string the agent can relay to the user explaining what happened.

---

## Error Propagation Model

Errors flow upward through four layers:

```
1. API Level
   └── Backend returns: { "error_code": 702, "llm_feedback": "Session expired. Please log in again." }

2. Workflow Level
   └── API call node receives the response and stores it in its "response" field

3. Routing Level
   └── Engine checks "on_error" for a matching code → routes to handler node
       If no match in on_error → evaluates post_conditions → falls to default_step

4. User Level
   └── llm_feedback is passed to agent (if is_silent_step is false for this code)
       Agent presents the message to the user in natural language
```

---

## `on_error` — Node-Level Error Routing

`on_error` is defined inside an API call node and maps specific error codes directly to handler nodes, bypassing post-condition evaluation entirely.

```json
"on_error": {
  "500": "system_error_node",
  "702": "request_new_credentials",
  "706": "escalate_to_admin"
}
```

**Routing Priority:**
1. If the returned `error_code` is in `on_error` → route to the mapped node immediately.
2. If not in `on_error` → proceed to evaluate `post_conditions`.
3. If no post-condition matches → follow `default_step`.

**Design Guidance:**
- Always define at minimum a `500` handler in `on_error` to catch server-side failures gracefully.
- Use `on_error` for codes that require a distinct recovery path (e.g., `702` → re-authenticate, `706` → escalate).
- Use `post_conditions` for codes that are part of expected business logic flow (e.g., checking for `200` vs. `701`).

> For `on_error` field specification, see [`05-api-call-node.md`](./05-api-call-node.md).

---

## `on_error` vs. `post_conditions` — When to Use Which

| Scenario | Recommended Approach |
|---|---|
| Unexpected server failure (500) | `on_error` — route to a graceful error message node |
| Authentication expired (702) | `on_error` — route to credential re-collection |
| Validation failure (701) that needs custom handling | `on_error` or `post_conditions` depending on complexity |
| Checking for success (200) to route forward | `post_conditions` |
| Business rule rejection (708) that should loop | `post_conditions` |
| Any error requiring immediate, code-specific routing | `on_error` |

---

## Controlling User Visibility with `is_silent_step`

Not every API outcome should be shown to the user. Background operations — like pre-fetching a department list or silently validating a token — may not be relevant to the user even if they fail.

`is_silent_step` controls per-error-code whether the `llm_feedback` is passed to the agent:

```json
"is_silent_step": {
  "200": true,
  "500": false
}
```

- `true` → `llm_feedback` is suppressed. The agent does not see the outcome.
- `false` → `llm_feedback` is included in agent context. The agent can surface it to the user.

**Design Guidance:** Set `200` to `true` for background operations where success is not meaningful to the user. Always set failure codes (`500`, `702`, `708`, etc.) to `false` so the user can be informed and take action.

---

## Retry Logic

API call nodes support automatic retries for transient failures via the `retry_count` field:

```json
"retry_count": 3
```

- The engine retries the API call up to this many times on transient failures (typically `500` errors).
- After the retry limit is exceeded, the engine proceeds with the last response — routing via `on_error` or `post_conditions` as usual.
- Parameter nodes also support `retry_count` to limit how many times a user can attempt to provide a valid value before the workflow routes to an error node.

---

## Designing Resilient Error Flows

**Every API call node should have:**

1. `on_error` handlers for critical error codes (`500`, `702`, `706` as relevant).
2. A `default_step` that points to a safe fallback — never leave `default_step` pointing to a success path.
3. Post-conditions that explicitly check for `200` before routing forward, rather than assuming success.

**Every workflow should have:**

1. Dedicated error message nodes (type `"parameter"` or `"api_call"`) that present a clear message to the user and end the workflow cleanly.
2. A path that always terminates — either via `<--|end-of-flow|-->` or via a node with a terminal `default_step`. Workflows must never get stuck.

---

## Related References

- [`05-api-call-node.md`](./05-api-call-node.md) — `on_error`, `is_silent_step`, `retry_count` field specs
- [`06-post-conditions.md`](./06-post-conditions.md) — Conditional routing including error-code-based branching
- [`ref-error-handling.md`](./ref-error-handling.md) — Quick reference card: all error codes, propagation, and routing decision guide