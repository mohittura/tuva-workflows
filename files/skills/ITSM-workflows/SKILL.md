---
name: ITSM-workflows
description: Contains the detailed understanding of all the components of the ITSM workflow JSON structure which must be used when the task involves creating new workflows, updating, editing, or debugging the existing workflows.
---

# ITSM Workflow JSON Structure

This skill enables the agent to understand the complex JSON structure of the ITSM workflows. ITSM workflows are defined as JSON objects with specific fields and nested structures that dictate how the workflow operates. This document provides a comprehensive reference to the key components of the workflow JSON, including special nodes like `__SOFT_STORAGE__` and terminal markers like `<--|end-of-flow|-->`, as well as an overview of node types and their properties. The JSON defines *what* the agent does — parameter collection, API calls, conditional routing, error handling — while the agent handles conversation and decision-making.

---

## Mandatory Pre-Reading

Before generating or modifying any workflow, read these two documents in full:

1. **`references/08-best-practices.md`** — Design principles, naming conventions, validation strategy, performance rules.
2. **`references/01-what-is-a-workflow.md`** — System architecture, execution loop, agent-workflow communication, state model.

These are non-negotiable. Skip them and the workflow will have structural or behavioral defects.

---

## References Usage Matrix

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `references/01-what-is-a-workflow.md` | System architecture, execution loop, discovery model | **Always** — read before starting any workflow task |
| `references/02-workflow-json-structure.md` | Top-level metadata fields and `steps` object schema | When writing the workflow skeleton and metadata |
| `references/03-node-types-and-structure.md` | Common node properties, `__SOFT_STORAGE__`, `<--|end-of-flow|-->` | When designing the node graph and special constructs |
| `references/04-parameter-node.md` | Parameter definition: `value`, `llm_key`, `datatype`, `validation`, `available_options`, `is_optional`, `retry_count` | When building any parameter collection node |
| `references/05-api-call-node.md` | API call structure: `api_endpoint`, `prefill_params`, `copy_params`, `on_error`, `is_silent_step`, `soft_storage_params`, `set_available_options` | When building any API call node |
| `references/06-post-conditions.md` | Conditional branching: `logical_operator`, `conditions`, `true_step`, operators, functions | When adding conditional routing to any node |
| `references/07-error-handling.md` | Error codes, propagation model, `on_error` vs `post_conditions`, retry logic | When designing error paths and resilience |
| `references/08-best-practices.md` | Design principles, naming, validation strategy, performance | **Always** — read before starting any workflow task |
| `references/copy-params.md` | Passing data between nodes via `copy_params` | When wiring data flow between parameter and API nodes |
| `references/validation.md` | Local validation (regex, range, len) and remote API validation | When adding input validation to parameters |
| `references/silent-loading.md` | Auto-filling parameter values from prior API responses | When a parameter value can be inferred from a prior API call |
| `references/error-handling.md` | Quick reference card for error codes and routing decisions | When configuring `on_error` mappings |

---

## Workflow Creation Lifecycle

Follow these phases sequentially. Each phase has a clear deliverable.

### Phase 1 — Analyze the WRS

Read the Workflow Requirement Specification document given by the user completely. Extract:
- The business objective (what the workflow accomplishes)
- All data points to collect from the user
- All API operations required
- Conditional logic and branching requirements
- Error scenarios and recovery expectations
- Cross-workflow data needs (soft storage)

If the WRS is ambiguous or incomplete on any point, make a reasonable assumption and document it in the DECISIONS file (see Phase 6). Do not halt generation.

### Phase 2 — Design the Node Graph

Sketch the directed graph before writing JSON. Identify:
- The entry point (usually `__SOFT_STORAGE__` with session-aware routing)
- Each parameter collection node and what it collects
- Each API call node and what it executes
- Transitions between nodes (`default_step` and conditional `true_step`)
- Error handler nodes and terminal paths to `<--|end-of-flow|-->`
- Points where `set_available_options` pre-populates dynamic choices
- Points where `silent_loading` avoids redundant user prompts
- Points where `soft_storage_params` persists session data

Confirm every node is reachable from `current_step` and at least one path reaches `<--|end-of-flow|-->`.

### Phase 3 — Write the Metadata

