# Parameter Node

A parameter node contains the meta information about each parameter that prompts the agent to ask for the info to the user. The paramter node contains atleast one parameter object, which stores the values once collected from the user.

---

## Complete Structure

The complete structure of a parameter node is as follows:
- `type`
- `params`
- `silent_loading`
- `post_conditions`
- `default_step`

```json
"node_name": {
  "type": "parameter",
  "params": {
    "parameter_key": {
      "value": "",
      "llm_key": "Human-Readable Label",
      "datatype": "str",
      "description": "What this field is and any format expectations.",
      "validation": { },
      "available_options": [],
      "is_optional": false,
      "retry_count": 3
    }
  },
  "silent_loading": [ ], //only when needed else dont use this
  "post_conditions": [ ],
  "default_step": "next_node_name"
}
```

## 1. `type`

- **Type:** String
- **Required:** Yes
- **Purpose:** Defines the type of node. For a parameter node, this value MUST be `"parameter"`. The workflow engine uses this field to identify and process the node correctly.

## 2. `params` Object

- **Type:** Object
- **Required:** Yes
- **Purpose:** Contains one or more parameter definitions. Each key in this object is a unique identifier for a parameter within this node, and each value is a **parameter definition object** that describes a single field the workflow needs to collect.

  > **Important** : See the below section **Parameter Object** to understand how to configure the JSON for a parameter.

## 3. `silent_loading`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Automatically pre-fills parameter values from the response of a previous API call node, without asking the user. If a value is successfully loaded silently, the engine skips prompting the user for that parameter, thus its called `silent_loading`. 

  > **Important** : Only define this key when you actually need this in your workflow, else dont define this key. For complete usage and structure, see [`silent-loading.md`](./silent-loading.md).

## 4. `post_conditions`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Defines routing conditions that are evaluated after all parameters in this node have been collected.

  > **Important** : Only define this key when you actually need this in your workflow, else dont define this key. For complete **post conditions rules**, see [`06-post-conditions.md`](./06-post-conditions.md).


## 5. `default_step`

- **Type:** String
- **Required:** No
- **Default:** `"<--|end-of-flow|-->"` if omitted
- **Purpose:** Specifies the next node to execute if no `post_conditions` match or if this is the initial node in the workflow. This acts as the fallback or default transition.
- **Common Values:**
  - A node name (string) for a subsequent node in the workflow.
  - `"<--|end-of-flow|-->"` to terminate the workflow.

---

## How to use the `params` object?

The `params` field is a key-value map. Each key is the internal identifier for a parameter (used throughout the workflow to reference this value, defined using snake casing), and each value is a **parameter definition object**.

A single parameter node can collect multiple related fields at once. Group fields that logically belong together in one node, and separate fields that belong to different stages of the process into different nodes.

**Example:**
```json
"collect_requester_info": {
  "type": "parameter",
  "params": {
    "email_address": { ... paramter object of "email_address" key},
    "department": { ... parameter object of "department" key},
    "contact_number": { ... parameter object of "contact_number" key}
  },
  "silent_loading": [...], //only when needed else dont use this
  "post_conditions": [], //only when needed else dont use this
  "default_step": "next_node_name" //only when needed else dont use this
}
```
---

## Parameter Definition Object & its properties

### `value`

- **Type:** String (initially)
- **Required:** Yes
- **Default:** `""` (empty string — always start empty, because `None` also have significance)
- **Purpose:** Stores the user-provided value after it passes validation. The workflow engine writes to this field; you should never pre-populate it in the JSON definition.
- **After Collection:** The engine stores the value here and marks the parameter as resolved. Other nodes can then read from it via `copy_params`.

---

### `llm_key`

- **Type:** String
- **Required:** Yes
- **Purpose:** The human-readable label the agent uses to identify this parameter when communicating with the user. This is what the agent sees and what it uses to ask the user for input.
- **Best Practice:** Use clear, natural language labels that match what a user would expect to be asked. Don't use snake, pascal, camel casing or any special characters.

  | ✅ Good | ❌ Bad |
  |---|---|
  | `"Email address"` | `"email_address"` |
  | `"Department name"` | `"departmentName"` |
  | `"Start date"` | `"startDate"` |

