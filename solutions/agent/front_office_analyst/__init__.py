"""Front Office Analyst — MLB Race to October Lab Task 4.

This package exposes the root_agent that ADK CLI tools (`adk web`,
`adk run`) discover when invoked from the parent `agent/` directory.
"""

from .agent import root_agent

__all__ = ["root_agent"]
