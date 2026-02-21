# ADR-007: Dynamic Orchestration System

## Status
Proposed

## Context
The previous system relied on static configuration files or direct code instantiation for agents and tasks. This made it difficult for users to iterate quickly on agent definitions and task workflows without modifying the core codebase or complex JSON configs.

## Decision
We are implementing a dynamic orchestration system where:
1.  **Skills** (tools) are defined as Markdown files in `workspace/skills/` containing Python code.
2.  **Agents** are defined as YAML or Markdown files in `workspace/agents/` specifying roles, goals, and assigned skills.
3.  **Tasks** are defined as YAML or Markdown files in `workspace/tasks/` specifying descriptions, expected outputs, and assigned agents.

Loaders (`SkillsLoader`, `AgentsLoader`, `TasksLoader`) will dynamically read these directories and register components into the CrewAI ecosystem.

## Consequences
- **Pros**:
    - Faster iteration and prototyping.
    - Separation of agentic logic from application core.
    - Improved readability of agent personas and task assignments.
- **Cons**:
    - Security implications of executing dynamic code from Markdown skills (needs sandboxing).
    - Potential for runtime errors if configurations are invalid.
