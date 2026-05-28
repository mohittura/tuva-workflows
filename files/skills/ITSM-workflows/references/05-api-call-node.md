# API Call Node

An API call node is the action component of a workflow. While parameter nodes collect information from users, API call nodes use that information to perform real operations — creating tickets, searching records, validating data, fetching lists, authenticating users, and so on.

---

## Complete Structure

```json
"node_name": {
  "type": "api_call",
  "api_endpoint": "service/operation",
  "prefill_params": {
    "static_key": "static_value"
  },
  "copy_params": [],
  "response": {},
  "on_error": {
    "500": "error_handling_node",
    "701": "retry_node"
  },
  "is_silent_step": {
    "200": false,
    "708": true
  },
  "soft_storage_params": [],
  "silent_loading": [],
  "retry_count": 3,
  "set_available_options": [],
  "post_conditions": [],
  "default_step": "next_node_name"
}
```

---

## Properties

### `api_endpoint`

- **Type:** String
- **Required:** Yes
- **Purpose:** The path of the API endpoint to call. The base URL is configured at the system level — this field contains only the relative path.
- **Examples:** `"tickets/create"`, `"users/search"`, `"auth/validate"`, `"hr/departments"`

---

### `prefill_params`

- **Type:** Object
- **Required:** No
- **Purpose:** A map of static key-value pairs that are always included in the API request payload from this node. Use this for constant values that never change — routing keys, operation type identifiers, system identifiers, etc.
- **Example:**
  ```json
  "prefill_params": {
    "operation_type": "CREATE_TICKET",
    "source_system": "ITSM"
  }
  ```
- **Note:** Values in `prefill_params` can also be auto-filled at runtime using `silent_loading`. See [`silent-loading.md`](./silent-loading.md).

---

### `copy_params`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Maps values from the workflow's current state (parameter values or prior API responses) into the request payload for this API call. This is the primary mechanism for passing dynamic data between nodes.

  > For full structure and all source options, see [`copy-params.md`](./copy-params.md).

---

### `response`

- **Type:** Object
- **Required:** Yes (always start as `{}`)
- **Purpose:** After the API call executes, the engine writes the full response payload here. This stored response can be referenced by later nodes via `copy_params` or post-conditions.
- **Required Response Fields:** All API responses in this system always return at minimum:
  - `error_code` — a numeric status code indicating the outcome (see [`07-error-handling.md`](./07-error-handling.md))
  - `llm_feedback` — a natural language string describing what happened, suitable for the agent to relay to the user

---

### `on_error`

- **Type:** Object
- **Required:** No (but strongly recommended)
- **Purpose:** Maps specific error codes to handler nodes. When an API call returns an error code listed here, the engine routes to the corresponding node instead of following the `default_step` or evaluating post-conditions.
- **Example:**
  ```json
  "on_error": {
    "500": "system_error_node",
    "702": "request_new_credentials",
    "706": "escalate_to_admin"
  }
  ```
- **Design Guidance:** Always define `on_error` for API call nodes. At minimum, handle `500` (server errors) and any domain-specific error codes your backend returns.

  > For the full error code reference and propagation model, see [`07-error-handling.md`](./07-error-handling.md).

---

### `is_silent_step`

- **Type:** Object (error code → boolean)
- **Required:** No
- **Purpose:** Controls whether the `llm_feedback` from this API call is passed to the agent (and thereby shown to the user). Keyed by error code.

  | Value | Effect |
  |---|---|
  | `false` | `llm_feedback` IS passed to the agent — the user sees the outcome |
  | `true` | `llm_feedback` is NOT passed to the agent — the step runs invisibly |

- **Example:**
  ```json
  "is_silent_step": {
    "200": true,
    "500": false
  }
  ```
- **Use Case:** Background API calls (fetching department lists, pre-validating data) where a success doesn't need to surface to the user, but failures should.

  > Note: `is_silent_step` controls agent visibility of the *result*. For pre-filling parameter values silently from API responses, see [`silent-loading.md`](./silent-loading.md).

---

### `soft_storage_params`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Persists selected fields from this node's API response into `__SOFT_STORAGE__`, making them available to future workflows in the same session without re-fetching.
- **Structure:**
  ```json
  "soft_storage_params": [
    {
      "keys": [
        {
          "get_from": "auth_token",
          "set_to": "user_auth_token",
          "source": "response"
        }
      ],
      "step": "current_step_name"
    }
  ]
  ```
- **Fields:**
  - `get_from` — the field name in the response to read from
  - `set_to` — the key name to store it under in `__SOFT_STORAGE__`
  - `source` — always `"response"` for API call responses
  - `step` — the name of this node (self-reference, used for state tracking)

---

### `silent_loading`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Automatically populates `prefill_params` values in this node from the response of a prior API call, without user interaction. This is the mechanism for chaining API calls where the output of one feeds the input of another invisibly.

  > For full usage, structure, and nested field access, see [`silent-loading.md`](./silent-loading.md).

---

### `retry_count`

- **Type:** Integer
- **Required:** No
- **Purpose:** The number of times the engine will retry this API call if it encounters a transient failure (e.g., a 500 server error). The engine handles retry delays automatically.
- **Default:** If omitted, no automatic retries occur.
- **When to Set:** Use for non-idempotent-safe calls only when your backend guarantees safe retries, or for read-only operations. `retry_count` must be set for the nodes of type  `api_call`.

---

### `set_available_options`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** After this API call completes, writes a list from the response into the `available_options` of a downstream parameter node. This is the mechanism for dynamic option population — fetching valid choices from a backend before asking the user to select one.
- **Structure:**
  ```json
  "set_available_options": [
    {
      "set_from": "response.departments",
      "set_to": "user_department",
      "set_step": "collect_user_info"
    }
  ]
  ```
- **Fields:**
  - `set_from` — dot-notation path to the list in the API response (e.g., `"response.departments"`)
  - `set_to` — the `params` key in the target parameter node whose `available_options` should be populated
  - `set_step` — the name of the parameter node that contains the target parameter

---

## Related References

- [`copy-params.md`](./copy-params.md) — To populate the request payload of the `api_call` nodes using the parameter values collected from the user or the response of the previous api calls.
<!-- - [`validation.md`](./validation.md) — Using API calls for remote validation inside parameter nodes -->
- [`silent-loading.md`](./silent-loading.md) — Auto-filling `prefill_params` from prior API responses
- [`07-error-handling.md`](./07-error-handling.md) — Error codes, `on_error` routing, and propagation model
- [`06-post-conditions.md`](./06-post-conditions.md) — Conditional routing after API call completion