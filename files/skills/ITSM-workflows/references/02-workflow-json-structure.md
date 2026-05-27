# Workflow JSON Structure

A workflow is stored as a single JSON document in MongoDB. This document contains two sections: the **core metadata** (top-level fields that describe and control the workflow) and the **steps object** (the graph of nodes that define the actual process).

---

## Core Metadata Fields

### `workflow_id`

- **Type:** String
- **Required:** Yes
- **Purpose:** Unique identifier for the workflow. Acts as the primary key linking the MongoDB document to its corresponding Milvus vector record.
- **Format:** UUID or any other collision-resistant identifier.
- **Example:** `"122cc5aa48224c06abc7505f0c9c651a"`

---

### `workflow_name`

- **Type:** String
- **Required:** Yes
- **Purpose:** Human-readable name used by the agent to initialize the workflow. This name appears in search results returned to the agent, so it must be descriptive and unambiguous.
- **Best Practice:** Use action-oriented names that clearly describe what the workflow does.
- **Example:** `"Create Incident Ticket"` ✅ — not `"Ticket Process"` ❌

---

### `workflow_description`

- **Type:** String
- **Required:** Yes
- **Purpose:** Natural language description of the workflow's objective. The agent reads this description when deciding whether a workflow matches the user's intent.
- **Best Practice:** Be concise but complete. Cover the primary objective, typical use cases, and any notable constraints.
- **Example:** `"Creates a new incident ticket in the ITSM system for reporting hardware, software, or service issues."`

---

### `training_text`

- **Type:** String
- **Required:** Yes
- **Purpose:** The text corpus vectorized and stored in Milvus for semantic search. This is what the discovery system matches against when a user makes a request.
- **Content Strategy:**
  - Include natural language phrasings a user might say to trigger this workflow.
  - Cover synonyms, related phrases, and common misspellings.
  - Include the `workflow_description` for contextual grounding.
- **Example:** `"I need to report a problem. My laptop isn't working. Can you raise a ticket? There's an issue with my software. I want to report an incident. Creates a new incident ticket in the ITSM system..."`

---

### `executed_steps`

- **Type:** Array of Strings
- **Required:** Yes
- **Default:** `[]`
- **Purpose:** Tracks which nodes have already been executed in the current workflow instance. Managed automatically by the workflow engine.
- **Engine Behavior:** When a node completes, its name is appended to this array. This prevents replaying completed steps and provides an audit trail of the execution path.

---

### `current_step`

- **Type:** String
- **Required:** Yes
- **Purpose:** Points to the node that the workflow engine should execute next. Updated automatically after each step completes.
- **Initial Value:** Typically `"__SOFT_STORAGE__"` (the system's global data cache node) or the name of whichever node should run first.
- **Engine Behavior:** After a node executes, the engine evaluates post-conditions and the `default_step` to set the new value.

---

### `is_workflow_ended`

- **Type:** Boolean
- **Required:** Yes
- **Default:** `false`
- **Purpose:** Terminal flag. When `true`, the engine stops processing and considers the workflow complete. No further nodes are executed.
- **Set to `true` when:**
  - A node's `default_step` or post-condition `true_step` points to `"<--|end-of-flow|-->"`.
  - The maximum retry count for a node is exceeded.
  - An API response signals explicit termination.

---

### `steps`

- **Type:** Object (key-value map)
- **Required:** Yes
- **Purpose:** Contains every node in the workflow graph. Each key is a unique node name; each value is a node definition object.

```json
"steps": {
  "node_name_1": { /* node definition */ },
  "node_name_2": { /* node definition */ },
  "node_name_3": { /* node definition */ }
}
```

The node names are referenced throughout the workflow — in `current_step`, `executed_steps`, `default_step`, `true_step`, and `copy_params` — so they must be stable and descriptive.

---

## Minimal Workflow Example

```json
{
  "workflow_id": "122cc5aa48224c06abc7505f0c9c651a",
  "workflow_name": "Create Incident Ticket",
  "workflow_description": "Creates a new incident ticket in the ITSM system.",
  "training_text": "I need to report a problem. My laptop isn't working. Raise a ticket...",
  "executed_steps": [],
  "current_step": "__SOFT_STORAGE__",
  "is_workflow_ended": false,
  "steps": {
    "__SOFT_STORAGE__": { ... },
    "collect_issue_details": { ... },
    "create_ticket_api": { ... }
  }
}
```

---

## Node Types Overview

The `steps` object is composed of nodes, each of which belongs to one of two fundamental types:

| Type | Key | Purpose |
|---|---|---|
| **Parameter Node** | `"type": "parameter"` | Collects, validates, and stores user-provided input |
| **API Call Node** | `"type": "api_call"` | Executes an HTTP request to a backend system |

In addition, two **special constructs** exist that are not node types but control execution flow:

| Construct | Purpose |
|---|---|
| `__SOFT_STORAGE__` | A special parameter node that acts as a global cross-workflow data cache |
| `<--|end-of-flow|-->` | A terminal marker — not a real node, but used as a `default_step` or `true_step` value to end the workflow |

> For the full structure and properties of each node type, see:
> - [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) — common node properties and special constructs
> - [`04-parameter-node.md`](./04-parameter-node.md) — parameter node reference
> - [`05-api-call-node.md`](./05-api-call-node.md) — API call node reference