Build the top-level fields following `references/02-workflow-json-structure.md`:
- `workflow_id` — UUID, no hyphens preferred
- `workflow_name` — action-oriented (e.g., "Create Incident Ticket")
- `workflow_description` — concise but complete objective and use cases
- `training_text` — 20+ natural language phrasings covering synonyms, short forms, and the description itself
- `executed_steps` — always `[]`
- `current_step` — typically `"__SOFT_STORAGE__"`
- `is_workflow_ended` — always `false`



### Phase 4 — Build the Nodes

Write each node following the reference documents. Key structural rules:

**Parameter nodes** (see `references/04-parameter-node.md`):
- Every parameter must have: `value` (always `""`), `llm_key`, `description`, `datatype`, `validation`, `available_options`, `is_optional`
- Set `retry_count` on any parameter with non-empty `validation`
- Group related parameters in one node; separate different stages into different nodes
- Use `|` separator in node names for multi-parameter collection: `"collect_subject_|_comment_|_priority"`

**API call nodes** (see `references/05-api-call-node.md`):
- Always include `"inputs": {}` and `"response": {}`
- `api_endpoint` is the relative path only — no protocol prefix
- Define `on_error` for at minimum `500` (server errors)
- Use `is_silent_step` to suppress background operation successes from the user
- Use `copy_params` to wire data from prior nodes into the API payload (see `references/copy-params.md`)

**Validation** (see `references/validation.md`):
- Static validation uses `function` + `criteria` + `operator` (e.g., regex email check)
- Dynamic validation uses `condition_step` + `condition_key` + `condition_source` + `operator` (no `function` or `criteria`)
- A parameter supports only one `validation` object; for complex validation, chain a dedicated `api_call` node after collection

**Post-conditions** (see `references/06-post-conditions.md`):
- `logical_operator` is `"and"`, `"or"`, or `""` (single condition)
- Maximum 2 conditions per post-condition object
- Evaluated in array order; first match wins
- `__SOFT_STORAGE__` can and should have post-conditions for session-aware routing

**Soft storage** (see `references/03-node-types-and-structure.md`):
- `__SOFT_STORAGE__` is always a parameter node with `"params": {}`
- Data persists for the entire user session across workflows
- When storing from API response: include `"source": "response"` in `soft_storage_params` keys
- When storing from parameter value: omit `source` entirely

**Silent loading** (see `references/silent-loading.md`):
- Use to auto-fill parameter values from prior API responses without prompting
- Source must be an `api_call` node that has already executed
- Use `$` as the nested field path separator in `source_field`

### Phase 5 — Validate

Run through the validation checklist below. Every item must pass before the workflow is considered complete.

### Phase 6 — Write the DECISIONS Document

Create a companion document listing every assumption, placeholder, and design decision made during generation. Structure it as:

```
## Assumptions
- [assumption description] — [rationale]

## Placeholders
- [field or value] — [what needs to be filled in and by whom]

## Design Decisions
- [decision] — [why this approach was chosen over alternatives]
```

This document is a mandatory deliverable alongside the workflow JSON.

---

## Validation Checklist

### Metadata
- [ ] `workflow_id` present (UUID format)
- [ ] `workflow_name` starts with action verb
- [ ] `workflow_description` covers objective and use cases
- [ ] `training_text` has 20+ natural phrasings with synonyms
- [ ] `executed_steps` is `[]`
- [ ] `current_step` is `"__SOFT_STORAGE__"` (or the correct entry node)
- [ ] `is_workflow_ended` is `false`
- [ ] No `_id` field

### Graph Integrity
- [ ] `__SOFT_STORAGE__` is defined in `steps` with `"params": {}`
- [ ] Every `default_step` references a valid node or `"<--|end-of-flow|-->"`
- [ ] Every `true_step` references a valid node or `"<--|end-of-flow|-->"`
- [ ] Every `on_error` code maps to a valid node or `"<--|end-of-flow|-->"`
- [ ] No orphan nodes (all nodes reachable from `current_step`)
- [ ] At least one path reaches `"<--|end-of-flow|-->"`
- [ ] No infinite loops without retry limits

