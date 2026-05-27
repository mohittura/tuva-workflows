"""Deep Research Agent Example.

This module demonstrates building a research agent using the deepagents package
with custom tools for web search and strategic thinking.
"""
from workflow_agent.prompts import (
    NODE_BUILDER_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS as WF_SUBAGENT_DELEGATION_INSTRUCTIONS,
    WORKFLOW_BUILD_INSTRUCTIONS,
)
from workflow_agent.tools import (
    generate_uuid,
    render_graph,
    think_tool as wf_think_tool,
    validate_workflow,
)

__all__ = [
    # ── Workflow builder agent ───────────────────────────────────────────────
    "wf_think_tool",
    "generate_uuid",
    "validate_workflow",
    "render_graph",
    "WORKFLOW_BUILD_INSTRUCTIONS",
    "NODE_BUILDER_INSTRUCTIONS",
    "WF_SUBAGENT_DELEGATION_INSTRUCTIONS",
]
