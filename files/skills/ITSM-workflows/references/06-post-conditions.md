# Post-Conditions

Post-conditions are the flow control mechanism of the workflow graph. After a node (parameter or API call) finishes executing, the engine evaluates the node's `post_conditions` array to decide which node to visit next. If no condition matches, the engine falls back to the `default_step`.

Think of post-conditions as a chain of **if / else-if** branches, with `default_step` acting as the final **else**.

---

## How Evaluation Works

1. After a node executes, its `post_conditions` array is evaluated in order.
2. For each post-condition object, all conditions in its `conditions` array are evaluated together using the `logical_operator`.
3. The **first** post-condition whose conditions evaluate to `true` wins — the engine routes to its `true_step`.
4. If **no** post-condition evaluates to `true`, the engine uses the node's `default_step`.

---

## Complete Structure

```json
"post_conditions": [
  {
    "logical_operator": "and",
    "conditions": [
      {
        "key": "status",
        "step": "previous_api_call",
        "source": "response",
        "function": "",
        "condition_key": "",
        "condition_source": "",
        "condition_step": "",
        "criteria": "success",
        "operator": "==",
        "start": "",
        "end": ""
      },
      {
        "key": "ticket_count",
        "step": "previous_api_call",
        "source": "response.count",
        "function": "len",
        "criteria": 5,
        "operator": ">"
      }
    ],
    "true_step": "handle_multiple_tickets"
  }
]
```

---

## Post-Condition Object Properties

### `logical_operator`

- **Type:** String Literal
- **Values:** `"and"`, `"or"`, or `""` (empty string)
- **Purpose:** Defines how multiple conditions within this post-condition object are combined.
  - `"and"` — all conditions must be true
  - `"or"` — at least one condition must be true
  - `""` — use when there is only a single condition (no combination needed)
- **Current Limitation:** A maximum of **two conditions** is supported when using `"and"` or `"or"`. Nested logic is not currently supported.

---

### `conditions`

An array of one or two condition objects. Each condition object evaluates a single value from the workflow state.

---

### `true_step`

- **Type:** String
- **Required:** Yes (within each post-condition object)
- **Purpose:** The node to route to if all conditions in this post-condition evaluate to `true`.
- **Values:** Any node name in `steps`, or `"<--|end-of-flow|-->"` to terminate the workflow.

---

## Condition Object Properties

### `key`

- **Type:** String
- **Required:** Yes
- **Purpose:** The name of the field to evaluate. This corresponds to either a parameter key or a response field from an API call, depending on the `source`.

---

### `step`

- **Type:** String
- **Required:** Yes
- **Purpose:** The name of the node whose data contains the value being evaluated. Used together with `source` to locate the exact value.

---

### `source`

- **Type:** String
- **Required:** No
- **Purpose:** Specifies where within the referenced `step` to find the value.

| Value | Meaning |
|---|---|
| Omitted / `""` | Read the value directly from the parameter (`params[key].value`) |
| `"response"` | Read from the full API response object of the step |
| `"response.field_name"` | Read a specific field from within the API response |

---

### `function`

- **Type:** String Literal
- **Required:** No
- **Purpose:** Applies a transformation to the value before comparing it to `criteria`. If omitted, the raw value is compared directly.

| Function | Description |
|---|---|
| `"len"` | Get the length of a string or list before comparing |
| `"range"` | Check if the value falls between `start` and `end` (inclusive) |
| `"regex"` | Match the value against the regex pattern in `criteria` |
| `"is_empty"` | Check if the value is empty (string `""`, list `[]`, or `null`) |
| `"is_not_empty"` | Inverse of `is_empty` |
| `"is_none"` | Check if the value is `null` |
| `"is_not_none"` | Inverse of `is_none` |
| `"is_subset"` | Check if all elements of the value list appear in the `criteria` list |
| `"is_date_time_format_valid"` | Validate that the value is a parseable date/time string |

---

### `criteria`

- **Type:** Varies (string, number, list — depends on `operator`)
- **Required:** Required unless using dynamic comparison via `condition_key`
- **Purpose:** The static value to compare the field against.

---

### `operator`

- **Type:** String Literal
- **Required:** Yes
- **Purpose:** Defines the comparison between the field value (optionally transformed by `function`) and `criteria`.

| Operator | Description |
|---|---|
| `"=="` | Equal to |
| `"!="` | Not equal to |
| `">"` | Greater than |
| `"<"` | Less than |
| `">="` | Greater than or equal to |
| `"<="` | Less than or equal to |
| `"in"` | Value exists within the `criteria` list |
| `"not in"` | Value does not exist in the `criteria` list |

---

### `condition_key`, `condition_step`, `condition_source`

- **Type:** String
- **Required:** No (alternative to `criteria`)
- **Purpose:** Instead of comparing against a static `criteria` value, these three fields identify a **dynamic value from another node** to compare against at runtime.

| Field | Purpose |
|---|---|
| `condition_key` | The parameter or response field name to read from |
| `condition_step` | The node that contains the comparison value |
| `condition_source` | Where to find it within that node (`""`, `"response"`, `"response.field"`) |

Use dynamic comparison when the threshold or expected value is not known at design time — for example, checking whether the user's selected value matches what was returned by a prior API call.

---

### `start` and `end`

- **Type:** String or Number
- **Required:** Only when `function` is `"range"`
- **Purpose:** Define the inclusive lower and upper bounds of the numeric range check.
- **Example:** `"start": 1, "end": 100` with `"operator": "=="` checks if the value is within `[1, 100]`.

---

## Example: Branching on API Response

```json
"post_conditions": [
  {
    "logical_operator": "",
    "conditions": [
      {
        "key": "error_code",
        "step": "create_ticket_api",
        "source": "response",
        "criteria": 200,
        "operator": "=="
      }
    ],
    "true_step": "confirm_success"
  },
  {
    "logical_operator": "",
    "conditions": [
      {
        "key": "error_code",
        "step": "create_ticket_api",
        "source": "response",
        "criteria": 701,
        "operator": "=="
      }
    ],
    "true_step": "collect_issue_details"
  }
],
"default_step": "handle_unexpected_error"
```

In this example:
- If the API returned `200`, route to `confirm_success`.
- If the API returned `701` (validation error), loop back to `collect_issue_details`.
- Any other outcome falls to `handle_unexpected_error`.