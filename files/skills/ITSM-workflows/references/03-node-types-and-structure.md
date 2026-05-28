# Node Types & Structure

All executable logic in a workflow lives inside nodes. The behaviour of the nodes, and how they are connected in the workflow is governs the workflows as a whole.
The node can either contains the detailed instructions of what kind of parameters to collect from the user or what action to make using the API call that can either execute some operations or fetches the information. There are 2 special constructs , one for caching ( `__SOFT_STORAGE__` ) and other for terminating the workflow ( `<--|end-of-flow|-->` ).

---

## Common Node Properties that exist in all nodes:

1. `type`
2. `default_step`
3. `post_conditions`
4. `silent_loading`

Below is the detailed description of all the common node properties:

#### 1. `type`

- **Type:** String Literal
- **Required:** Yes
- **Values:** `"parameter"` or `"api_call"`
- **Purpose:** Determines the fundamental behavior of the node. The workflow engine reads this field first to decide how to process the node. The node type 'parameter' will signal the agent to collect the detailed information from the user, where as the node type 'api_call' will signal the agent to make an API call to a backend system.

---

#### 2. `default_step`

- **Type:** String
- **Required:** Yes
- **Purpose:** Specifies the next node to execute when no post-condition evaluates to `true`. Think of this as the "else" branch — the fallback path when no conditional routing applies.
- **Values:** Any other node name in the `steps` object, or `"<--|end-of-flow|-->"` to terminate the workflow.

---

#### 3. `post_conditions`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Defines conditional branching logic evaluated after the node executes. If a condition matches, the workflow routes to the `true_step` rather than the `default_step`.
- **Evaluation Order:** Conditions are checked in array order. The first one that evaluates to `true` wins.

> For the full post-condition structure and all supported operators and functions, see [`06-post-conditions.md`](./06-post-conditions.md).

---

#### 4. `silent_loading`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Silently loads the value of a parameter from the previous node's response or from the soft storage in case if it exists in a parameter typed node. If it exists in the api_call typed node, it will populate the `prefill_param` object, used for the api call. 

> For the full silent_loading structure and all examples, see [`silent-loading.md`](./silent-loading.md).


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

This is a **terminal marker**, not an actual node. It doesn't exist as a key in the `steps` object like other nodes including `__SOFT_STORAGE__`. It signals to the workflow engine that execution should stop and the workflow should be marked as complete (`is_workflow_ended = true`).

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

| Node Type | `type` Value | Primary Role | Key Properties | When to use |
|---|---|---|---|---|
| Parameter Node | `"parameter"` | Collect and validate user input | `params`, `post_conditions`, `default_step` | To collect input parameters from the user |
| API Call Node | `"api_call"` | Execute backend HTTP requests | `api_endpoint`, `copy_params`, `on_error`, `default_step` | To execute backend HTTP requests |
| Soft Storage *(special)* | `"parameter"` | Cross-workflow session cache | `params` (empty initially, auto-managed) | To cache data across workflows |
| End of Flow *(terminal marker)* | — | Terminate the workflow | Used as a step reference, not a node itself | To terminate the workflow |

---

## Detailed References

Each node type has its own dedicated document covering the full property specification, structure examples, and design guidance:

- **Parameter Nodes** → [`04-parameter-node.md`](./04-parameter-node.md)
  Covers all the different keys required to define the type, the usage, the need, the default values, the validation logic of a specific parameter including the retry logic, or the routing conditions for the next node based on the validation or the values of the collected parameter.

- **API Call Nodes** → [`05-api-call-node.md`](./05-api-call-node.md)
  Covers all the different keys required to define the API endpoint, values to include in the api call from prevoiusly executed steps, and the routing conditions of the next node using the response received from the api call.