# What Is a Workflow?

## Fundamental Definition

A workflow or ITSM workflow is a JSON based structure that defines the various steps to execute an operation. A workflow in this system is **not** a simple script or a linear sequence of steps. It is a self-contained, configurable description of a business process — expressed as a graph — that an AI agent can discover, initialize, and drive to completion entirely on its own.

This definition inverts the traditional relationship between humans, automation, and AI:

| Traditional System | This System |
|---|---|
| Humans trigger workflows | AI agent triggers workflows |
| AI is a component inside a workflow | AI is the orchestrator that runs workflows |
| Business logic is coded in the agent | Business logic lives in the workflow JSON |

The result is a clean separation of concerns:
- The **agent** handles natural language understanding, user conversation, and deciding *what* to do.
- The **workflow** defines *how* to do it — the parameters to collect, the API calls to make, the conditions to check, and the order to do all of this in.

---

## Workflow as a Directed Cyclic Graph (DCG)

Unlike traditional flowcharts or pipelines that only move forward, a workflow here is modeled as a **Directed Cyclic Graph (DCG)**. This means:

- Every workflow is composed of **nodes** (individual steps) connected by **directed edges** (transitions).
- The graph can contain **cycles** — a node can route back to a previously visited node. Because the cycles can take the system into the infinite loop, the workflow supports the recursion count that saves the workflow from going into the infinite loop.

This cyclic capability is essential for real-world business processes:

- **Iterative Refinement:** A user can provide information incrementally. If a required field is missing or invalid, the workflow loops back to re-collect it rather than failing outright.
- **Retry Logic:** After a failed validation or API error, the workflow can return the user to the relevant collection node with a clear explanation.
- **Conditional Revisiting:** Business processes genuinely require returning to a prior step depending on what was discovered at a later step.

Each node in the graph is one of two types: a **parameter node** (collects information) or an **API call node** (executes an action). The graph progresses through these nodes based on user inputs, API responses, and conditional logic called post-conditions.

> See [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) for the full node reference.

---

## How Workflows Attach to the System

Workflows attach to the system as external JSON definitions. The agent discovers the right workflow, loads its full definition, and executes it in the session.

```
User Request
     │
     ▼
  AI Agent
     │
     ▼
Search matching workflows
     │
     ▼
Load selected workflow JSON
     │
     ▼
Execute steps until complete
```

### Storage Layer

| Store | Purpose |
|---|---|
| **MongoDB** | Stores the complete workflow JSON definitions (all nodes, edges, configurations) |
| **Milvus Vector DB** | Stores vector embeddings of each workflow's `training_text` for semantic search |

### How the System Works

1. The agent receives the user request and searches for the available operations(workflows) with a context-rich query.
2. The agent will receive the top-5 most similar workflows as candidate and the agent will select the relevant one.
3. The agent loads the workflow json, and executes it.
4. The workflow logic will provide the feedback that will be passed into the agent for making the responses to the users.
5. The feedback can be asking for parameters, operation execution response etc in natural language.
6. The agent collects the information provided by the user, submits it into the workflow, and the workflow proceeds with the next steps. This loop continues until the workflow is ended or terminated.

---

### State Tracked During Execution

The session maintains the full workflow state at every turn, including:

- The complete workflow JSON structure
- `current_step` — which node is active
- `executed_steps` — history of completed nodes
- Collected parameter values from the user
- API response payloads from each `api_call` node
- The **soft storage cache** (`__SOFT_STORAGE__`) for cross-workflow data

This stateful design allows workflows to span multiple conversational turns, resume after interruptions, and support long-running processes without losing context.

## Workflow JSON at a Glance

A workflow is stored as one JSON document in MongoDB. At the top level, it contains metadata that helps the agent discover and control the workflow, plus a `steps` object that defines the executable graph.

The core structure includes:

| Field | datatype | Purpose |
|---|---|---|
| `workflow_id` | string | Unique identifier that links the MongoDB record with its Milvus vector record |
| `workflow_name` | string | Human-readable operation name used by the agent during initialization |
| `workflow_description` | string | Short explanation of what the workflow does |
| `training_text` | string | Search text embedded into Milvus for semantic discovery |
| `executed_steps` | array | Runtime history of nodes already completed |
| `current_step` | string | The node the engine should execute next |
| `is_workflow_ended` | boolean | Flag that stops execution when the workflow is complete |
| `steps` | object | Also known as nodes. Has all the node of the workflow in the object. Each node can be a parameter node, an API call node or an Interrupt node, including special constructs like `__SOFT_STORAGE__` and `<--|end-of-flow|-->` which help in managing state and terminating the workflow. |

> For the full workflow JSON reference, see [`02-workflow-json-structure.md`](./02-workflow-json-structure.md).
