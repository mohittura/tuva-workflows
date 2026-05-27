# Copy Parameters (`copy_params`)

`copy_params` is the primary mechanism for passing data between nodes in a workflow. It maps values from the workflow's current state — whether from a collected parameter or from a prior API call's response — into the payload of an outgoing API request.

---

## Where It Is Used

`copy_params` can appear in two places:

1. **Inside an `api_call` node** — to populate the request payload of that API call with values from earlier steps.
2. **Inside a `validation.api_call` block within a parameter node** — to populate the request payload of a validation API call with values already collected.

---

## Complete Structure

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "source_field_name",
        "copy_to": "destination_field_name",
        "source": "response"
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
- **Purpose:** Specifies which part of the source node to read from.

| Value | Reads From |
|---|---|
| Omitted / `""` | The parameter's `value` field directly (for parameter nodes) |
| `"response"` | The full `response` object of an API call node |
| `"response.field_name"` | A specific named field within the API call's response |

---

## Practical Examples

### Example 1: Copying a Parameter Value

Copy the collected email address into the API request:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "user_email",
        "copy_to": "email",
        "source": ""
      }
    ],
    "step": "collect_user_details"
  }
]
```

Here, `user_email` is a parameter key in the `collect_user_details` node. Its `.value` is copied to `email` in the outgoing request.

---

### Example 2: Copying from an API Response

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

The `ticket_id` field from `create_parent_ticket_api`'s response object is copied into the new request as `parent_ticket_id`.

---

### Example 3: Copying from Soft Storage

Reuse an authentication token stored in `__SOFT_STORAGE__` from a prior session workflow:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "user_auth_token",
        "copy_to": "auth_token",
        "source": ""
      }
    ],
    "step": "__SOFT_STORAGE__"
  }
]
```

---

### Example 4: Multiple Sources in One Node

Copy from multiple prior nodes in a single `copy_params` array:

```json
"copy_params": [
  {
    "keys": [
      {
        "copy_from": "user_email",
        "copy_to": "requester_email",
        "source": ""
      }
    ],
    "step": "collect_user_details"
  },
  {
    "keys": [
      {
        "copy_from": "ticket_priority",
        "copy_to": "priority",
        "source": ""
      },
      {
        "copy_from": "issue_description",
        "copy_to": "description",
        "source": ""
      }
    ],
    "step": "collect_issue_info"
  }
]
```

---

## Key Rules

- Each object in `copy_params` references **one source node** (`step`), but can map **multiple fields** from it (`keys`).
- Multiple objects in the array allow copying from **multiple source nodes** in one go.
- The `copy_to` key name must match what the backend API expects in its request body.
- `source: "response"` is only valid for `api_call` type nodes. Applying it to a parameter node will fail.
- When reading from `__SOFT_STORAGE__`, the `copy_from` value must match the `set_to` key used when the data was stored via `soft_storage_params`.

---

## Related Documents

- [`04-parameter-node.md`](./04-parameter-node.md) — Parameter collection and value storage
- [`05-api-call-node.md`](./05-api-call-node.md) — API call node and response storage
- [`ref-validation.md`](./ref-validation.md) — `copy_params` inside validation API calls
- [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) — `__SOFT_STORAGE__` reference