### Parameter Nodes
- [ ] Every parameter has: `value: ""`, `llm_key`, `description`, `datatype`, `validation`, `available_options`, `is_optional`
- [ ] `value` is always `""`
- [ ] `available_options` is `[]` when dynamically populated
- [ ] `retry_count` set for parameters with non-empty `validation`
- [ ] Dynamic validation uses `condition_step`/`condition_key`/`condition_source`/`operator`
- [ ] Static validation uses `function`/`criteria`/`operator`

### API Call Nodes
- [ ] `"inputs": {}` present on every api_call node
- [ ] `"response": {}` present on every api_call node
- [ ] `api_endpoint` has no protocol prefix
- [ ] `on_error` defined with at minimum `500`
- [ ] `set_available_options.set_from` is the bare field name (not `response.field`)
- [ ] `soft_storage_params` uses `"source": "response"` for API response data
- [ ] `soft_storage_params` omits `source` for parameter value data

### Post-Conditions
- [ ] `logical_operator` is `"and"`, `"or"`, or `""`
- [ ] Max 2 conditions per post-condition object
- [ ] Each condition has `key`, `step`, `operator`

### JSON Integrity
- [ ] Valid JSON (no comments, no trailing commas)
- [ ] All field names are case-sensitive and match the reference documents exactly
- [ ] No extra fields beyond what the reference documents define

---

## Debugging Strategy

When a workflow fails or behaves unexpectedly, follow this sequence:

1. **Identify the failing node** — Check `current_step` and `executed_steps` to locate where execution stopped.
2. **Inspect the node definition** — Read the corresponding reference document for that node type and verify every field matches the spec.
3. **Trace data flow** — Follow `copy_params` chains backward to confirm source values exist and `source` flags are correct.
4. **Check post-conditions** — Verify condition evaluation order, `logical_operator`, and that `step`/`source` references point to the right data.
5. **Verify error routing** — Confirm `on_error` covers the returned error code and routes to a valid node.
6. **Compare against best practices** — Re-read `references/08-best-practices.md` for patterns the workflow may violate.
7. **Compare against examples** — Check `examples/` for production workflows that handle similar patterns.

If the issue is still unclear, re-read the specific reference document for the construct involved (validation, silent loading, copy params, etc.) and cross-reference against the example workflows.

---

## Thinking Strategy

When approaching a workflow generation task, reason through it in this order:

1. **What is the end goal?** — What business outcome does the WRS describe?
2. **What data is needed?** — What must be collected from the user vs. fetched from APIs vs. read from soft storage?
3. **What is the sequence?** — What depends on what? Which API calls gate which parameter collections?
4. **What can go wrong?** — Map every error scenario to a recovery path or clean termination.
5. **What can be optimized?** — Can any prompts be skipped via `silent_loading`? Can any data be cached in `__SOFT_STORAGE__`?
6. **Does it follow the spec?** — Run the validation checklist before finalizing.

Do not invent patterns, field names, or behaviors beyond what the reference documents define. When uncertain, fall back to the reference documents and the example workflows in `examples/`.

---

## Reference Examples

Production workflow examples are in `examples/`. Use them to verify structural patterns and field conventions. Match their style for field ordering, naming, and structure. Available examples:

- `examples/view_single_zendesk_ticket.json` — Read-only ticket lookup flow

---

## Quick Reference: Key Patterns

**Session-aware entry via `__SOFT_STORAGE__`:**
Use post-conditions on `__SOFT_STORAGE__` to skip authentication if the user is already authenticated. Route to the first post-auth step via `true_step`, and to credential collection via `default_step`.

**Dynamic option population:**
Use an `api_call` node with `set_available_options` to fetch valid choices *before* the parameter node that collects the user's selection. The `set_from` value is the bare field name from the API response (not prefixed with `response.`).

**Cross-node data wiring:**
Use `copy_params` to pass collected parameter values or API response fields into downstream API call payloads. Omit `source` for parameter values; use `"source": "response"` for API response fields.

**Error routing:**
Use `on_error` for unexpected failures requiring immediate redirection. Use `post_conditions` for expected business logic branching (e.g., success vs. validation failure). Route directly to `<--|end-of-flow|-->` for unrecoverable errors.

**Soft storage persistence:**
Persist authentication tokens, user identity, or session context via `soft_storage_params` on `api_call` nodes. Include `"source": "response"` when storing from API responses; omit `source` when storing from parameter values.
