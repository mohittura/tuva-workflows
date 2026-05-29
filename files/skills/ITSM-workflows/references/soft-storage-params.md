# soft_storage_params

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Persists data from this node's execution into the global soft storage for cross-workflow access.

## Where it is used 
It is defined within individual workflow nodes (either `api_call` nodes or `parameter` nodes) that generate or collect data that needs to be preserved. 
It writes values to `__SOFT_STORAGE__` immediately after the parent node executes successfully. Once stored, these parameters can be read by other nodes using `copy_params` or evaluated in `post_conditions`.

## Why do we need it?

Workflows are generally isolated and their local states are destroyed upon completion. `soft_storage_params` solves this by acting as a "write" channel to the persistent session memory. By caching information like authentication tokens, user email addresses, or user roles, we avoid prompting the user repeatedly for the same information during their session, enabling a seamless and conversational user experience.

## Structure
```json
"soft_storage_params": [
  {
    "keys": [
      {
        "get_from": "source_field_name",
        "set_to": "storage_key_name",
        "source": "response"
      }
    ],
    "step": "current_node_name"
  }
]
```
An entry in the `soft_storage_params` array contains:
- **`step`**: The name of the current node containing the `soft_storage_params` block (self-reference).
- **`keys`**: A mapping array defining what to extract and where to store it:
  - **`get_from`**: The name of the field to read from the current step (either a response field name or a parameter key name).
  - **`set_to`**: The key name under which this value will be saved in the global `__SOFT_STORAGE__` cache.
  - **`source`**: Indicates the data source type. Use `"response"` when storing data from an `api_call` response. Omit this field (or do not include it) when storing a value from a `parameter` node.



## Example

### Case 1: Storing from an API Response (e.g., saving an auth token)
```json
"authenticate_user_api": {
  "type": "api_call",
  "api_endpoint": "auth/login",
  "inputs": {},
  "response": {},
  "soft_storage_params": [
    {
      "keys": [
        {
          "get_from": "token",
          "set_to": "user_auth_token",
          "source": "response"
        }
      ],
      "step": "authenticate_user_api"
    }
  ],
  "default_step": "<--|end-of-flow|-->"
}
```

### Case 2: Storing from a User Parameter (e.g., saving a user email)
```json
"collect_user_email": {
  "type": "parameter",
  "params": {
    "email_address": {
      "value": "",
      "llm_key": "Email Address",
      "datatype": "str",
      "description": "User corporate email",
      "is_optional": false
    }
  },
  "soft_storage_params": [
    {
      "keys": [
        {
          "get_from": "email_address",
          "set_to": "session_email"
        }
      ],
      "step": "collect_user_email"
    }
  ],
  "default_step": "<--|end-of-flow|-->"
}
```

## Key Rules
- **Source Field Usage**: Always set `"source": "response"` when extracting values from the response payload of an `api_call` node. Omit the `"source"` field entirely when extracting values from a `parameter` node.
- **Self-Referential Step Name**: The `"step"` parameter inside the mapping object must always match the name of the node in which the `soft_storage_params` is declared.
- **Valid Cache Keys**: Ensure that the `"set_to"` name is unique and descriptive, as this key will be used to retrieve the value in downstream nodes (via `copy_params` or `post_conditions` targeting `"step": "__SOFT_STORAGE__"`).