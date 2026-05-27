"""Workflow Builder Tools.

Three tools purpose-built for the Tuva ITSM workflow builder agent:

  think_tool           — Strategic reflection for graph design decisions
  validate_workflow    — Programmatic pre-flight checklist against the full schema
  render_graph         — ASCII directed graph of workflow nodes and edges
"""

import json
import re
import uuid
from typing import Any

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

END_OF_FLOW = "<--|end-of-flow|-->"
SOFT_STORAGE = "__SOFT_STORAGE__"

VALID_DATATYPES = {
    "str", "int", "float", "bool",
    "List[str]", "List[int]", "List[float]",
    "Dict[str, str]", "Dict[str, int]",
}

VALID_VALIDATION_FUNCTIONS = {
    "regex", "range", "len",
    "is_empty", "is_not_empty",
    "is_none", "is_not_none",
    "is_subset", "is_date_time_format_valid",
}

VALID_OPERATORS = {"==", "!=", ">", "<", ">=", "<=", "in", "not in"}

VALID_LOGICAL_OPERATORS = {"and", "or", ""}

KNOWN_ERROR_CODES = {"200", "500", "701", "702", "704", "706", "708"}

ACTION_VERBS = {
    "create", "update", "delete", "fetch", "get", "search", "find",
    "submit", "assign", "resolve", "escalate", "approve", "reject",
    "reset", "send", "notify", "validate", "generate", "list",
    "close", "open", "add", "remove", "check", "verify", "log",
}


