"""Generic helper tools for the ITSM workflow agent.

These tools intentionally do not encode the Tuva ITSM workflow schema. Workflow
creation, workflow validation, and DECISIONS.md content rules are owned by the
`ITSM-workflows` skill and its reference documents. The tools here only provide
safe JSON parsing and path-based editing primitives.
"""

import json
import re
import uuid
from typing import Any

from langchain_core.tools import tool


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Record deliberate reasoning before a workflow or JSON editing decision.

    Use this to reason through the current task while applying the
    `ITSM-workflows` skill references. This tool does not validate workflow
    semantics; it only records the reasoning step.

    Args:
        reflection: Detailed reasoning about the current decision.

    Returns:
        Confirmation that the reflection was recorded.
    """
    return f"[think_tool] Reflection recorded:\n{reflection}"


@tool(parse_docstring=True)
def generate_uuid() -> str:
    """Generate a UUID4 value.

    Use this when the `ITSM-workflows` skill requires a new `workflow_id`.

    Returns:
        A UUID4 hex string without hyphens.
    """
    return uuid.uuid4().hex


@tool(parse_docstring=True)
def validate_json_syntax(json_text: str, require_object: bool = False) -> str:
    """Validate generic JSON syntax and summarize the parsed shape.

    This only checks JSON syntax and the optional top-level object requirement.
    Use the `ITSM-workflows` skill validation checklist for workflow correctness.

    Args:
        json_text: JSON content as a string.
        require_object: When true, the top-level JSON value must be an object.

    Returns:
        A syntax validation report with the top-level type and basic counts.
    """
    data, parse_error = _load_json_value(json_text, "validate_json_syntax")
    if parse_error:
        return parse_error

    if require_object and not isinstance(data, dict):
        return (
            "INVALID JSON SHAPE\n"
            f"Top-level value must be an object. Got: {_type_name(data)}."
        )

    if isinstance(data, dict):
        keys = ", ".join(str(k) for k in list(data.keys())[:20])
        extra = "" if len(data) <= 20 else f", ... {len(data) - 20} more"
        return (
            "VALID JSON\n"
            "Top-level type: object\n"
            f"Top-level keys ({len(data)}): {keys}{extra}"
        )

    if isinstance(data, list):
        return f"VALID JSON\nTop-level type: array\nItems: {len(data)}"

    return f"VALID JSON\nTop-level type: {_type_name(data)}\nValue: {data!r}"


@tool(parse_docstring=True)
def read_json_path(json_text: str, path: str) -> str:
    """Read a nested value from JSON using a dot path or JSON Pointer.

    Path examples:
    - Dot path: steps.collect_issue_details.params.priority
    - List index: post_conditions[0].true_step
    - JSON Pointer: /steps/collect_issue_details/default_step
    - Empty path: returns the whole JSON document.

    Args:
        json_text: JSON content as a string.
        path: Dot path, bracket path, JSON Pointer, or empty string for root.

    Returns:
        The selected value formatted as JSON, or a clear path error.
    """
    data, parse_error = _load_json_value(json_text, "read_json_path")
    if parse_error:
        return parse_error

    tokens, path_error = _parse_json_path(path)
    if path_error:
        return path_error

    value, read_error = _get_json_path(data, tokens)
    if read_error:
        return read_error

    return json.dumps(value, indent=2, ensure_ascii=False)


@tool(parse_docstring=True)
def write_json_path(
    json_text: str,
    path: str,
    value_json: str,
    create_missing: bool = False,
) -> str:
    """Replace or create a nested JSON value at a path.

    The replacement value must itself be valid JSON. Use this only as a precise
    editing primitive; decide whether the edit is valid by following the
    `ITSM-workflows` skill references.

    Args:
        json_text: Original JSON content as a string.
        path: Dot path, bracket path, JSON Pointer, or empty string for root.
        value_json: Replacement value encoded as JSON.
        create_missing: Create missing object keys along the path when true.

    Returns:
        The full updated JSON document, pretty-printed.
    """
    data, parse_error = _load_json_value(json_text, "write_json_path")
    if parse_error:
        return parse_error

    value, value_error = _load_json_value(value_json, "write_json_path value_json")
    if value_error:
        return value_error

    tokens, path_error = _parse_json_path(path)
    if path_error:
        return path_error

    if not tokens:
        return json.dumps(value, indent=2, ensure_ascii=False)

    write_error = _set_json_path(data, tokens, value, create_missing)
    if write_error:
        return write_error

    return json.dumps(data, indent=2, ensure_ascii=False)


@tool(parse_docstring=True)
def merge_json_object(json_text: str, path: str, patch_json: str) -> str:
    """Merge a JSON object chunk into an object at the selected path.

    Existing keys at that object path are updated or added. Nested objects are
    merged recursively; arrays and scalar values are replaced.

    Args:
        json_text: Original JSON content as a string.
        path: Dot path, bracket path, JSON Pointer, or empty string for root.
        patch_json: JSON object to merge into the selected object.

    Returns:
        The full updated JSON document, pretty-printed.
    """
    data, parse_error = _load_json_value(json_text, "merge_json_object")
    if parse_error:
        return parse_error

    patch, patch_error = _load_json_value(patch_json, "merge_json_object patch_json")
    if patch_error:
        return patch_error
    if not isinstance(patch, dict):
        return f"INVALID PATCH - patch_json must be an object. Got: {_type_name(patch)}."

    tokens, path_error = _parse_json_path(path)
    if path_error:
        return path_error

    target, read_error = _get_json_path(data, tokens)
    if read_error:
        return read_error
    if not isinstance(target, dict):
        location = path or "<root>"
        return f"INVALID MERGE TARGET - {location} must be an object. Got: {_type_name(target)}."

    _deep_merge(target, patch)
    return json.dumps(data, indent=2, ensure_ascii=False)


@tool(parse_docstring=True)
def delete_json_path(json_text: str, path: str) -> str:
    """Delete a nested key or list item from JSON.

    Args:
        json_text: Original JSON content as a string.
        path: Dot path, bracket path, or JSON Pointer to the value to delete.

    Returns:
        The full updated JSON document, pretty-printed.
    """
    data, parse_error = _load_json_value(json_text, "delete_json_path")
    if parse_error:
        return parse_error

    tokens, path_error = _parse_json_path(path)
    if path_error:
        return path_error
    if not tokens:
        return "INVALID DELETE PATH - Refusing to delete the root document."

    delete_error = _delete_json_path(data, tokens)
    if delete_error:
        return delete_error

    return json.dumps(data, indent=2, ensure_ascii=False)


def _load_json_value(json_text: Any, tool_name: str) -> tuple[Any, str | None]:
    """Parse any JSON value from a string or return an already-decoded value."""
    if isinstance(json_text, (dict, list, str, int, float, bool)) or json_text is None:
        if isinstance(json_text, str):
            try:
                return json.loads(json_text), None
            except json.JSONDecodeError as e:
                return (
                    None,
                    f"INVALID JSON - {tool_name} cannot parse input:\n"
                    f"  {e}\n\nFix the JSON syntax and try again.",
                )
        return json_text, None

    if isinstance(json_text, (bytes, bytearray)):
        try:
            return json.loads(json_text), None
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return (
                None,
                f"INVALID JSON - {tool_name} cannot parse input:\n"
                f"  {e}\n\nFix the JSON syntax and try again.",
            )

    return (
        None,
        f"INVALID JSON INPUT - {tool_name} expected JSON text or a decoded JSON value. "
        f"Got: {_type_name(json_text)}.",
    )


def _parse_json_path(path: str) -> tuple[list[str | int], str | None]:
    """Parse dot/bracket path or JSON Pointer into navigation tokens."""
    if path is None:
        return [], "INVALID PATH - path cannot be null."
    if not isinstance(path, str):
        return [], f"INVALID PATH - path must be a string. Got: {_type_name(path)}."
    if path == "":
        return [], None

    if path.startswith("/"):
        tokens: list[str | int] = []
        for part in path.split("/")[1:]:
            tokens.append(part.replace("~1", "/").replace("~0", "~"))
        return tokens, None

    tokens = []
    current = ""
    i = 0
    while i < len(path):
        char = path[i]
        if char == ".":
            if current:
                tokens.append(current)
                current = ""
            i += 1
            continue
        if char == "[":
            if current:
                tokens.append(current)
                current = ""
            end = path.find("]", i)
            if end == -1:
                return [], f"INVALID PATH - missing closing ']' in {path!r}."
            index_text = path[i + 1:end].strip()
            if not index_text:
                return [], f"INVALID PATH - empty list index in {path!r}."
            if not re.fullmatch(r"-?\d+", index_text):
                return [], f"INVALID PATH - list index must be an integer. Got: {index_text!r}."
            tokens.append(int(index_text))
            i = end + 1
            continue
        current += char
        i += 1

    if current:
        tokens.append(current)

    return tokens, None


def _get_json_path(data: Any, tokens: list[str | int]) -> tuple[Any, str | None]:
    """Read a nested JSON value by parsed path tokens."""
    current = data
    traversed: list[str] = []

    for token in tokens:
        traversed.append(str(token))
        if isinstance(token, int) or (isinstance(current, list) and _is_int_text(token)):
            index = token if isinstance(token, int) else int(token)
            if not isinstance(current, list):
                return None, (
                    f"PATH ERROR - {'.'.join(traversed[:-1]) or '<root>'} "
                    f"is not an array. Got: {_type_name(current)}."
                )
            if index < 0 or index >= len(current):
                return None, (
                    f"PATH ERROR - index {index} out of range at "
                    f"{'.'.join(traversed[:-1]) or '<root>'}."
                )
            current = current[index]
            continue

        if not isinstance(current, dict):
            return None, (
                f"PATH ERROR - {'.'.join(traversed[:-1]) or '<root>'} "
                f"is not an object. Got: {_type_name(current)}."
            )
        if token not in current:
            return None, f"PATH ERROR - key '{token}' not found at {'.'.join(traversed[:-1]) or '<root>'}."
        current = current[token]

    return current, None


def _set_json_path(data: Any, tokens: list[str | int], value: Any, create_missing: bool) -> str | None:
    """Set a nested JSON value by parsed path tokens."""
    parent = data
    traversed: list[str] = []

    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        traversed.append(str(token))

        if isinstance(token, int) or (isinstance(parent, list) and _is_int_text(token)):
            list_index = token if isinstance(token, int) else int(token)
            if not isinstance(parent, list):
                return (
                    f"PATH ERROR - {'.'.join(traversed[:-1]) or '<root>'} "
                    f"is not an array. Got: {_type_name(parent)}."
                )
            if list_index < 0 or list_index >= len(parent):
                return f"PATH ERROR - index {list_index} out of range at {'.'.join(traversed[:-1]) or '<root>'}."
            parent = parent[list_index]
            continue

        if not isinstance(parent, dict):
            return (
                f"PATH ERROR - {'.'.join(traversed[:-1]) or '<root>'} "
                f"is not an object. Got: {_type_name(parent)}."
            )
        if token not in parent:
            if not create_missing:
                return f"PATH ERROR - key '{token}' not found at {'.'.join(traversed[:-1]) or '<root>'}."
            parent[token] = [] if isinstance(next_token, int) else {}
        parent = parent[token]

    final_token = tokens[-1]
    if isinstance(final_token, int) or (isinstance(parent, list) and _is_int_text(final_token)):
        list_index = final_token if isinstance(final_token, int) else int(final_token)
        if not isinstance(parent, list):
            return f"PATH ERROR - target parent is not an array. Got: {_type_name(parent)}."
        if list_index < 0 or list_index >= len(parent):
            return f"PATH ERROR - index {list_index} out of range at target parent."
        parent[list_index] = value
        return None

    if not isinstance(parent, dict):
        return f"PATH ERROR - target parent is not an object. Got: {_type_name(parent)}."
    parent[final_token] = value
    return None


def _delete_json_path(data: Any, tokens: list[str | int]) -> str | None:
    """Delete a nested JSON value by parsed path tokens."""
    parent, read_error = _get_json_path(data, tokens[:-1])
    if read_error:
        return read_error

    final_token = tokens[-1]
    if isinstance(final_token, int) or (isinstance(parent, list) and _is_int_text(final_token)):
        list_index = final_token if isinstance(final_token, int) else int(final_token)
        if not isinstance(parent, list):
            return f"PATH ERROR - target parent is not an array. Got: {_type_name(parent)}."
        if list_index < 0 or list_index >= len(parent):
            return f"PATH ERROR - index {list_index} out of range at target parent."
        del parent[list_index]
        return None

    if not isinstance(parent, dict):
        return f"PATH ERROR - target parent is not an object. Got: {_type_name(parent)}."
    if final_token not in parent:
        return f"PATH ERROR - key '{final_token}' not found at target parent."
    del parent[final_token]
    return None


def _is_int_text(value: Any) -> bool:
    """Return true when value is a string representation of an integer."""
    return isinstance(value, str) and re.fullmatch(r"-?\d+", value) is not None


def _deep_merge(target: dict, patch: dict) -> None:
    """Recursively merge patch into target."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _type_name(value: Any) -> str:
    """Return a compact type name for validation messages."""
    return type(value).__name__
