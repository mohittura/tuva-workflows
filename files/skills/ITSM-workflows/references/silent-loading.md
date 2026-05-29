# Silent Loading (`silent_loading`)

## Abstract

The workflow engine can transfer a value from one step to another using `copy_params`, which populates the payload of an outgoing API call. However, there was previously no mechanism to automatically fill a **parameter's value** from an API response, or to auto-populate `prefill_params` in an API call node from a prior response — without asking the user.

**Silent loading** solves this problem. It allows the workflow to pre-fill values from a prior API call's response automatically and silently, and only prompt the user if the value couldn't be found.

---

## How it is different from `copy_params`

While both mechanisms are used for data flow between workflow nodes, they serve fundamentally different purposes and target different parts of the node structure:

| Aspect | `copy_params` | `silent_loading` |
|---|---|---|
| **Primary Purpose** | **Construct API Request Payloads**: Maps values from the workflow state (parameters or prior responses) into the payload of an outgoing API call. | **Pre-fill State & Bypass Prompts**: Populates parameter values or static prefill keys from a prior response without prompting the user. |
| **Destination** | Outgoing API request payload (`api_endpoint` call). | Parameter values (`params.<key>.value`) or node configurations (`prefill_params`). |
| **User Prompts** | **No impact on user prompts**: Parameters must have already been collected/prompted *before* they can be copied. | **Bypasses user prompts**: If the value is loaded successfully, the user is never asked for it. |
| **Data Sources** | Parameter values, API response fields, and `__SOFT_STORAGE__`. | Only the `response` object of a previously executed `api_call` node. |
| **Location in JSON** | Placed inside an `api_call` node (or a parameter validation block). | Placed at the root level of the destination node (`parameter` or `api_call`). |

### Key Conceptual Difference

* **`copy_params` is an exporter**: It says, *"Take these values we have gathered and send them to the API endpoint we are about to call."*
* **`silent_loading` is an importer**: It says, *"Check the results of that previous API call. If the value we need is there, load it into our parameters/prefills immediately so we don't have to ask the user for it."*

---

## When to Use Silent Loading

Silent loading is appropriate when:

1. A parameter's value can be inferred or fetched from a prior API call (e.g., the user's name retrieved from an AD lookup), and you only want to ask the user if the lookup failed.
2. A `prefill_params` key in an API call node needs to be populated from the response of a prior step, without user involvement.
3. You want to avoid redundant user prompts when the system already has the data.

---

## Scopes

Silent loading can be applied in three scenarios:

| Scope | Description |
|---|---|
| **Parameter value** | Set the `value` of a parameter directly from a prior API response. The user is not prompted if the value is successfully loaded. |
| **`prefill_params` in a validation `api_call`** | Auto-fill a static key inside the `api_call` validation block of a parameter node. |
| **`prefill_params` in an API call node** | Auto-fill a static key inside an `api_call` node's `prefill_params` from a prior API response. |

---

## How It Works

- The `silent_loading` payload is placed in the **destination node** — the node where you want the values to be auto-filled.
- The **source** of silent loading is always the `response` field of a prior `api_call` type node.
- Nested fields in the response can be accessed using `$` as the path separator.
- The loading happens **silently** — the agent is not informed of what was loaded, and the user is not prompted for values that were successfully filled.
- If a value cannot be loaded (e.g., the source field is absent or null), the engine falls back to prompting the user normally.

---

## Complete Structure Example

```json
"silent_loading": [
  {
    "mappings": [
      {
        "source_field": "ad_user_details$first_name",
        "destination_param": "first_name"
      },
      {
        "source_field": "ad_user_details$last_name",
        "destination_param": "last_name",
        "set_as": "example_last_name"
      },
      {
        "source_field": "ad_user_details$last_name",
        "set_as": "my_last_name"
      }
    ],
    "step": "fetch_ad_user_details"
  }
]
```

---

## Field Reference

### `step`

- **Type:** String
- **Required:** Yes
- **Purpose:** The name of the `api_call` node whose `response` object is the data source for this silent loading block. Must be a node that has already executed by the time this node runs.
- **Note:** This will always be the type of `api_call` node.

---

### `mappings`

- **Type:** Array of Objects
- **Required:** Yes
- **Purpose:** Defines one or more field mappings from the source response to the destination node.

---

### `source_field`

- **Type:** String
- **Required:** Yes
- **Purpose:** The path to the field within the source step's `response` object. Use `$` as the separator for nested access.

