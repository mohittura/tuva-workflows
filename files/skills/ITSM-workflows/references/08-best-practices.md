# Best Practices

This document consolidates design principles, JSON structure guidelines, and performance considerations for building reliable, maintainable workflows. Cross-references to specific documents are provided where a principle requires deeper technical context.

---

## Workflow Design Principles

### Single Responsibility
Each workflow should accomplish one primary business objective. A workflow that creates a ticket should not also handle user authentication — those are separate concerns, each deserving their own workflow. When a workflow grows beyond one clear objective, split it.

### Progressive Disclosure
Collect only the information needed at each stage of the process. Don't front-load a workflow with ten parameters when the first API call might reveal that half of them aren't needed. Use the results of early API calls to determine which parameters to collect next.

### Defensive Validation
Validate user input before sending it to backend systems. Use parameter-level `validation` rules for format checks (regex, range, length), and use `api_call` nodes for business-rule validation that requires a backend lookup.
> See [`ref-validation.md`](./ref-validation.md).

### Graceful Degradation
Every workflow should handle its failure cases with user-friendly responses. A workflow that can silently fail or get stuck is worse than one that clearly communicates the problem and exits cleanly.
> See [`07-error-handling.md`](./07-error-handling.md).

### State Awareness
Use `__SOFT_STORAGE__` for data that spans multiple workflows — authentication tokens, user identity, session context. Avoid re-fetching data the session already has. But use soft storage judiciously: don't store data there that should be re-validated on each request.

---

## JSON Structure Guidelines

### Naming Conventions
Use consistent, descriptive names for nodes and parameters. Node names should reflect their action: `collect_issue_description`, `validate_user_access`, `create_ticket_api`. Avoid generic names like `step_1` or `node_a`.

| ✅ Good | ❌ Avoid |
|---|---|
| `"collect_affected_user_email"` | `"step_3"` |
| `"fetch_department_list"` | `"api_node"` |
| `"validate_ticket_priority"` | `"validate"` |

### Modular Parameter Grouping
Group logically related parameters in a single parameter node. Collect "who is affected and what happened" together, then collect "when and what priority" in the next node. This creates a natural conversational flow.

### Always Document
Fill in `description` for every parameter, and `workflow_description` / `training_text` for every workflow. Future maintainers (and the AI agent itself) depend on these descriptions to understand intent.

### Always Define `on_error`
Every `api_call` node should have an `on_error` mapping for at minimum `500` (server errors). Leaving `on_error` empty means unexpected failures silently fall to `default_step`, which is almost never the correct behavior.
> See [`07-error-handling.md`](./07-error-handling.md) and [`05-api-call-node.md`](./05-api-call-node.md).

### Never Pre-Populate `value`
The `value` field in parameter definitions must always start as `""`. Pre-populating it would cause the engine to treat the field as already collected, skipping the user prompt.

---

## Parameter Design

### Required Before Optional
Always place required parameters before optional ones within a node, and collect required nodes before optional ones in the graph. This ensures the workflow can exit early (via post-conditions) if it has the minimum data it needs, without waiting for optional input.

### Retry Counts on High-Stakes Fields
For fields with strict validation — confirmation codes, identifiers that must match a backend record — set an explicit `retry_count`. Allowing unlimited retries on such fields risks infinite loops.

### Use `available_options` for Controlled Choices
When a parameter has a fixed set of valid values, always populate `available_options` (statically or dynamically). This reduces validation errors, guides the user toward valid input, and makes the agent's phrasing more precise.

---

## API Call Design

### Separate Read from Write
Prefer separate nodes for read operations (fetching options, validating existence) and write operations (creating, updating, deleting). This makes error handling cleaner and allows retry logic to be applied safely to reads without fear of duplicate writes.

### Cache with Soft Storage
If an API response contains data that other workflows in the session will need — user auth tokens, user profile data, department mappings — persist it to `__SOFT_STORAGE__` via `soft_storage_params`. This eliminates redundant API calls across the session.
> See [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) for `__SOFT_STORAGE__` behavior.

### Use Silent Loading for Pre-fill
When a prior API call already returned data that a subsequent node needs in its `prefill_params`, use `silent_loading` instead of asking the user or duplicating the API call.
> See [`ref-silent-loading.md`](./ref-silent-loading.md).

### Set `is_silent_step` Deliberately
For background API calls (fetching lists, pre-validating tokens), set `200` to silent (`true`) so the user isn't narrated through invisible bookkeeping. But always keep failure codes visible (`false`) so the user can be informed if something goes wrong.

---

## Post-Condition Design

### Prefer Explicit Success Checks
Rather than assuming a node succeeded if no error was detected, write explicit post-conditions that check for `error_code == 200` before routing forward. This makes the happy path explicit and the failure paths visible.

### Keep Condition Logic Simple
Post-conditions currently support a maximum of two conditions per object. If your routing logic is becoming complex, consider breaking the workflow into more granular API call nodes, each with its own simple conditions.
> See [`06-post-conditions.md`](./06-post-conditions.md).

---

## Performance Optimization

| Principle | Practice |
|---|---|
| Minimize redundant API calls | Cache frequently used data in `__SOFT_STORAGE__` |
| Validate cheaply first | Run regex / range checks in parameter `validation` before making API validation calls |
| Exit early | Use post-conditions to route to `<--|end-of-flow|-->` as soon as the workflow has everything it needs |
| Collect mandatory fields first | Don't wait for optional fields to make critical API calls |
| Use `set_available_options` before collection | Fetch option lists in a preceding API call, not during the parameter collection step itself |

---

## Training Text Quality

The quality of `training_text` directly determines how reliably the discovery system finds this workflow. Poor training text means the workflow is hard to trigger.

**Good training text includes:**
- Multiple natural phrasings of the user's intent
- Domain synonyms (e.g., "incident," "issue," "problem," "outage" for an incident ticket workflow)
- The `workflow_description` itself for contextual grounding
- Common short forms and alternate phrasings users actually type

**Avoid:**
- Technical jargon that users would never say
- Phrasing that is too generic and would match many workflows
- Exact duplicates of other workflows' training text