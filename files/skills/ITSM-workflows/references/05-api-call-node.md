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
## Example
[Example of API Call Node](../examples/create_zendesk_tickets.json)

```json
"send_email_otp": {
      "type": "api_call",
      "inputs": {},
      "response": {},
      "api_endpoint": "send-otp",
      "prefill_params": {},
      "copy_params": [
        {
          "keys": [
            {
              "copy_from": "user_email",
              "copy_to": "email"
            }
          ],
          "step": "collect_user_name_|_email"
        }
      ],
      "default_step": "collect_otp"
    }
```

  Here, `send_email_otp` is defined as an `api_call` node that triggers an external API operation to send a one-time password (OTP):
  * **`api_endpoint`**: Specifies the endpoint `send-otp` to indicate which API endpoint is to be invoked.
  * **`copy_params`**: This copies the collected value of `user_email` from the previous step (`collect_user_name_|_email`) and maps it to the `email` key in the request payload for this API call.
  * **`default_step`**: Once the API call executes successfully, the workflow engine automatically transitions to the `collect_otp` node.

  **Note** This is just a specific example to illustrate the node structure. Configurations are subject to change based on the workflow requirements; different API steps will define endpoints, copy parameters, error handling, or option setting differently depending on the specific design of the flow and requirement of the workflow.

---

## Properties

#### 1. `api_endpoint`

- **Type:** String
- **Required:** Yes
- **Purpose:** The path of the API endpoint to call. The base URL is configured at the system level — this field contains only the relative path.
- The endpoints will be provided by the user in the WRS (Workflow Request Specification). The user can define multiple endpoints and can specify the name of the endpoint in the node that he wants to use.
- if the endpoints are not specified by the user, then ask the user about the endpoints to be used.

---

#### 2. `prefill_params`

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

#### 3. `copy_params`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Maps values from the workflow's current state (parameter values or prior API responses) into the request payload for this API call. This is the primary mechanism for passing dynamic data between nodes.

  > For full structure and all source options, see [`copy-params.md`](./copy-params.md).

---

#### 4. `response`

- **Type:** Object
- **Required:** Yes (always start as `{}`)
- **Purpose:** After the API call executes, the engine writes the full response payload here. This stored response can be referenced by later nodes via `copy_params` or post-conditions.
- **Required Response Fields:** All API responses in this system always return at minimum:
  - `error_code` — a numeric status code indicating the outcome (see [`07-error-handling.md`](./07-error-handling.md))
  - `llm_feedback` — a natural language string describing what happened, suitable for the agent to relay to the user

---

#### 5. `on_error`

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

#### 6. `is_silent_step`

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

#### 7. `soft_storage_params`

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

#### 8. `silent_loading`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Automatically populates `prefill_params` values in this node from the response of a prior API call, without user interaction. This is the mechanism for chaining API calls where the output of one feeds the input of another invisibly.

  > For full usage, structure, and nested field access, see [`silent-loading.md`](./silent-loading.md).

---

#### 9. `retry_count`

- **Type:** Integer
- **Required:** No
- **Purpose:** The number of times the engine will retry this API call if it encounters a transient failure (e.g., a 500 server error). The engine handles retry delays automatically.
- **Default:** If omitted, no automatic retries occur.
- **When to Set:** Use for non-idempotent-safe calls only when your backend guarantees safe retries, or for read-only operations. `retry_count` must be set for the nodes of type  `api_call`.

---

#### 10. `set_available_options`

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
#### 11. `default_step`

- **Type:** String
- **Required:** Yes
- **Purpose:** Specifies the next node to execute when no post-condition evaluates to `true`. Think of this as the "else" branch — the fallback path when no conditional routing applies.
- **Values:** Any other node name in the `steps` object, or `"<--|end-of-flow|-->"` to terminate the workflow.

---

#### 12. `post_conditions`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Defines conditional branching logic evaluated after the node executes. If a condition matches, the workflow routes to the `true_step` rather than the `default_step`.
- **Evaluation Order:** Conditions are checked in array order. The first one that evaluates to `true` wins.

  > For the full post-condition structure and all supported operators and functions, see [`06-post-conditions.md`](./06-post-conditions.md).

---

## Related References

- [`copy-params.md`](./copy-params.md) — Explains how to map and populate the request payload of the current API call using the gathered user inputs or prior API responses.
- [`silent-loading.md`](./silent-loading.md) — Covers the mechanisms for silently pre-filling API parameters using data collected in previous steps automatically.
- [`07-error-handling.md`](./07-error-handling.md) — Covers how to handle API call failures, to configure custom error paths (`on_error`), and interpret system error codes.
- [`06-post-conditions.md`](./06-post-conditions.md) — Covers routing rules and conditions to dynamically decide the next workflow step based on the API response.