```python
# Example: accessing nested data
response = {
  "ad_user_details": {
    "first_name": "Neel",
    "last_name": "Shah",
    "department": {
      "name": "Engineering"
    }
  }
}

# Accessing first_name:
source_field = "ad_user_details$first_name"

# Accessing department name (nested):
source_field = "ad_user_details$department$name"
```

---

### `destination_param`

- **Type:** String
- **Required:** Conditional (see cases below)
- **Purpose:** The key of the parameter (within `params`) whose `value` should be set. Used when the goal is to fill a parameter value.

---

### `set_as`

- **Type:** String
- **Required:** Conditional (see cases below)
- **Purpose:** The key name to use when setting the value in `prefill_params`. Used when the goal is to populate a `prefill_params` entry.

---

## The Three Mapping Cases

### Case 1: Set a parameter value

```json
"silent_loading": [
  {
    "mappings": [
      {
        "source_field": "ad_user_details$first_name",
        "destination_param": "first_name"
      }
    ],
    "step": "fetch_ad_user_details"
  }
]
```

Reads `first_name` from the `ad_user_details` object in the source step's response, and sets it as the `value` of the `first_name` parameter in the current node. The user will not be prompted for `first_name` if this succeeds.

---

### Case 2: Set a parameter value AND store it in `prefill_params` under a custom key

```json
"silent_loading": [
  {
    "mappings": [
      {
        "source_field": "ad_user_details$last_name",
        "destination_param": "last_name",
        "set_as": "example_last_name"
      }
    ],
    "step": "fetch_ad_user_details"
  }
]
```

Both sets the `value` of the `last_name` parameter and also stores the same value in `prefill_params` under the key `"example_last_name"`. Useful when the same value needs to serve as both a collected parameter and a static payload field.

---

### Case 3: Set a `prefill_params` value only (no parameter involved)

```json
"silent_loading": [
  {
    "mappings": [
      {
        "source_field": "ad_user_details$last_name",
        "set_as": "my_last_name"
      }
    ],
    "step": "fetch_ad_user_details"
  }
]
```

Reads the `last_name` from the `ad_user_details` object in the response of the `fetch_ad_user_details` step, and stores it in the current node's `prefill_params` under the key `"my_last_name"`. Since `destination_param` is not defined, no parameter `value` is set on the node; this mapping is purely used to populate the API request payload silently without prompting the user.

---

## Full Example

**Scenario:** After fetching user details from an Active Directory lookup, silently pre-fill the user's first and last name before prompting for ticket details. Only ask the user if the values weren't found.

```json
"collect_ticket_details": {
  "type": "parameter",
  "silent_loading": [
    {
      "mappings": [
        {
          "source_field": "user_profile$first_name",
          "destination_param": "requester_first_name"
        },
        {
          "source_field": "user_profile$last_name",
          "destination_param": "requester_last_name"
        }
      ],
      "step": "fetch_user_profile_api"
    }
  ],
  "params": {
    "requester_first_name": {
      "value": "",
      "llm_key": "First Name",
      "datatype": "str",
      "description": "The requester's first name.",
      "is_optional": false
    },
    "requester_last_name": {
      "value": "",
      "llm_key": "Last Name",
      "datatype": "str",
      "description": "The requester's last name.",
      "is_optional": false
    },
    "issue_description": {
      "value": "",
      "llm_key": "Issue Description",
      "datatype": "str",
      "description": "A description of the problem being reported.",
      "is_optional": false
    }
  },
  "default_step": "create_ticket_api"
}
```

In this example:
- `requester_first_name` and `requester_last_name` will be silently loaded from `fetch_user_profile_api`'s response.
- The user will only be asked for `issue_description` (and for any names that couldn't be loaded).

---

## Limitations

- **No agent feedback:** Whatever is loaded silently is never reported to the agent. The user will not be informed about what was auto-filled.
- **Source must be an `api_call` node:** Silent loading can only pull from the `response` field of an API call type node. It cannot pull from another parameter node's value.
- **Source node must have already executed:** The source step must appear earlier in the workflow graph.
- **Single level of nesting per mapping:** Each mapping resolves a single path. You cannot transform or combine values; only direct field access is supported.

---

## Related Documents

- [`04-parameter-node.md`](./04-parameter-node.md) — Where `silent_loading` is used in parameter nodes
- [`05-api-call-node.md`](./05-api-call-node.md) — Where `silent_loading` is used in API call nodes
- [`copy-params.md`](./copy-params.md) — The explicit (non-silent) mechanism for passing values between nodes