# Validation

Validation in the workflow engine ensures that a user's input satisfies defined rules before the value is accepted and stored. Validation is configured per-parameter inside a parameter node and supports both **local rules** (evaluated by the engine itself) and **remote rules** (evaluated by an external API call).

---

## Where Validation Appears

Validation is defined inside a parameter's definition object:

```json
"params": {
  "user_email": {
    "value": "",
    "llm_key": "Email Address",
    "datatype": "str",
    "description": "Corporate email address.",
    "validation": { /* validation rules here */ }
  }
}
```

---

## Validation Object Structure

```json
"validation": {
  "function": "regex",
  "criteria": "^[a-zA-Z0-9._%+-]+@company\\.com$",
  "operator": "==",
  "condition_key": "",
  "condition_source": "",
  "condition_step": "",
  "start": "",
  "end": "",
  "api_call": {
    "api_endpoint": "validation/check_user",
    "true_code": 200,
    "prefilled_params": {
      "routing_key": "user_lookup"
    },
    "copy_params": [
      {
        "keys": [
          {
            "copy_from": "user_email",
            "copy_to": "email",
            "source": ""
          }
        ],
        "step": "collect_user_email"
      }
    ]
  }
}
```

---

## Local Validation Fields

Local validation is evaluated by the workflow engine without making any external call.

### `function`

- **Type:** String Literal
- **Required:** No (if omitted, a direct comparison is performed using `operator`)
- **Purpose:** Applies a transformation or check to the input value before comparison.

| Function | Description |
|---|---|
| `"regex"` | Test the value against the pattern in `criteria` |
| `"range"` | Check if the value falls between `start` and `end` |
| `"len"` | Check the length of the string or list against `criteria` |
| `"is_empty"` | Pass if value is `""`, `[]`, or `null` |
| `"is_not_empty"` | Pass if value is not empty |
| `"is_none"` | Pass if value is `null` |
| `"is_not_none"` | Pass if value is not `null` |
| `"is_subset"` | Pass if all elements of the value list are contained in `criteria` list |
| `"is_date_time_format_valid"` | Pass if the value is a parseable date/time string |

---

### `criteria`

- **Type:** Varies (string, number, list — depends on `function` and `operator`)
- **Required:** Yes for local validation (unless using dynamic comparison)
- **Purpose:** The static value to compare the (optionally transformed) input against.

**Examples by function:**
- `"regex"` → `"^\\d{4}-\\d{2}-\\d{2}$"` (date format YYYY-MM-DD)
- `"len"` + `"operator": "<="` → `100` (max 100 characters)
- `"is_subset"` → `["Low", "Medium", "High", "Critical"]`
- No function + `"operator": "=="` → `"active"`

---

### `operator`

- **Type:** String Literal
- **Required:** Yes for local validation
- **Purpose:** Defines the comparison between the (optionally transformed) input and `criteria`.
- **Supported:** `"=="`, `"!="`, `">"`, `"<"`, `">="`, `"<="`, `"in"`, `"not in"`

---

### `start` and `end`

- **Type:** String or Number
- **Required:** Only when `function` is `"range"`
- **Purpose:** Define the inclusive lower and upper bounds for a range check.
- **Example:** `"start": 1, "end": 10` with `"function": "range"` passes if the value is between 1 and 10.

---

### Dynamic Comparison: `condition_key`, `condition_step`, `condition_source`

Instead of comparing the input against a static `criteria` value, you can compare it against a **value dynamically read from another node at runtime**.

| Field | Purpose |
|---|---|
| `condition_key` | The parameter or response field name to read from |
| `condition_step` | The node containing the comparison value |
| `condition_source` | Where in that node to find it (`""` for param value, `"response"` or `"response.field"` for API response) |

**Use Case:** Confirm that a "confirm email" parameter matches the "email" parameter collected in a prior step.

```json
"validation": {
  "function": "",
  "operator": "==",
  "condition_key": "user_email",
  "condition_step": "collect_user_email",
  "condition_source": ""
}
```

---

## Remote Validation via `api_call`

When the validation rule requires a backend lookup — checking if a user exists, verifying a record is active, validating a license key — use the `api_call` sub-object inside `validation`.

### `api_call` Fields

#### `api_endpoint`

- **Type:** String
- **Required:** Yes
- **Purpose:** The relative API endpoint path for the validation call.

---

#### `true_code`

- **Type:** Integer
- **Required:** Yes
- **Purpose:** The `error_code` value in the API response that signals successful validation. Any other code is treated as a validation failure, and the user is prompted again.
- **Example:** `200`

---

#### `prefilled_params`

- **Type:** Object
- **Required:** No
- **Purpose:** Static key-value pairs always included in the validation API request. Used for routing keys or operation type identifiers.
- **Example:** `{"routing_key": "user_lookup"}`

---

#### `copy_params`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Maps values from already-collected parameters or prior API responses into the validation API request payload.
- **Structure:** Same as `copy_params` in an `api_call` node.

> See [`ref-copy-params.md`](./ref-copy-params.md) for full structure and examples.

---

## Validation Failure Behavior

When a local or remote validation fails:
1. The engine does **not** store the value.
2. It decrements the parameter's `retry_count` (if set).
3. The `llm_feedback` from the validation API (or a default failure message for local rules) is passed to the agent.
4. The agent re-prompts the user for the value.
5. If `retry_count` is exhausted, the engine routes to the error-handling path.

---

## Examples

### Local: Regex Email Format

```json
"validation": {
  "function": "regex",
  "criteria": "^[a-zA-Z0-9._%+-]+@company\\.com$",
  "operator": "=="
}
```

### Local: Numeric Range

```json
"validation": {
  "function": "range",
  "start": 1,
  "end": 100,
  "operator": "=="
}
```

### Remote: Verify User Exists

```json
"validation": {
  "api_call": {
    "api_endpoint": "users/verify",
    "true_code": 200,
    "copy_params": [
      {
        "keys": [
          {
            "copy_from": "employee_id",
            "copy_to": "emp_id",
            "source": ""
          }
        ],
        "step": "collect_employee_id"
      }
    ]
  }
}
```

---

## Current Limitation

A parameter can have **only one** `validation` object. It is not currently possible to chain multiple validation rules for a single parameter (e.g., "must match regex AND must exist in backend"). As a workaround:

- Apply the local format check first via `validation.function`.
- Follow the parameter collection node with a dedicated `api_call` node for backend verification.
- Use the API call's `on_error` or `post_conditions` to loop back to re-collection if verification fails.

---

## Related Documents

- [`04-parameter-node.md`](./04-parameter-node.md) — Parameter node structure
- [`ref-copy-params.md`](./ref-copy-params.md) — `copy_params` inside validation API calls
- [`07-error-handling.md`](./07-error-handling.md) — Error handling when validation fails
- [`06-post-conditions.md`](./06-post-conditions.md) — Routing based on validation outcomes