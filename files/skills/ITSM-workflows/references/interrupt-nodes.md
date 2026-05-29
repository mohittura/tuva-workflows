# Interrupt nodes 

These are special nodes which are used to temporarily pause the workflow execution. They are very rare and should only be used when explicitly specified in the Workflow Request Specification (WRS) document. In complex, multi-stage, or asynchronous workflows (such as those requiring external approvals, background jobs, or human-in-the-loop validation), these nodes serve to halt the flow safely without terminating it, preserving all current state data.

## Where it is used 
It is used when certain post-conditions are evaluated and met, signaling that the workflow requires a pause—for instance, when a task is running for a long duration in the background or requires manual intervention/external approval. Once the engine enters this node, it directs the conversational agent to pause execution, preserve the session state (including all gathered parameters and `__SOFT_STORAGE__` data), and inform the user clearly about the suspension.

## Structure
```json
"node_name": {
  "type": "__INTERRUPT__",
  "inputs": {},
  "response": {},
  "default_step": "<--|end-of-flow|-->"
}
```
An interrupt node is declared in the workflow `steps` graph like any regular parameter or API call node:
- **`type`**: Must always have the exact value `"__INTERRUPT__"`.
- **`default_step`**: Defines where execution should resume once the pause state is cleared or completed. This is either set to the next verification node specified in the WRS or defaulted to the terminal marker `"<--|end-of-flow|-->"`.
- **`inputs` & `response`**: Must be declared and initialized as empty objects (`{}`). They carry no payloads since the node does not collect data or invoke APIs, but are required to pass validation against the engine's schema.

## Why do we need it?

In long-running automation or processes with human approval stages, the agent cannot hold a synchronous connection open indefinitely. An interrupt node is essential to gracefully serialize and store the state of the active workflow. It allows the system to notify the user of the pause (e.g., waiting for background operations or manager approval) and cleanly release operational resources. When the external event finishes, the workflow can resume from this exact point without losing previously collected inputs.

## Example

```json
"pause_remove_unused_apps": {
  "type": "__INTERRUPT__",
  "inputs": {},
  "response": {},
  "default_step": "<--|end-of-flow|-->"
}
```
In this example:
- **`pause_remove_unused_apps`** is the unique identifier for the node.
- The node serves to pause the workflow because its `type` is set to `"__INTERRUPT__"`.
- The `inputs` and `response` keys are empty objects (`{}`) because no parameters are gathered and no HTTP calls are executed at this node.
- The workflow execution halts here to wait for background operations (such as app removal tasks). When execution resumes, it defaults to the terminal step `"<--|end-of-flow|-->"`.

## Key Rules
- **WRS Authorization**: Only implement this node when explicitly requested or required by the Workflow Request Specification (WRS) document.
- **Node Type Specifier**: The `type` attribute must always be exactly `"__INTERRUPT__"`.
- **Default Step Routing**: It must have a `default_step` defined, which is typically set to `"<--|end-of-flow|-->"` unless a specific resumption target node is requested by the WRS.
- **Payload Requirements**: The `inputs` and `response` objects must be defined as empty objects (`{}`) to conform to the system schema validation.
