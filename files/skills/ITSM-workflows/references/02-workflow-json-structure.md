# Workflow JSON Structure

A workflow is stored as a single JSON document in the database. This document contains two sections: the **core metadata** (top-level fields that describe and control the workflow) and the **steps object** (the graph of nodes that define the actual process).

---

## Core Metadata Fields

Each workflow MUST have these metadata fields, using which the workflow remains the unique in the system, helps the agent to find the correct workflow and manage the workflow's lifecycle:

1. `workflow_id`
2. `workflow_name`
3. `workflow_description`
4. `training_text`
5. `executed_steps`
6. `current_step`
7. `is_workflow_ended`
8. `steps`

---

## Detailed understanding of metadata fields

### 1. `workflow_id`

- **Type:** String
- **Required:** Yes
- **Purpose:** Unique identifier for the workflow. Acts as the primary key linking the MongoDB document to its corresponding Milvus vector record.
- **Format:** UUID or any other collision-resistant identifier.
- **Example:** `"122cc5aa48224c06abc7505f0c9c651a"`

---

### 2. `workflow_name`

- **Type:** String
- **Required:** Yes
- **Purpose:** Human-readable name used by the agent to initialize the workflow. This name appears in search results returned to the agent, so it must be descriptive and unambiguous.
- **Best Practice:** Use action-oriented names that clearly describe what the workflow does.
- **Example:** `"Create Incident Ticket"` ✅ — not `"Ticket Process"` ❌

---

### 3. `workflow_description`

- **Type:** String
- **Required:** Yes
- **Purpose:** Natural language description of the workflow's objective. The agent reads this description when deciding whether a workflow matches the user's intent.
- **Best Practice:** Be concise but complete. Cover the primary objective, typical use cases, and any notable constraints.
- **Example:** `"Creates a new incident ticket in the ITSM system for reporting hardware, software, or service issues."`

---

### 4. `training_text`

- **Type:** String
- **Required:** Yes
- **Purpose:** The training_text is used to create the embeddings for the workflow, using which the agent finds the most relevant workflow from the vector database.
- **Content Strategy:**
  - Include natural language phrasings a user might say to trigger this workflow.
  - Cover synonyms, related phrases, and common misspellings.
  - Include the `workflow_description` for contextual grounding.
- **Example:** `"I need to report a problem. My laptop isn't working. Can you raise a ticket? There's an issue with my software. I want to report an incident. Creates a new incident ticket in the ITSM system..."`

---

### 5. `executed_steps`

- **Type:** Array of Strings
- **Required:** Yes
- **Default:** `[]`
- **Purpose:** Tracks which nodes have already been executed in the current workflow instance. Managed automatically by the workflow engine. Initialized as empty.
- **Engine Behavior:** When a node completes, its name is appended to this array. This prevents replaying completed steps and provides an audit trail of the execution path.

---

### 6. `current_step`

- **Type:** String
- **Required:** Yes
- **Purpose:** Points to the node that the workflow engine should execute next. Updated automatically after each step completes.
- **Initial Value:** Typically `"__SOFT_STORAGE__"` (the system's global data cache node) or the name of whichever node should run first. The value of this key will always be there in the `steps` object.
- **Engine Behavior:** After a node executes, the engine evaluates post-conditions and the `default_step` to set the new value.

---

### 7. `is_workflow_ended`

- **Type:** Boolean
- **Required:** Yes
- **Default:** `false`
- **Purpose:** Terminal flag. When `true`, the engine stops processing and considers the workflow complete. No further nodes are executed. Only the workflow engine can change the value of this flag.
- **Set to `true` when:**
  - A node's `default_step` or post-condition `true_step` points to `"<--|end-of-flow|-->"`.
  - The maximum retry count for a node is exceeded.
  - An API response signals explicit termination.

---

### 8. `steps`

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

| Type | Key | Purpose | Reference |
|---|---|---|---|
| **Parameter Node** | `"type": "parameter"` | Collects, validates, and stores user-provided input | [`04-parameter-node.md`](./04-parameter-node.md) |
| **API Call Node** | `"type": "api_call"` | Executes an HTTP request to a backend system | [`05-api-call-node.md`](./05-api-call-node.md) |

In addition, two **special constructs** exist that are not node types but impacts the execution flow:

| Construct | Purpose | Usage |
|---|---|---|
| `__SOFT_STORAGE__` | A special parameter node that acts as a global cross-workflow data cache. It can be used to store and retrieve data across different workflows. | It is a parameter type node, because it holds the values cached during the execution of the workflow. Note that the name will always be `__SOFT_STORAGE__` and it will always be the first node in the `steps` object. |
| `<--\|end-of-flow\|-->` | A terminal marker — not a real node, but used as a `default_step` or `true_step` value to end the workflow execution | It's a terminal marker, therefor, the workflow engine uses this value to determine that the workflow has ended, but there won't be a dedicated step for it in the `steps` object like `__SOFT_STORAGE__`.  |


**Note:** Though parameter and api_call nodes have different purposes, they share some common keys/sub-structure that must exist in any node. For more details about the common keys/sub-structure, see [`03-node-types-and-structure.md`](./03-node-types-and-structure.md). It also contains the detailed understanding of the special nodes `__SOFT_STORAGE__` and `<--|end-of-flow|-->`. 