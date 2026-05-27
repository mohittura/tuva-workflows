# Reference: Error Handling Quick Reference

This document is a concise reference card for error codes, routing decisions, and error-handling patterns. For the full conceptual guide, see [`07-error-handling.md`](./07-error-handling.md).

---

## Error Code Table

| Code | Meaning | Suggested `on_error` Action |
|---|---|---|
| `200` | Success | Route forward via `post_conditions` |
| `500` | Server Error | Route to a "something went wrong" message node |
| `701` | Validation Error | Route back to the parameter collection node with feedback |
| `702` | Authentication Error | Route to credential re-collection or session restart |
| `704` | Not Found / Invalid | Route to a "resource not found" message node |
| `706` | Permission Denied | Route to escalation or inform user they lack access |
| `708` | Business Logic Error | Route back to relevant collection node with explanation |

---

## Routing Decision Tree

After an API call node executes:

```
Did the response error_code match an entry in on_error?
├── YES → Route immediately to the mapped handler node
└── NO  →
      Does any post_condition evaluate to true?
      ├── YES → Route to that condition's true_step
      └── NO  → Follow the node's default_step
```

---

## `on_error` vs. `post_conditions` Cheat Sheet

| Use `on_error` when... | Use `post_conditions` when... |
|---|---|
| The error requires a completely different recovery path | The routing is part of expected business logic |
| You need immediate routing before any condition is checked | You're branching on success vs. specific failure codes |
| The error is unexpected (server failures, auth issues) | Multiple outcomes need to be distinguished |

---

## `is_silent_step` Patterns

```json
"is_silent_step": {
  "200": true,   // Background success → don't narrate to user
  "500": false,  // Server failure → inform user
  "701": false,  // Validation failure → inform user
  "708": false   // Business rule failure → inform user
}
```

**Rule of thumb:** Silence successes for background operations. Never silence failures.

---

## `retry_count` Reference

| Field Location | Purpose |
|---|---|
| `parameter.params.param_key.retry_count` | Max attempts for a user to provide valid input |
| `api_call.retry_count` | Max retries for transient API failures (e.g., 500 errors) |

If omitted: parameter nodes allow unlimited user retries; API call nodes do not automatically retry.

---

## Designing Error Handler Nodes

A typical error handler node is a simple parameter node or API call node that:
1. Surfaces a clear, user-facing message via `llm_feedback` or a static message parameter.
2. Routes to `"<--|end-of-flow|-->"` as its `default_step` to cleanly terminate the workflow.

```json
"system_error_node": {
  "type": "api_call",
  "api_endpoint": "notify/error",
  "prefill_params": {
    "message_type": "SYSTEM_ERROR"
  },
  "is_silent_step": {
    "200": false
  },
  "default_step": "<--|end-of-flow|-->"
}
```

---

## Required Response Fields

Every backend API response consumed by this system must include:

| Field | Type | Purpose |
|---|---|---|
| `error_code` | Integer | Standardized code used by the engine for routing |
| `llm_feedback` | String | Natural language message passed to the agent for user display |

Missing either field will cause unpredictable engine behavior.

---

## Related Documents

- [`07-error-handling.md`](./07-error-handling.md) — Full error handling guide
- [`05-api-call-node.md`](./05-api-call-node.md) — `on_error`, `is_silent_step`, `retry_count` specs
- [`06-post-conditions.md`](./06-post-conditions.md) — Conditional routing including error-code branching