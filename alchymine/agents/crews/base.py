"""Lightweight CrewAI-compatible abstractions for domain agents.

Defines DomainAgent, AgentTask, and SystemCrew — the spoke layer of
Alchymine's hub-and-spoke architecture. These mirror CrewAI's API
without requiring the heavy dependency.

Each DomainAgent wraps one or more engine function calls and produces
a structured output dict. SystemCrew orchestrates sequential execution
of tasks, passing context between agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ─── Agent roles ────────────────────────────────────────────────────


class AgentRole(StrEnum):
    """Domain agent roles within a system crew."""

    ANALYST = "analyst"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"
    GUIDE = "guide"
    DETECTOR = "detector"
    CALCULATOR = "calculator"


# ─── Domain agent ───────────────────────────────────────────────────


@dataclass
class DomainAgent:
    """A domain-specific agent within a system crew.

    Attributes
    ----------
    name:
        Human-readable agent name (e.g., "NumerologyAnalyst").
    role:
        The agent's role within the crew.
    goal:
        What this agent aims to accomplish.
    backstory:
        Context for the agent's expertise and perspective.
    system:
        Which Alchymine system this agent belongs to.
    tools:
        List of engine tool/function identifiers this agent uses.
    """

    name: str
    role: AgentRole
    goal: str
    backstory: str
    system: str
    tools: list[str] = field(default_factory=list)

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute this agent's task with given context.

        Subclasses must override this to call the appropriate engine
        functions.

        Parameters
        ----------
        context:
            Input data dict — typically contains user profile fields,
            prior agent outputs, and request parameters.

        Returns
        -------
        dict[str, Any]
            Output data dict to merge into the crew's running context.

        Raises
        ------
        NotImplementedError
            If the subclass has not overridden this method.
        """
        raise NotImplementedError(f"{self.name} must implement execute()")


# ─── Agent task ─────────────────────────────────────────────────────


@dataclass
class AgentTask:
    """A task assigned to a domain agent.

    Attributes
    ----------
    name:
        Task identifier (e.g., "calculate_numerology").
    description:
        What the task does.
    agent:
        The DomainAgent responsible for this task.
    expected_output:
        Description of the expected output format.
    """

    name: str
    description: str
    agent: DomainAgent
    expected_output: str


# ─── System crew ────────────────────────────────────────────────────


@dataclass
class SystemCrew:
    """A crew of agents for one Alchymine system.

    Executes tasks in sequence, threading context between agents so
    downstream agents can build on upstream results.

    Attributes
    ----------
    name:
        The system/crew name (e.g., "intelligence").
    agents:
        All agents in this crew.
    tasks:
        Ordered list of tasks to execute.
    """

    name: str
    agents: list[DomainAgent] = field(default_factory=list)
    tasks: list[AgentTask] = field(default_factory=list)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute all tasks in sequence, passing context between agents.

        Each task's agent is invoked with the current context. On
        success the result is merged into context for downstream tasks.
        On failure the error is recorded and execution continues.

        Parameters
        ----------
        context:
            Initial context dict (typically user profile + request data).

        Returns
        -------
        dict[str, Any]
            Mapping of task name to that task's result dict. Failed
            tasks have an ``error`` key in their result.
        """
        results: dict[str, Any] = {}
        for task in self.tasks:
            try:
                result = task.agent.execute(context)
                results[task.name] = result
                context.update(result)
            except Exception as exc:
                logger.warning(
                    "Task %s failed in crew %s: %s",
                    task.name,
                    self.name,
                    exc,
                )
                results[task.name] = {"error": str(exc)}
        return results
