---
name: ITSM-workflows
description: "Build, validate, and audit Tuva ITSM workflow JSON definitions — the directed cyclic graph structures that power agentic automation in the Tuva ITSM system. Use this skill any time the user wants to CREATE a new workflow, EDIT an existing workflow JSON, REVIEW a workflow for correctness, DEBUG a workflow that isn't executing properly, or understand any part of the Tuva workflow schema (nodes, post-conditions, soft storage, error handling, etc.). Trigger on phrases like: 'create a workflow', 'write the workflow JSON', 'build a workflow for', 'add a step to my workflow', 'validate this workflow', 'why isn't my workflow working', 'explain this workflow', 'what should the JSON look like', or any reference to workflow nodes, parameter steps, api_call steps, post_conditions, soft_storage, copy_params, or training_text. Always use this skill when the user is working with Tuva ITSM workflow definitions."
---

# Tuva ITSM Workflows
 
You are an expert author and reviewer of Tuva ITSM workflow JSON definitions.
 
---
 
## ⚠️  AUTHORITATIVE REFERENCES — READ BEFORE WRITING ANY JSON
 
Two files in this skill are the ground truth. Consult them before generating or validating
any workflow. No assumption, pattern, or convention takes precedence over these documents.
 
| File | What it is |
|------|-----------|
| `references/spec.md` | The complete official specification. Every field, every rule, every constraint. |
| `references/examples/create_zendesk_ticket.json` | A real production workflow. This is the gold standard for JSON structure and conventions. When in doubt, match this file's style exactly. |
 
**Rule:** If anything in this SKILL.md conflicts with `references/spec.md` or
`references/examples/create_zendesk_ticket.json`, the spec and example win.
 
---
 
## Core Mental Model
 
A workflow is a **Directed Cyclic Graph (DCG)** of nodes. The AI agent:
1. **Discovers** the workflow via semantic search on `training_text`
2. **Initializes** it (loads the JSON, sets `current_step`)
3. **Drives** it to completion by iteratively calling "Submit Information"
Two node types exist:
- **`parameter`** — Collects user input, stores it, optionally validates it
- **`api_call`** — Calls an external API, routes on results, stores response data
The engine loops: execute `current_step` → evaluate `post_conditions` → move to `default_step`
(or a `true_step`) → repeat until `<--|end-of-flow|-->`.
 
---
 
## Step-by-Step Workflow Creation Process
 
### Step 1 — Understand the Business Process
Before writing JSON, clarify:
- What data must be collected from the user?
- What API calls must be made, and in what order?
- What can go wrong, and how should each error be handled?
- Is any data shared with or from other workflows (soft storage)?
- Is the user potentially already authenticated (soft storage session check)?
### Step 2 — Design the Graph First
Sketch the node sequence before writing JSON:
```
__SOFT_STORAGE__ [check auth?] → collect_info → api_call → end / error_node
```
Identify all branching points, retry loops, and terminal paths.
 
### Step 3 — Write the Metadata Section
```json
{
  "workflow_id": "<uuid>",
  "workflow_name": "<Action-Oriented Name>",
  "workflow_description": "<concise description>",
  "training_text": "<25+ natural language query phrasings>",
  "executed_steps": [],
  "current_step": "__SOFT_STORAGE__",
  "is_workflow_ended": false,
  "steps": { ... }
}
```
 
### Step 4 — Write Each Node
Follow the exact field order and structure shown in `references/examples/create_zendesk_ticket.json`.
 
### Step 5 — Wire Post-Conditions
Add `post_conditions` to any node that needs conditional branching.
 
### Step 6 — Validate Against the Checklist
Run through the full **Pre-Flight Checklist** below before presenting the workflow.
 
---
 
## Verified Production Patterns
 
These patterns are extracted directly from `references/examples/create_zendesk_ticket.json`.
They override any earlier assumptions.
 
### 1. `inputs: {}` is REQUIRED on every api_call node
 
Every `api_call` node must have `"inputs": {}` as a field. This field is always empty `{}`.
It is NOT documented in the spec but IS present in every production api_call node.
 
```json
"my_api_node": {
  "type": "api_call",
  "inputs": {},
  "response": {},
  "api_endpoint": "service/operation",
  ...
}
```
 
### 2. Node naming convention with `|` separator
 
When a node collects multiple related items, use `|` as a separator in the name:
```
"collect_user_name_|_email"
"get_ticket_type_|_priority"
"collect_subject_|_comment_|_group_name_|_priority_|_type"
```
This is a production convention — use it for multi-param collection nodes.
 
