# Node Types & Structure

All executable logic in a workflow lives inside nodes. Each node is an entry in the `steps` object of the workflow JSON and represents a single unit of work — either collecting information from a user or performing an operation against a backend system.

---

## Common Node Properties

Every node, regardless of type, shares the following base properties:

### `type`

- **Type:** String Literal
- **Required:** Yes
- **Values:** `"parameter"` or `"api_call"`
- **Purpose:** Determines the fundamental behavior of the node. The workflow engine reads this field first to decide how to process the node.

---

### `default_step`

- **Type:** String
- **Required:** Yes
- **Purpose:** Specifies the next node to execute when no post-condition evaluates to `true`. Think of this as the "else" branch — the fallback path when no conditional routing applies.
- **Values:** Any other node name in the `steps` object, or `"<--|end-of-flow|-->"` to terminate the workflow.

---

### `post_conditions`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Defines conditional branching logic evaluated after the node executes. If a condition matches, the workflow routes to the `true_step` rather than the `default_step`.
- **Evaluation Order:** Conditions are checked in array order. The first one that evaluates to `true` wins.

> For the full post-condition structure and all supported operators and functions, see [`06-post-conditions.md`](./06-post-conditions.md).

---

## Special System Constructs

These are not regular node types but built-in constructs the engine recognizes.

### `__SOFT_STORAGE__`

`__SOFT_STORAGE__` is a special parameter node that acts as a **global, session-scoped data cache** accessible across all workflows for the duration of a user session.

**Purpose:**
- Store data that multiple workflows need to share — such as authentication tokens, user identity, or preference data — without prompting the user repeatedly.
- Acts as a "memory" layer between otherwise isolated workflow executions.

**Key Behaviors:**
- Its `params` dictionary starts empty and is populated either by API call nodes using `soft_storage_params`, or by silent loading.
- Any node in any workflow can read from `__SOFT_STORAGE__` via `copy_params` by referencing `"step": "__SOFT_STORAGE__"`.
- Data written here persists for the entire user session, not just the current workflow.

**Example Use Cases:**
- Auth tokens retrieved during a login workflow are stored here and reused by all subsequent workflows.
- User email or department fetched once and reused across multiple ticket creation flows.

---

### `<--|end-of-flow|-->`

This is a **terminal marker**, not an actual node. It signals to the workflow engine that execution should stop and the workflow should be marked as complete (`is_workflow_ended = true`).

**Usage:**
- Set as the `default_step` of the final node in a workflow.
- Set as the `true_step` in a post-condition when a successful path should terminate the workflow.

```json
"submit_ticket_api": {
  "type": "api_call",
  "api_endpoint": "tickets/create",
  "default_step": "<--|end-of-flow|-->"
}
```

---

## Node Types At a Glance

| Node Type | `type` Value | Primary Role | Key Properties |
|---|---|---|---|
| Parameter Node | `"parameter"` | Collect and validate user input | `params`, `post_conditions`, `default_step` |
| API Call Node | `"api_call"` | Execute backend HTTP requests | `api_endpoint`, `copy_params`, `on_error`, `default_step` |
| Soft Storage *(special)* | `"parameter"` | Cross-workflow session cache | `params` (empty initially, auto-managed) |
| End of Flow *(terminal marker)* | — | Terminate the workflow | Used as a step reference, not a node itself |

---

## Detailed References

Each node type has its own dedicated document covering the full property specification, structure examples, and design guidance:

- **Parameter Nodes** → [`04-parameter-node.md`](./04-parameter-node.md)
  Covers: `params`, `value`, `llm_key`, `datatype`, `description`, `validation`, `available_options`, `is_optional`, `retry_count`

- **API Call Nodes** → [`05-api-call-node.md`](./05-api-call-node.md)
  Covers: `api_endpoint`, `prefill_params`, `copy_params`, `response`, `on_error`, `is_silent_step`, `soft_storage_params`, `retry_count`, `set_available_options`, `silent_loading`

- **Copy Parameters** (used by both node types) → [`copy-params.md`](./copy-params.md)

- **Validation** (used by parameter nodes and API call validation) → [`validation.md`](./validation.md)

- **Silent Loading** (used to auto-fill values from API responses) → [`silent-loading.md`](./silent-loading.md)