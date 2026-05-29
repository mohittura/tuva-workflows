# Copy Parameters (`copy_params`)

`copy_params` is used to import parameters from previously executed steps into the request payload of the current step. They are used in `api_call` nodes as well as in the `api_call`-based validation blocks of parameter nodes. Therefore, they are fully utilized in all API execution nodes and processes.

## Conceptual Model (`m * n` Mapping)

The previously executed `m` steps are mapped to `n` parameters/values to populate the request payload of the current step. In total, the workflow engine can import up to `m * n` key-value pairs.
- **`m`** represents the number of distinct source steps we are reading data from.
- **`n`** represents the number of specific values/keys we are importing from a given source step.

For example, if we have `m = 2` source steps and want to import `n = 3` values from each of them, `copy_params` will map and populate `2 * 3 = 6` key-value pairs in the outgoing request payload.

---

## Where It Is Used

`copy_params` appears in two places:
1. **Inside an `api_call` node** — to populate the request payload of that API call with values from earlier steps.
2. **Inside a validation based on `api_call` for parameter** — to populate the request payload of a validation API call with values already collected.

---

## Structure

The configuration format allows importing `n` values from a single step, repeated for all `m` source steps:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "source_field_name",
        "copy_to": "destination_field_name",
        "source": "response" // Only when the step is pointing to an api_call type node
      }
    ],
    "step": "source_node_name"
  }
]
```

`copy_params` is an array. Each object in the array targets a single source node (`step`) and maps one or more fields from that node into the request payload.

---

## Field Reference

### `step`

- **Type:** String
- **Required:** Yes
- **Purpose:** The name of the node from which to read the value. Can be any node in `steps`, including `__SOFT_STORAGE__`.
- **Examples:** `"collect_user_email"`, `"fetch_departments"`, `"__SOFT_STORAGE__"`

---

### `keys`

- **Type:** Array of Objects
- **Required:** Yes
- **Purpose:** Defines one or more field mappings from the source node to the API request payload.

---

### `copy_from`

- **Type:** String
- **Required:** Yes
- **Purpose:** The name of the field to read from the source node. For parameter nodes, this is the parameter key. For API call nodes, this is the response field name (when combined with the appropriate `source`).

---

### `copy_to`

- **Type:** String
- **Required:** Yes
- **Purpose:** The key name to use in the outgoing API request payload. This is the field name the backend API expects.

---

### `source`

- **Type:** String
- **Required:** No
- **Purpose:** Specifies which part of the source node to read from, only used when `step` points to an `api_call` type node.

| Value | Reads From |
|---|---|
| Omitted / `""` | The parameter's `value` field directly (for parameter nodes) |
| `"response"` | The full `response` object of an API call node |
| `"response.field_name"` | A specific named field within the API call's response |

---

## Practical Examples

### Example 1: Importing `n = 1` Value from `m = 1` Step (Parameter Node)

Copy the collected email address into the API request:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "user_email",
        "copy_to": "email"
      }
    ],
    "step": "collect_user_details"
  }
]
```
Here, we read the parameter value `user_email` from the parameter node `collect_user_details` and map it to `email` in the outgoing request payload. Since the source is a parameter node, the `source` property is omitted.

### Example 2: Importing `n = 1` Value from `m = 1` Step (API Response)

Use a field returned by a prior API call:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "ticket_id",
        "copy_to": "parent_ticket_id",
        "source": "response"
      }
    ],
    "step": "create_parent_ticket_api"
  }
]
```
Here, the `ticket_id` field from the API response of `create_parent_ticket_api` is mapped to `parent_ticket_id`. Since the source is an API call, `source` is set to `"response"`.

### Example 3: Importing from Multiple Steps (`m = 2`, `n = 1` and `n = 2`)

Importing from multiple steps in a single `copy_params` array:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "user_email",
        "copy_to": "requester_email"
      }
    ],
    "step": "collect_user_details"
  },
  {
    "keys": [
      {
        "copy_from": "ticket_priority",
        "copy_to": "priority"
      },
      {
        "copy_from": "issue_description",
        "copy_to": "description"
      }
    ],
    "step": "collect_issue_info"
  }
]
```
In this configuration, we import:
1. `n = 1` parameter value (`user_email`) from the first step `collect_user_details`.
2. `n = 2` parameter values (`ticket_priority`, `issue_description`) from the second step `collect_issue_info`.
In total, `3` key-value pairs are imported.

---

## Key Rules
- **Mapping Array Size**: Each object inside `copy_params` represents a single source step. If you need to import values from multiple steps, declare multiple mapping objects in the `copy_params` array.
- **Node Type Rule**: Always verify the type of the source `step`. If it is an `api_call` node, `"source": "response"` is required. If it is a `parameter` node or `__SOFT_STORAGE__`, the `source` field must be omitted.
- **Key Matching**: The `copy_to` key must match the exact parameter name expected by the target API endpoint.

---

## Related Documents

- [`04-parameter-node.md`](./04-parameter-node.md) — Parameter collection and value storage
- [`05-api-call-node.md`](./05-api-call-node.md) — API call node and response storage
- [`parameter-validation.md`](./parameter-validation.md) — Using `copy_params` inside validation API calls
- [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) — `__SOFT_STORAGE__` reference