# ---------------------------------------------------------------------------
# think_tool
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Strategic reflection tool for workflow design decisions.

    Use this tool before and after any significant design decision to reason
    through the workflow graph deliberately. This prevents structural mistakes
    that are hard to fix later.

    When to use:
    - Before sketching the node graph: What nodes are needed? What order?
    - After sketching: Are all error paths handled? Are there infinite loops?
    - Before writing a parameter node: Does validation make sense? What retry_count?
    - Before writing an api_call node: What error codes are realistic? Silent or visible?
    - After writing a node: Does it need post_conditions or is default_step enough?
    - Before assembling final JSON: Are all copy_params referencing real node names?
    - After validate_workflow() reports issues: What is the root cause of each error?

    Reflection should address:
    1. What decision am I making right now?
    2. What constraints apply (schema rules, business logic, error handling)?
    3. What are the failure modes if I get this wrong?
    4. What is the correct approach and why?

    Args:
        reflection: Detailed reasoning about the current workflow design decision.

    Returns:
        Confirmation that the reflection was recorded.
    """
    return f"[think_tool] Reflection recorded:\n{reflection}"


# ---------------------------------------------------------------------------
# generate_uuid
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def generate_uuid() -> str:
    """Generate a UUID4 value for workflow metadata.

    Use this tool when creating a new Tuva ITSM workflow_id.

    Returns:
        A UUID4 string suitable for the workflow_id metadata field.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# validate_workflow
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def validate_workflow(workflow_json: str) -> str:
    """Validate a Tuva ITSM workflow JSON definition against the full schema.

    Runs the complete pre-flight checklist programmatically:
    - Metadata fields (workflow_id, workflow_name, training_text, etc.)
    - Structural integrity (no dead-end references, at least one path to end-of-flow)
    - Parameter node correctness (required fields, valid datatypes, retry_count rules)
    - API call node correctness (endpoint format, response placeholder, on_error coverage)
    - Post-condition correctness (operator validity, condition count limits, source format)
    - Best practice warnings (missing 500 handler, missing retry_count, silent step usage)

    Use this tool:
    - After assembling the full workflow JSON (before presenting to user)
    - After every edit (even small ones — references can break silently)
    - When debugging a workflow that isn't executing correctly

    Args:
        workflow_json: The complete workflow JSON as a string.

    Returns:
        A structured validation report: errors (must fix), warnings (should fix),
        and a pass/fail summary.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- Parse ---
    wf, parse_error = _load_workflow(workflow_json, "validate_workflow")
    if parse_error:
        return parse_error

    steps: dict[str, Any] = wf.get("steps", {})
    if steps and not isinstance(steps, dict):
        errors.append(
            f"[Steps] 'steps' must be an object mapping node names to node definitions. "
            f"Got: {_type_name(steps)}."
        )
        return _format_report(errors, warnings)

    # -------------------------------------------------------------------------
    # 1. METADATA CHECKS
    # -------------------------------------------------------------------------

    if not wf.get("workflow_id"):
        errors.append(
            "[Metadata] 'workflow_id' is missing or empty. "
            f"Generate one with generate_uuid(), for example: '{uuid.uuid4()}'."
        )
    else:
        try:
            uuid.UUID(str(wf["workflow_id"]))
        except (AttributeError, TypeError, ValueError):
            warnings.append(
                "[Metadata] 'workflow_id' is not a valid UUID. "
                f"Generate one with generate_uuid(), for example: '{uuid.uuid4()}'."
            )

    wf_name = wf.get("workflow_name", "")
    if not wf_name:
        errors.append("[Metadata] 'workflow_name' is missing.")
    elif not isinstance(wf_name, str):
        errors.append(f"[Metadata] 'workflow_name' must be a string. Got: {_type_name(wf_name)}.")
    else:
        first_word = wf_name.split()[0].lower() if wf_name.split() else ""
        if first_word not in ACTION_VERBS:
            warnings.append(
                f"[Metadata] 'workflow_name' should start with an action verb "
                f"(e.g., 'Create Incident Ticket'). Got: '{wf_name}'."
            )

    workflow_description = wf.get("workflow_description")
    if not workflow_description:
        errors.append("[Metadata] 'workflow_description' is missing.")
    elif not isinstance(workflow_description, str):
        errors.append(
            f"[Metadata] 'workflow_description' must be a string. "
            f"Got: {_type_name(workflow_description)}."
        )

    training_text = wf.get("training_text", "")
    if not training_text:
        errors.append("[Metadata] 'training_text' is missing.")
    elif not isinstance(training_text, str):
        errors.append(
            f"[Metadata] 'training_text' must be one string, not {_type_name(training_text)}. "
            "Join all example phrases into a single sentence-style string."
        )
    else:
        # Rough phrase count: split on sentence-ending punctuation
        phrases = [s.strip() for s in re.split(r"[.!?]+", training_text) if s.strip()]
        if len(phrases) < 5:
            warnings.append(
                f"[Metadata] 'training_text' has only {len(phrases)} phrase(s). "
                "Include 5+ natural language query phrasings for good semantic search coverage."
            )

    if wf.get("executed_steps") != []:
        errors.append("[Metadata] 'executed_steps' must be [] in the workflow definition.")

    current_step = wf.get("current_step", "")
    if not current_step:
        errors.append("[Metadata] 'current_step' is missing.")
    elif not isinstance(current_step, str):
        errors.append(f"[Metadata] 'current_step' must be a string. Got: {_type_name(current_step)}.")
    elif current_step != SOFT_STORAGE and current_step not in steps:
        errors.append(
            f"[Metadata] 'current_step' is '{current_step}' but this node does not exist in 'steps'."
        )

    if wf.get("is_workflow_ended") is not False:
        errors.append("[Metadata] 'is_workflow_ended' must be false in the workflow definition.")

    if not steps:
        errors.append("[Steps] 'steps' object is missing or empty.")
        return _format_report(errors, warnings)

    # -------------------------------------------------------------------------
    # 2. STRUCTURAL INTEGRITY
    # -------------------------------------------------------------------------

    if SOFT_STORAGE not in steps:
        errors.append(
            f"[Structure] '__SOFT_STORAGE__' node is missing from 'steps'. "
            "It must always be defined, even if empty."
        )
    else:
        ss_node = steps[SOFT_STORAGE]
        if not isinstance(ss_node, dict):
            errors.append("[Structure] '__SOFT_STORAGE__' node must be an object.")
        elif ss_node.get("type") != "parameter":
            errors.append("[Structure] '__SOFT_STORAGE__' node must have type='parameter'.")
        elif ss_node.get("params") != {}:
            warnings.append(
                "[Structure] '__SOFT_STORAGE__'.params should be {} in the JSON definition "
                "(the engine populates it at runtime)."
            )

    # Check all step references resolve
    for node_name, node in steps.items():
        if not isinstance(node, dict):
            errors.append(f"[Structure] Node '{node_name}' must be an object. Got: {_type_name(node)}.")
            continue

        # default_step
        ds = node.get("default_step")
        if not ds:
            errors.append(f"[Structure] Node '{node_name}' is missing 'default_step'.")
        elif not isinstance(ds, str):
            errors.append(
                f"[Structure] Node '{node_name}'.default_step must be a string. "
                f"Got: {_type_name(ds)}."
            )
        elif ds != END_OF_FLOW and ds not in steps:
            errors.append(
                f"[Structure] Node '{node_name}'.default_step = '{ds}' "
                "does not exist in 'steps'."
            )

        # post_conditions true_step
        post_conditions = _list_field(
            node.get("post_conditions", []),
            f"[Structure] Node '{node_name}'.post_conditions",
            errors,
        )
        for i, pc in enumerate(post_conditions):
            if not isinstance(pc, dict):
                errors.append(
                    f"[Structure] Node '{node_name}'.post_conditions[{i}] must be an object. "
                    f"Got: {_type_name(pc)}."
                )
                continue
            ts = pc.get("true_step")
            if not ts:
                errors.append(
                    f"[Structure] Node '{node_name}'.post_conditions[{i}] is missing 'true_step'."
                )
            elif not isinstance(ts, str):
                errors.append(
                    f"[Structure] Node '{node_name}'.post_conditions[{i}].true_step must be a string. "
                    f"Got: {_type_name(ts)}."
                )
            elif ts != END_OF_FLOW and ts not in steps:
                errors.append(
                    f"[Structure] Node '{node_name}'.post_conditions[{i}].true_step = '{ts}' "
                    "does not exist in 'steps'."
                )

        # on_error references
        on_error = _dict_field(
            node.get("on_error", {}),
            f"[Structure] Node '{node_name}'.on_error",
            errors,
        )
        for code, target in on_error.items():
            if not isinstance(target, str):
                errors.append(
                    f"[Structure] Node '{node_name}'.on_error['{code}'] must be a string. "
                    f"Got: {_type_name(target)}."
                )
                continue
            if target != END_OF_FLOW and target not in steps:
                errors.append(
                    f"[Structure] Node '{node_name}'.on_error['{code}'] = '{target}' "
                    "does not exist in 'steps'."
                )

    # Reachability — BFS from current_step
    reachable: set[str] = set()
    queue = [current_step] if isinstance(current_step, str) and current_step in steps else []
    while queue:
        node_name = queue.pop(0)
        if node_name in reachable or node_name not in steps:
            continue
        reachable.add(node_name)
        node = steps[node_name]
        if not isinstance(node, dict):
            continue
        ds = node.get("default_step", "")
        if isinstance(ds, str) and ds in steps:
            queue.append(ds)
        for pc in node.get("post_conditions", []) if isinstance(node.get("post_conditions", []), list) else []:
            if not isinstance(pc, dict):
                continue
            ts = pc.get("true_step", "")
            if isinstance(ts, str) and ts in steps:
                queue.append(ts)
        for target in node.get("on_error", {}).values() if isinstance(node.get("on_error", {}), dict) else []:
            if isinstance(target, str) and target in steps:
                queue.append(target)

    orphans = set(steps.keys()) - reachable
    if orphans:
        warnings.append(
            f"[Structure] Orphan nodes (unreachable from '{current_step}'): "
            + ", ".join(sorted(str(orphan) for orphan in orphans))
        )

    # Check at least one path to end-of-flow
    has_terminal = any(_node_routes_to_end(node) for node in steps.values())
    if not has_terminal:
        errors.append(
            f"[Structure] No node routes to '{END_OF_FLOW}'. "
            "The workflow has no termination path."
        )

    # -------------------------------------------------------------------------
    # 3. NODE-LEVEL CHECKS
    # -------------------------------------------------------------------------

    for node_name, node in steps.items():
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")

        if node_type not in ("parameter", "api_call"):
            errors.append(
                f"[Node '{node_name}'] 'type' must be 'parameter' or 'api_call'. Got: '{node_type}'."
            )
            continue

        # --- PARAMETER NODE ---
        if node_type == "parameter" and node_name != SOFT_STORAGE:
            params = node.get("params", {})
            if not isinstance(params, dict):
                errors.append(f"[Node '{node_name}'] 'params' must be an object.")
                continue

            for param_key, param_def in params.items():
                prefix = f"[Node '{node_name}'.params.'{param_key}']"
                if not isinstance(param_def, dict):
                    errors.append(f"{prefix} must be an object. Got: {_type_name(param_def)}.")
                    continue

                # Required fields
                for required_field in ("llm_key", "datatype", "description", "is_optional"):
                    if required_field not in param_def:
                        errors.append(f"{prefix} Missing required field '{required_field}'.")

                # value must be ""
                if "value" not in param_def:
                    errors.append(f"{prefix} Missing 'value' field (must be present and set to \"\").")
                elif param_def["value"] != "":
                    errors.append(
                        f"{prefix} 'value' must be \"\" in the JSON definition — "
                        f"never pre-populate it. Got: '{param_def['value']}'."
                    )

                # datatype validity
                dt = param_def.get("datatype", "")
                if dt and not isinstance(dt, str):
                    errors.append(f"{prefix} 'datatype' must be a string. Got: {_type_name(dt)}.")
                elif dt and dt not in VALID_DATATYPES:
                    errors.append(
                        f"{prefix} 'datatype' = '{dt}' is not a recognised type. "
                        f"Valid types: {sorted(VALID_DATATYPES)}."
                    )

                # Validation object
                validation = param_def.get("validation")
                if validation:
                    if not isinstance(validation, dict):
                        errors.append(
                            f"{prefix}.validation must be an object. Got: {_type_name(validation)}."
                        )
                        continue

                    vf = validation.get("function", "")
                    if vf and not isinstance(vf, str):
                        errors.append(
                            f"{prefix}.validation 'function' must be a string. Got: {_type_name(vf)}."
                        )
                    elif vf and vf not in VALID_VALIDATION_FUNCTIONS:
                        errors.append(
                            f"{prefix}.validation 'function' = '{vf}' is not recognised. "
                            f"Valid: {sorted(VALID_VALIDATION_FUNCTIONS)}."
                        )
                    if vf == "range" and (not validation.get("start") or not validation.get("end")):
                        errors.append(
                            f"{prefix}.validation function='range' requires both 'start' and 'end'."
                        )

                    # retry_count should be set when validation is present
                    if "retry_count" not in param_def:
                        warnings.append(
                            f"{prefix} Has validation but no 'retry_count'. "
                            "Set retry_count to prevent infinite retry loops."
                        )

                # is_optional type check
                if "is_optional" in param_def and not isinstance(param_def["is_optional"], bool):
                    errors.append(f"{prefix} 'is_optional' must be a boolean (true or false).")

            # Post-conditions on parameter node
            _check_post_conditions(node_name, node.get("post_conditions", []), steps, errors, warnings)

        # --- API CALL NODE ---
        elif node_type == "api_call":
            prefix = f"[Node '{node_name}']"

            # api_endpoint
            ep = node.get("api_endpoint", "")
            if not ep:
                errors.append(f"{prefix} 'api_endpoint' is missing.")
            elif not isinstance(ep, str):
                errors.append(f"{prefix} 'api_endpoint' must be a string. Got: {_type_name(ep)}.")
            elif re.match(r"https?://", ep):
                errors.append(
                    f"{prefix} 'api_endpoint' must be a path only (no protocol). "
                    f"Got: '{ep}'. Use 'service/operation' format."
                )

            # response must be {}
            response = node.get("response")
            if response is None:
                errors.append(f"{prefix} 'response' field is missing (must be present as {{}}).")
            elif response != {}:
                warnings.append(
                    f"{prefix} 'response' should be {{}} in the JSON definition. "
                    "The engine populates it at runtime."
                )

            # on_error
            on_error = _dict_field(node.get("on_error", {}), f"{prefix}.on_error", errors)
            if "500" not in on_error:
                warnings.append(
                    f"{prefix} No 'on_error' mapping for code '500' (Server Error). "
                    "All api_call nodes should handle 500."
                )

            for code in on_error.keys():
                if code not in KNOWN_ERROR_CODES:
                    warnings.append(
                        f"{prefix}.on_error has non-standard code '{code}'. "
                        f"Known codes: {sorted(KNOWN_ERROR_CODES)}."
                    )

            # copy_params source steps
            copy_params = _list_field(node.get("copy_params", []), f"{prefix}.copy_params", errors)
            for i, cp_group in enumerate(copy_params):
                if not isinstance(cp_group, dict):
                    errors.append(f"{prefix}.copy_params[{i}] must be an object. Got: {_type_name(cp_group)}.")
                    continue
                keys = _list_field(cp_group.get("keys", []), f"{prefix}.copy_params[{i}].keys", errors)
                for j, key in enumerate(keys):
                    if not isinstance(key, dict):
                        errors.append(
                            f"{prefix}.copy_params[{i}].keys[{j}] must be an object. "
                            f"Got: {_type_name(key)}."
                        )
                        continue
                    src_step = key.get("step", "")
                    if src_step and not isinstance(src_step, str):
                        errors.append(
                            f"{prefix}.copy_params[{i}].keys[{j}].step must be a string. "
                            f"Got: {_type_name(src_step)}."
                        )
                    elif src_step and src_step != SOFT_STORAGE and src_step not in steps:
                        errors.append(
                            f"{prefix}.copy_params[{i}].keys[{j}].step = '{src_step}' "
                            "does not exist in 'steps'."
                        )

            # soft_storage_params source format
            soft_storage_params = _list_field(
                node.get("soft_storage_params", []),
                f"{prefix}.soft_storage_params",
                errors,
            )
            for i, ssp_group in enumerate(soft_storage_params):
                if not isinstance(ssp_group, dict):
                    errors.append(
                        f"{prefix}.soft_storage_params[{i}] must be an object. "
                        f"Got: {_type_name(ssp_group)}."
                    )
                    continue
                keys = _list_field(
                    ssp_group.get("keys", []),
                    f"{prefix}.soft_storage_params[{i}].keys",
                    errors,
                )
                for j, key in enumerate(keys):
                    if not isinstance(key, dict):
                        errors.append(
                            f"{prefix}.soft_storage_params[{i}].keys[{j}] must be an object. "
                            f"Got: {_type_name(key)}."
                        )
                        continue
                    src = key.get("source", "")
                    if src and not isinstance(src, str):
                        errors.append(
                            f"{prefix}.soft_storage_params[{i}].keys[{j}].source must be a string. "
                            f"Got: {_type_name(src)}."
                        )
                    elif src and not src.startswith("response"):
                        errors.append(
                            f"{prefix}.soft_storage_params[{i}].keys[{j}].source = '{src}' "
                            "must be 'response' or 'response.field_name'."
                        )

            # set_available_options target params
            set_available_options = _list_field(
                node.get("set_available_options", []),
                f"{prefix}.set_available_options",
                errors,
            )
            for i, sao in enumerate(set_available_options):
                if not isinstance(sao, dict):
                    errors.append(
                        f"{prefix}.set_available_options[{i}] must be an object. "
                        f"Got: {_type_name(sao)}."
                    )
                    continue
                set_step = sao.get("set_step", "")
                set_to = sao.get("set_to", "")
                if set_step and not isinstance(set_step, str):
                    errors.append(
                        f"{prefix}.set_available_options[{i}].set_step must be a string. "
                        f"Got: {_type_name(set_step)}."
                    )
                elif set_step and set_step not in steps:
                    errors.append(
                        f"{prefix}.set_available_options[{i}].set_step = '{set_step}' "
                        "does not exist in 'steps'."
                    )
                elif set_step and set_step in steps:
                    target_node = steps[set_step]
                    target_params = target_node.get("params", {}) if isinstance(target_node, dict) else {}
                    if set_to and not isinstance(set_to, str):
                        errors.append(
                            f"{prefix}.set_available_options[{i}].set_to must be a string. "
                            f"Got: {_type_name(set_to)}."
                        )
                    elif set_to and set_to not in target_params:
                        warnings.append(
                            f"{prefix}.set_available_options[{i}].set_to = '{set_to}' "
                            f"was not found in node '{set_step}'.params."
                        )

            # Post-conditions
            _check_post_conditions(node_name, node.get("post_conditions", []), steps, errors, warnings)

    return _format_report(errors, warnings)


def _load_workflow(workflow_json: Any, tool_name: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a workflow from a JSON string or already-decoded object."""
    if isinstance(workflow_json, dict):
        wf = workflow_json
    elif isinstance(workflow_json, (str, bytes, bytearray)):
        try:
            wf = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return (
                None,
                f"❌ INVALID JSON — {tool_name} cannot parse workflow:\n"
                f"  {e}\n\nFix the JSON syntax before running validation.",
            )
        except (TypeError, UnicodeDecodeError) as e:
            return (
                None,
                f"❌ INVALID JSON — {tool_name} expected a JSON object string. "
                f"Got {_type_name(workflow_json)}: {e}",
            )
    else:
        return (
            None,
            f"❌ INVALID WORKFLOW INPUT — {tool_name} expected a workflow JSON object "
            f"or JSON object string. Got: {_type_name(workflow_json)}.",
        )

    if not isinstance(wf, dict):
        return (
            None,
            f"❌ INVALID WORKFLOW — top-level workflow must be a JSON object. "
            f"Got: {_type_name(wf)}.",
        )

    return wf, None


