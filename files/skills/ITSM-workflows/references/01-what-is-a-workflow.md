# What Is a Workflow?

## Fundamental Definition

A workflow in this system is **not** a simple script or a linear sequence of steps. It is a self-contained, configurable description of a business process — expressed as a graph — that an AI agent can discover, initialize, and drive to completion entirely on its own.

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
- The graph can contain **cycles** — a node can route back to a previously visited node.

This cyclic capability is essential for real-world business processes:

- **Iterative Refinement:** A user can provide information incrementally. If a required field is missing or invalid, the workflow loops back to re-collect it rather than failing outright.
- **Retry Logic:** After a failed validation or API error, the workflow can return the user to the relevant collection node with a clear explanation.
- **Conditional Revisiting:** Some business processes genuinely require returning to a prior step depending on what was discovered at a later step.

Each node in the graph is one of two types: a **parameter node** (collects information) or an **API call node** (executes an operation). The graph progresses through these nodes based on user inputs, API responses, and conditional logic called post-conditions.

> See [`03-node-types-and-structure.md`](./03-node-types-and-structure.md) for the full node reference.

---

## How Workflows Attach to the System

Workflows attach to the system as external JSON definitions. The agent discovers the right workflow, loads its full definition, and attaches it to a LangGraph session for execution.

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
Attach to LangGraph session
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

1. The agent receives a user request and calls **"Search for Available Operations"** with a context-rich query.
2. Azure OpenAI's `text-embedding-3-large` model converts the query into a vector.
3. Milvus searches workflow embeddings and returns the closest matching workflow IDs.
4. MongoDB provides the matching workflow names and descriptions so the agent can choose the best operation.
5. The agent calls **"Initialize Operation"** with the selected workflow name.
6. MongoDB returns the full workflow JSON, and the workflow is loaded into a **LangGraph session** as active execution state.
7. The engine starts from `current_step` and continues through parameter collection, API calls, loops, and completion.

---

## Execution Loop

Once initialized, the workflow engine runs a continuous state machine loop until the workflow is marked complete:

```
Load workflow JSON into session state
         │
         ▼
  Read current_step
         │
         ▼
┌────────────────────┐
│  Is node type...   │
│                    │
│  parameter?  ──────┼──► Request value from user via agent
│  api_call?   ──────┼──► Execute HTTP request to backend
└────────────────────┘
         │
         ▼
  Process result:
  - Store response / parameter value in state
  - Evaluate post_conditions (if any)
  - Determine next step (post-condition match or default_step)
  - Update current_step
         │
         ▼
  is_workflow_ended == true?
  ├── Yes ──► Stop. Workflow complete.
  └── No  ──► Loop back to "Read current_step"
```

### State Tracked During Execution

The LangGraph session maintains the full workflow state at every turn, including:

- The complete workflow JSON structure
- `current_step` — which node is active
- `executed_steps` — history of completed nodes
- Collected parameter values from the user
- API response payloads from each `api_call` node
- The **soft storage cache** (`__SOFT_STORAGE__`) for cross-workflow data

This stateful design allows workflows to span multiple conversational turns, resume after interruptions, and support long-running processes without losing context.

### Agent–Workflow Communication

During execution, the agent and workflow exchange structured messages:

**Workflow → Agent:**
| Message | Meaning |
|---|---|
| `need_parameter` | Ask the user to provide a specific value |
| `execution_result` | Report what an API call returned |
| `validation_failed` | Inform the user their input was invalid, with a reason |
| `workflow_completed` | Signal that the workflow has finished successfully |

**Agent → Workflow:**
| Message | Meaning |
|---|---|
| `parameter_value` | Submit user-provided input to the workflow |
| `initiate_workflow` | Start a new workflow |
| `cancel_workflow` | Abort the current workflow |

---

## Workflow JSON at a Glance

A workflow is stored as one JSON document in MongoDB. At the top level, it contains metadata that helps the agent discover and control the workflow, plus a `steps` object that defines the executable graph.

The core structure includes:

| Field | Purpose |
|---|---|
| `workflow_id` | Unique identifier that links the MongoDB record with its Milvus vector record |
| `workflow_name` | Human-readable operation name used by the agent during initialization |
| `workflow_description` | Short explanation of what the workflow does |
| `training_text` | Search text embedded into Milvus for semantic discovery |
| `executed_steps` | Runtime history of nodes already completed |
| `current_step` | The node the engine should execute next |
| `is_workflow_ended` | Flag that stops execution when the workflow is complete |
| `steps` | Map of all workflow nodes and transitions |

The `steps` object contains the actual process graph. Each step is usually a **parameter node** that collects user input or an **API call node** that performs a backend operation. Special constructs like `__SOFT_STORAGE__` and `<--|end-of-flow|-->` help manage shared state and workflow termination.

> For the full workflow JSON reference, see [`02-workflow-json-structure.md`](./02-workflow-json-structure.md).
