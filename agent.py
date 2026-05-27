"""Tuva ITSM Workflow Builder Agent — LangGraph deployment entrypoint."""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import AzureChatOpenAI

from workflow_agent.prompts import (
    DECISIONS_DOCUMENT_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    WORKFLOW_JSON_BUILDER_INSTRUCTIONS,
    WORKFLOW_BUILD_INSTRUCTIONS,
)
from workflow_agent.tools import (
    delete_json_path,
    generate_uuid,
    merge_json_object,
    read_json_path,
    think_tool,
    validate_json_syntax,
    write_json_path,
)

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

max_concurrent_json_builders = 2
max_builder_iterations = 5

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

INSTRUCTIONS = (
    WORKFLOW_BUILD_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_node_builders=max_concurrent_json_builders,
        max_builder_iterations=max_builder_iterations,
    )
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

workflow_json_tools = [
    think_tool,
    generate_uuid,
    validate_json_syntax,
    read_json_path,
    write_json_path,
    merge_json_object,
    delete_json_path,
]


# ---------------------------------------------------------------------------
# Workflow JSON builder sub-agent
# ---------------------------------------------------------------------------

workflow_json_builder_sub_agent = {
    "name": "workflow-json-builder",
    "description": (
        "Delegate ITSM workflow JSON construction and targeted edits to this sub-agent. "
        "It must follow the ITSM-workflows skill and may use only generic JSON tools "
        "for parsing and path-based edits."
    ),
    "system_prompt": WORKFLOW_JSON_BUILDER_INSTRUCTIONS,
    "tools": workflow_json_tools,
}


# ---------------------------------------------------------------------------
# Decisions document sub-agent
# ---------------------------------------------------------------------------

decisions_writer_sub_agent = {
    "name": "decisions-writer",
    "description": (
        "Delegate creation of the mandatory DECISIONS.md companion document. "
        "It must follow Phase 6 of the ITSM-workflows skill."
    ),
    "system_prompt": DECISIONS_DOCUMENT_INSTRUCTIONS,
    "tools": [validate_json_syntax, read_json_path],
}

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

model = AzureChatOpenAI(
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    temperature=0.0,
)

# ---------------------------------------------------------------------------
# Agent — exported as 'agent' for langgraph.json
# ---------------------------------------------------------------------------

agent = create_deep_agent(
    model=model,
    tools=workflow_json_tools,
    system_prompt=INSTRUCTIONS,
    subagents=[workflow_json_builder_sub_agent, decisions_writer_sub_agent],
    backend=FilesystemBackend(root_dir="./files"),
    skills=["./skills/"],
)