---

### `datatype`

- **Type:** String
- **Required:** Yes
- **Purpose:** Declares the expected data type of the user's input. The workflow engine attempts to cast the raw string input to this type before applying validation rules.
- **Supported Types:**

  | Type String | Description |
  |---|---|
  | `"str"` | Plain text string |
  | `"int"` | Integer number |
  | `"float"` | Decimal number |
  | `"bool"` | Boolean (`true` / `false`) |
  | `"List[str]"` | List of strings |
  | `"List[int]"` | List of integers |
  | `"Dict[str, str]"` | Dictionary with string keys and string values |

- **Behavior:** If the cast fails (e.g., user provides `"hello"` for an `"int"` field), the engine treats it as a validation failure and prompts the user again. It supports all the types which can be validated using the **_Python's Pydantic models._**

---

### `description`

- **Type:** String
- **Required:** Yes
- **Purpose:** Explains to the agent what this parameter represents, including any format requirements, business context, or constraints. The agent uses this knowledge to communicate with the user.
- **Guidelines:**
  - Be specific about format when it matters (e.g., date formats, email domains).
  - Include business context to help the agent phrase the question appropriately.
  - Mention constraints the user should know about before answering.
- **Example:** `"The user's corporate email address. Must follow the format name@company.com. Used for ticket assignment and notification."`

---

### `validation`

- **Type:** Object
- **Required:** No
- **Purpose:** Defines one or more rules that the user's input must satisfy before the value is accepted. Supports both local rule-based validation and remote API-based validation. When there is no validation for a parameter, it is must to set it as an empty object.

  > For the full validation specification, supported functions, operators, and API validation structure, see [`parameter-validation.md`](./parameter-validation.md).

---

### `available_options`

- **Type:** Array
- **Required:** No
- **Purpose:** For parameters where the user must choose from a fixed set of values, this list defines the valid choices. The agent presents these options to the user.
- **Static vs. Dynamic:**
  - **Static:** Hardcoded in the workflow JSON. Use when options are known at design time (e.g., priority levels: `["Low", "Medium", "High", "Critical"]`).
  - **Dynamic:** The array starts empty (`[]`) and is populated at runtime by a preceding `api_call` node using `set_available_options`. Use when options depend on backend data (e.g., department list from HR system).
- **Behavior:** When `available_options` is non-empty, the engine validates that the user's input is one of the listed values.

---

### `is_optional`

- **Type:** Boolean
- **Required:** Yes
- **Default:** `false`
- **Purpose:** Controls whether the user must provide a value for this parameter.

  | Value | Behavior |
  |---|---|
  | `false` | Parameter is required. The agent will keep prompting until a valid value is provided (subject to `retry_count`). |
  | `true` | Parameter is optional. The user can skip it, and the engine stores `null` or an empty value and moves on. |

- **Design Guidance:** Mark parameters as optional only when the downstream API call or business process can genuinely function without the value.

---

### `retry_count`

- **Type:** Integer
- **Required:** No
- **Purpose:** Limits the number of times a user can attempt to provide a valid value for this parameter. If the user fails to provide a valid value within this many attempts, the engine routes to an error-handling node.
- **Default:** If omitted, unlimited retries are allowed.
- **When to Set:** Use `retry_count` for parameters with strict validation where it's better to fail gracefully than loop indefinitely (e.g., OTP codes, confirmation fields).

---

### `silent_loading`

- **Type:** Array of Objects
- **Required:** No
- **Purpose:** Automatically pre-fills parameter values from the response of a previous API call node, without asking the user. If a value is successfully loaded silently, the engine skips prompting the user for that parameter, thus its called `silent_loading`.

  > For full usage and structure, see [`silent-loading.md`](./silent-loading.md).

---

## Related References

- [`parameter-validation.md`](./parameter-validation.md) — Contains different kind of validations supported by the workflow engine like regex, range, API-based. Also covers how to handle validation failures.
- [`silent-loading.md`](./silent-loading.md) — Contains different usecases and how-to use  auto-filling parameter values from API responses
- [`06-post-conditions.md`](./06-post-conditions.md) — Conditional routing after parameter collection