### 3. `__SOFT_STORAGE__` can and should have `post_conditions`
 
Soft storage is NOT just a passive cache. It can route based on prior session state.
The Zendesk workflow uses it to skip authentication if the user is already authenticated:
 
```json
"__SOFT_STORAGE__": {
  "type": "parameter",
  "params": {},
  "post_conditions": [
    {
      "logical_operator": "",
      "conditions": [
        {
          "key": "is_user_authenticated",
          "step": "__SOFT_STORAGE__",
          "criteria": true,
          "operator": "=="
        }
      ],
      "true_step": "verify_user_role"
    }
  ],
  "default_step": "collect_user_name_|_email"
}
```
Always consider: should this workflow skip steps if the user is already authenticated?
 
### 4. `set_available_options.set_from` is the bare field name — NOT `response.field`
 
Wrong (what the spec example shows):
```json
{ "set_from": "response.departments", ... }
```
Correct (what production uses):
```json
{ "set_from": "ticket_types", ... }
{ "set_from": "priority_options", ... }
{ "set_from": "groups", ... }
```
`set_from` is just the field name from the API response object — no `response.` prefix.
 
### 5. `soft_storage_params` without `source` copies from a parameter node's value
 
When persisting data from a **parameter node** (not an API response) to soft storage,
omit the `source` field entirely:
 
```json
"soft_storage_params": [
  {
    "keys": [
      {
        "get_from": "is_user_authenticated",
        "set_to": "is_user_authenticated",
        "source": "response"
      }
    ],
    "step": "validate_otp"
  },
  {
    "keys": [
      {
        "get_from": "user_email",
        "set_to": "user_email"
      }
    ],
    "step": "collect_user_name_|_email"
  }
]
```
- With `source: "response"` → reading from the node's API response
- Without `source` → reading from the node's parameter value directly
### 6. Validation can use dynamic references without `function` or `criteria`
 
When validating against values returned by an API call, use only the dynamic reference fields:
 
```json
"validation": {
  "condition_step": "get_groups",
  "condition_key": "groups",
  "condition_source": "response",
  "operator": "in"
}
```
No `function`, no `criteria` needed — the dynamic reference IS the validation target.
Compare this to static regex validation which DOES use `function` and `criteria`:
```json
"validation": {
  "function": "regex",
  "criteria": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
}
```
 
### 7. `retry_count` belongs on api_call nodes too, not only parameter nodes
 
The `validate_otp` api_call node has `"retry_count": 3` at the node level.
Use this on any API call that should be retried on transient failure.
 
### 8. `on_error` can route directly to `<--|end-of-flow|-->`
 
Not every error needs a dedicated error node. Routing directly to end-of-flow is valid
and common for unrecoverable errors:
```json
"on_error": {
  "500": "<--|end-of-flow|-->",
  "708": "<--|end-of-flow|-->"
}
```
 
### 9. Do NOT include `_id` in authored workflows
 
The `_id: { "$oid": "..." }` field is added by MongoDB at insert time.
Never include it in the JSON you write.
 
---
 
## Quick Reference: Node Skeletons
 
### `__SOFT_STORAGE__` (with session-aware routing)
```json
"__SOFT_STORAGE__": {
  "type": "parameter",
  "params": {},
  "post_conditions": [
    {
      "logical_operator": "",
      "conditions": [
        {
          "key": "is_user_authenticated",
          "step": "__SOFT_STORAGE__",
          "criteria": true,
          "operator": "=="
        }
      ],
      "true_step": "first_step_after_auth"
    }
  ],
  "default_step": "collect_user_email"
}
```
 
### Parameter Node (with dynamic validation)
```json
"collect_subject_|_comment_|_priority": {
  "type": "parameter",
  "params": {
    "subject": {
      "value": "",
      "llm_key": "Subject",
      "description": "Brief summary of the issue.",
      "datatype": "str",
      "validation": {},
      "available_options": [],
      "is_optional": false
    },
    "priority": {
      "value": "",
      "llm_key": "Priority",
      "description": "Urgency level of the ticket.",
      "datatype": "str",
      "validation": {
        "condition_step": "get_priority_options",
        "condition_key": "priority_options",
        "condition_source": "response",
        "operator": "in"
      },
      "available_options": [],
      "is_optional": false,
      "retry_count": 3
    }
  },
  "default_step": "create_ticket"
}
```
 
