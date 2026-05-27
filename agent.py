"""Tuva ITSM Workflow Builder Agent — LangGraph deployment entrypoint."""

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import AzureChatOpenAI

from workflow_agent.prompts import (
    NODE_BUILDER_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    WORKFLOW_BUILD_INSTRUCTIONS,
)
from workflow_agent.tools import generate_uuid, render_graph, think_tool, validate_workflow

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

max_concurrent_node_builders = 2
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
        max_concurrent_node_builders=max_concurrent_node_builders,
        max_builder_iterations=max_builder_iterations,
    )
)

# ---------------------------------------------------------------------------
# Node-builder sub-agent
# ---------------------------------------------------------------------------

node_builder_sub_agent = {
    "name": "node-builder",
    "description": (
        "Delegate workflow node writing to this sub-agent. "
        "Give it a precise spec: node names, parameter details, API endpoints, "
        "error codes, copy_params sources, and any special patterns needed. "
        "It returns a JSON fragment (the nodes object) plus a Node Map summary. "
        "Do NOT ask it to assemble the full workflow — only specific sections."
    ),
    "system_prompt": NODE_BUILDER_INSTRUCTIONS,
    "tools": [think_tool, generate_uuid, validate_workflow, render_graph],
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
    tools=[think_tool, generate_uuid, validate_workflow, render_graph],
    system_prompt=INSTRUCTIONS,
    subagents=[node_builder_sub_agent],
    backend=FilesystemBackend(root_dir="./files"),
    skills=["./skills/"],
)