def _type_name(value: Any) -> str:
    """Return a compact type name for validation messages."""
    return type(value).__name__


def _list_field(value: Any, field_path: str, errors: list) -> list:
    """Return list fields safely, recording a validation error for bad types."""
    if value is None:
        return []
    if isinstance(value, list):
        return value

    errors.append(f"{field_path} must be an array. Got: {_type_name(value)}.")
    return []


def _dict_field(value: Any, field_path: str, errors: list) -> dict:
    """Return object fields safely, recording a validation error for bad types."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value

    errors.append(f"{field_path} must be an object. Got: {_type_name(value)}.")
    return {}


def _post_conditions_for_read(node: dict) -> list:
    """Read post_conditions when rendering or traversing without recording errors."""
    post_conditions = node.get("post_conditions", [])
    return post_conditions if isinstance(post_conditions, list) else []


def _node_routes_to_end(node: Any) -> bool:
    """Return whether a node has any terminal outgoing edge."""
    if not isinstance(node, dict):
        return False
    return node.get("default_step") == END_OF_FLOW or any(
        isinstance(pc, dict) and pc.get("true_step") == END_OF_FLOW
        for pc in _post_conditions_for_read(node)
    )


def _check_post_conditions(
    node_name: str,
    post_conditions: list,
    steps: dict,
    errors: list,
    warnings: list,
) -> None:
    """Validate post-condition objects for a given node."""
    post_conditions = _list_field(
        post_conditions,
        f"[Node '{node_name}'].post_conditions",
        errors,
    )
    for i, pc in enumerate(post_conditions):
        prefix = f"[Node '{node_name}'.post_conditions[{i}]]"
        if not isinstance(pc, dict):
            errors.append(f"{prefix} must be an object. Got: {_type_name(pc)}.")
            continue

        lo = pc.get("logical_operator", "")
        if not isinstance(lo, str):
            errors.append(f"{prefix} 'logical_operator' must be a string. Got: {_type_name(lo)}.")
        elif lo not in VALID_LOGICAL_OPERATORS:
            errors.append(
                f"{prefix} 'logical_operator' must be 'and', 'or', or ''. Got: '{lo}'."
            )

        conditions = pc.get("conditions", [])
        conditions = _list_field(conditions, f"{prefix}.conditions", errors)
        if lo in ("and", "or") and len(conditions) > 2:
            errors.append(
                f"{prefix} logical_operator='{lo}' supports max 2 conditions. "
                f"Got {len(conditions)}."
            )
        if not conditions:
            errors.append(f"{prefix} 'conditions' array is empty.")

        for j, cond in enumerate(conditions):
            cprefix = f"{prefix}.conditions[{j}]"
            if not isinstance(cond, dict):
                errors.append(f"{cprefix} must be an object. Got: {_type_name(cond)}.")
                continue

            if not cond.get("key"):
                errors.append(f"{cprefix} Missing 'key'.")
            if not cond.get("step"):
                errors.append(f"{cprefix} Missing 'step'.")
            elif not isinstance(cond["step"], str):
                errors.append(f"{cprefix} 'step' must be a string. Got: {_type_name(cond['step'])}.")
            elif cond["step"] not in steps and cond["step"] != SOFT_STORAGE:
                errors.append(
                    f"{cprefix} 'step' = '{cond['step']}' does not exist in 'steps'."
                )

            op = cond.get("operator", "")
            if not isinstance(op, str):
                errors.append(f"{cprefix} 'operator' must be a string. Got: {_type_name(op)}.")
            elif op not in VALID_OPERATORS:
                errors.append(
                    f"{cprefix} 'operator' = '{op}' is not valid. "
                    f"Valid operators: {sorted(VALID_OPERATORS)}."
                )

            fn = cond.get("function", "")
            if fn and not isinstance(fn, str):
                errors.append(f"{cprefix} 'function' must be a string. Got: {_type_name(fn)}.")
            elif fn and fn not in VALID_VALIDATION_FUNCTIONS:
                errors.append(
                    f"{cprefix} 'function' = '{fn}' is not recognised. "
                    f"Valid: {sorted(VALID_VALIDATION_FUNCTIONS)}."
                )

            if fn == "range" and (not cond.get("start") or not cond.get("end")):
                errors.append(
                    f"{cprefix} function='range' requires both 'start' and 'end'."
                )

            source = cond.get("source", "")
            if source and not isinstance(source, str):
                errors.append(f"{cprefix} 'source' must be a string. Got: {_type_name(source)}.")
            elif source and not (source == "response" or source.startswith("response.")):
                errors.append(
                    f"{cprefix} 'source' = '{source}' is invalid. "
                    "Must be 'response' or 'response.field_name'."
                )


def _format_report(errors: list, warnings: list) -> str:
    """Format the validation result into a readable report."""
    lines = []
    max_items = 75

    if not errors and not warnings:
        lines.append("VALIDATION PASSED - No errors or warnings.")
        return "\n".join(lines)

    status = "VALIDATION FAILED" if errors else "VALIDATION PASSED WITH WARNINGS"
    lines.append(f"{status}")
    lines.append(f"Errors: {len(errors)}   Warnings: {len(warnings)}")
    lines.append("")

    if errors:
        lines.append("ERRORS (must fix before deploying)")
        for i, e in enumerate(errors[:max_items], 1):
            lines.append(f"  {i}. {e}")
        if len(errors) > max_items:
            lines.append(f"  ... {len(errors) - max_items} more error(s) omitted.")
        lines.append("")

    if warnings:
        lines.append("WARNINGS (should fix for production quality)")
        for i, w in enumerate(warnings[:max_items], 1):
            lines.append(f"  {i}. {w}")
        if len(warnings) > max_items:
            lines.append(f"  ... {len(warnings) - max_items} more warning(s) omitted.")
        lines.append("")

    if errors:
        lines.append("Fix all errors and re-run validate_workflow() before presenting to the user.")
    else:
        lines.append("All errors resolved. Review warnings before deploying to production.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# render_graph
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def render_graph(workflow_json: str) -> str:
    """Render a Tuva ITSM workflow JSON as a human-readable ASCII directed graph.

    Shows every node, its type, and all outgoing edges:
    - default_step edge (shown as →)
    - post_condition true_step edges (shown with condition summary)
    - on_error edges (shown with error code)

    Use this tool:
    - After assembling the workflow to visually verify the graph logic
    - After editing a workflow to confirm edges still make sense
    - When debugging to spot dead ends, loops, and missing paths
    - When presenting the workflow to a user so they can review the flow

    Args:
        workflow_json: The complete workflow JSON as a string.

    Returns:
        An ASCII graph showing all nodes and their connections.
    """
    wf, parse_error = _load_workflow(workflow_json, "render_graph")
    if parse_error:
        return parse_error

    steps: dict[str, Any] = wf.get("steps", {})
    if steps and not isinstance(steps, dict):
        return f"❌ Cannot render graph — 'steps' must be an object. Got: {_type_name(steps)}."
    if not steps:
        return "❌ Cannot render graph — 'steps' is empty or missing."

    current_step = wf.get("current_step", SOFT_STORAGE)
    if not isinstance(current_step, str):
        current_step = SOFT_STORAGE
    wf_name = wf.get("workflow_name", "(unnamed workflow)")
    if not isinstance(wf_name, str):
        wf_name = "(unnamed workflow)"

    lines = []
    lines.append("+----------------------------------------------------+")
    lines.append(f"  Workflow: {wf_name}")
    lines.append(f"  Start:    {current_step}")
    lines.append(f"  Nodes:    {len(steps)}")
    lines.append("+----------------------------------------------------+")
    lines.append("")

    # BFS order for display
    visited = []
    queue = [current_step] if current_step in steps else list(steps.keys())[:1]
    seen = set()
    while queue:
        node_name = queue.pop(0)
        if node_name in seen or node_name not in steps:
            continue
        seen.add(node_name)
        visited.append(node_name)
        node = steps[node_name]
        if not isinstance(node, dict):
            continue
        ds = node.get("default_step", "")
        if isinstance(ds, str) and ds in steps:
            queue.append(ds)
        for pc in _post_conditions_for_read(node):
            if not isinstance(pc, dict):
                continue
            ts = pc.get("true_step", "")
            if isinstance(ts, str) and ts in steps:
                queue.append(ts)
        on_error = node.get("on_error", {})
        for target in on_error.values() if isinstance(on_error, dict) else []:
            if isinstance(target, str) and target in steps:
                queue.append(target)

    # Add any orphans at the end
    for name in steps:
        if name not in seen:
            visited.append(name)

    for node_name in visited:
        node = steps[node_name]
        if not isinstance(node, dict):
            lines.append(f"+- [?] {node_name}")
            lines.append(f"|   invalid node definition: {_type_name(node)}")
            lines.append("+----------------------------------------------------")
            lines.append("")
            continue
        node_type = node.get("type", "?")
        type_icon = "PARAM" if node_type == "parameter" else "API"
        is_start = " <START>" if node_name == current_step else ""

        lines.append(f"+- {type_icon} [{node_type.upper()}] {node_name}{is_start}")

        # Parameter node: list params
        if node_type == "parameter" and node_name != SOFT_STORAGE:
            params = node.get("params", {})
            if isinstance(params, dict) and params:
                for pk, pv in params.items():
                    if not isinstance(pv, dict):
                        lines.append(f"|   param: {pk} [invalid: {_type_name(pv)}]")
                        continue
                    optional_tag = " (optional)" if pv.get("is_optional") else ""
                    validation_tag = " [validated]" if pv.get("validation") else ""
                    retry_tag = f" retry={pv['retry_count']}" if pv.get("retry_count") else ""
                    lines.append(
                        f"|   param: {pk} "
                        f"({pv.get('datatype', '?')}){optional_tag}{validation_tag}{retry_tag}"
                    )
        elif node_name == SOFT_STORAGE:
            lines.append("|   [global cross-workflow cache]")

        # API call node: endpoint
        if node_type == "api_call":
            ep = node.get("api_endpoint", "?")
            lines.append(f"|   endpoint: {ep}")
            silent = node.get("is_silent_step", {})
            if isinstance(silent, dict) and silent:
                silent_codes = [k for k, v in silent.items() if v]
                if silent_codes:
                    lines.append(f"|   silent on: {', '.join(silent_codes)}")

        # Post-conditions
        for pc in _post_conditions_for_read(node):
            if not isinstance(pc, dict):
                lines.append(f"|   invalid post_condition: {_type_name(pc)}")
                continue
            conditions = pc.get("conditions", [])
            lo = pc.get("logical_operator", "")
            true_step = pc.get("true_step", "?")

            if not isinstance(conditions, list):
                cond_str = f"invalid conditions: {_type_name(conditions)}"
            elif len(conditions) == 1 and isinstance(conditions[0], dict):
                c = conditions[0]
                cond_str = _condition_summary(c)
            else:
                parts = [
                    _condition_summary(c) if isinstance(c, dict) else f"invalid:{_type_name(c)}"
                    for c in conditions
                ]
                cond_str = f" {lo} ".join(parts)

            arrow_target = f"-> {true_step}" if true_step != END_OF_FLOW else "-> END"
            lines.append(f"|   if ({cond_str}) {arrow_target}")

        # on_error edges
        on_error = node.get("on_error", {})
        for code, target in on_error.items() if isinstance(on_error, dict) else []:
            target_str = "END" if target == END_OF_FLOW else target
            lines.append(f"|   on error {code} -> {target_str}")

        # default_step
        ds = node.get("default_step", "")
        if ds:
            ds_str = "END" if ds == END_OF_FLOW else ds
            lines.append(f"|   default -> {ds_str}")

        lines.append("+----------------------------------------------------")
        lines.append("")

    # Legend
    lines.append("Legend: PARAM = parameter node  API = api_call node  END = end-of-flow")
    return "\n".join(lines)


def _condition_summary(condition: dict) -> str:
    """Produce a short human-readable string for a single post-condition."""
    key = condition.get("key", "?")
    step = condition.get("step", "?")
    source = condition.get("source", "")
    fn = condition.get("function", "")
    op = condition.get("operator", "?")
    criteria = condition.get("criteria", "?")

    location = f"{step}.{source}" if source else step
    fn_part = f"{fn}(" if fn else ""
    fn_close = ")" if fn else ""

    return f"{fn_part}{location}.{key}{fn_close} {op} {criteria!r}"