### API Call Node (full production structure)
```json
"create_ticket": {
  "type": "api_call",
  "inputs": {},
  "response": {},
  "api_endpoint": "zendesk/ticket-management",
  "prefill_params": {
    "routing_key": "create_ticket"
  },
  "copy_params": [
    {
      "keys": [
        { "copy_from": "subject", "copy_to": "subject" },
        { "copy_from": "priority", "copy_to": "priority" }
      ],
      "step": "collect_subject_|_comment_|_priority"
    },
    {
      "keys": [
        { "copy_from": "user_email", "copy_to": "requester_email" }
      ],
      "step": "collect_user_name_|_email"
    }
  ],
  "on_error": {
    "500": "<--|end-of-flow|-->",
    "708": "<--|end-of-flow|-->"
  },
  "default_step": "<--|end-of-flow|-->"
}
```
 
### API Call Node (with set_available_options — correct format)
```json
"get_ticket_type_|_priority": {
  "type": "api_call",
  "inputs": {},
  "response": {},
  "api_endpoint": "zendesk/ticket-management",
  "prefill_params": {
    "routing_key": "get_ticket_fields"
  },
  "set_available_options": [
    {
      "set_from": "ticket_types",
      "set_to": "type",
      "set_step": "collect_subject_|_comment_|_priority"
    },
    {
      "set_from": "priority_options",
      "set_to": "priority",
      "set_step": "collect_subject_|_comment_|_priority"
    }
  ],
  "on_error": {
    "500": "<--|end-of-flow|-->"
  },
  "default_step": "collect_subject_|_comment_|_priority"
}
```
 
---
 
## Pre-Flight Validation Checklist
 
### Metadata
- [ ] `workflow_id` is present (UUID, no hyphens preferred)
- [ ] `workflow_name` starts with an action verb ("Create", "Fetch", "Reset", etc.)
- [ ] `workflow_description` describes objective and use cases clearly
- [ ] `training_text` has 20+ natural language phrasings (see Zendesk example for density)
- [ ] `executed_steps` is `[]`
- [ ] `current_step` is `"__SOFT_STORAGE__"`
- [ ] `is_workflow_ended` is `false`
- [ ] No `_id` field present
### Structural Integrity
- [ ] `__SOFT_STORAGE__` is defined in `steps` with `params: {}`
- [ ] Every `default_step` references a valid node or `"<--|end-of-flow|-->"`
- [ ] Every `true_step` in post_conditions references a valid node or end-of-flow marker
- [ ] Every `on_error` code maps to a valid node or `"<--|end-of-flow|-->"`
- [ ] No orphan nodes (all nodes reachable from `current_step`)
- [ ] At least one path reaches `"<--|end-of-flow|-->"`
### Parameter Nodes
- [ ] Every parameter has: `value: ""`, `llm_key`, `description`, `datatype`, `validation`, `available_options`, `is_optional`
- [ ] `value` is always `""`
- [ ] `available_options` is `[]` when dynamically populated
- [ ] `retry_count` is set for any parameter with a non-empty `validation`
- [ ] Dynamic validation uses `condition_step` + `condition_key` + `condition_source` + `operator` (no `function` or `criteria`)
- [ ] Static validation uses `function` + `criteria` (regex, len, range, etc.)
### API Call Nodes
- [ ] `inputs: {}` is present on every api_call node
- [ ] `response: {}` is present on every api_call node
- [ ] `api_endpoint` is a path only — no protocol prefix
- [ ] `set_available_options.set_from` is the bare field name (NOT `response.field_name`)
- [ ] `soft_storage_params` key has `source: "response"` when reading from API response
- [ ] `soft_storage_params` key has NO `source` when reading from a parameter node's value
- [ ] `on_error` is defined for all expected error scenarios
- [ ] `retry_count` is set on nodes with transient failure risk
### Post-Conditions
- [ ] `logical_operator` is `"and"`, `"or"`, or `""`
- [ ] Max 2 conditions when using `logical_operator`
- [ ] Each condition has `key`, `step`, `operator`
- [ ] `source` is `"response"` or `"response.field_name"` when reading from API response
- [ ] `source` is omitted when reading from parameter value
---
 
## Reference Files
 
| File | When to Read |
|------|-------------|
| `references/spec.md` | **Always** — the authoritative specification for every field and rule |
| `references/examples/*` | **When Reviewing** — the gold standard production workflow; match these styles based on the needs |
| `references/field-reference.md` | Full property specs and corrected field details |
| `references/patterns.md` | Advanced patterns: dynamic options, cross-workflow sharing, retry loops |
| `references/error-codes.md` | Standard error codes and routing guidance |
 
