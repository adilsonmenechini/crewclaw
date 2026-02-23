# Self-Evolution Guide

CrewClaw agents have the unique capability to autonomously expand the system's functionality by creating new Agents, Tasks, and Skills. This process is called "Self-Evolution".

## How it Works

The assistant agent is equipped with the `evolution_skill`, which provides the necessary templates and instructions for creating new components. When you ask the agent to "create a new skill" or "add a specialist for X", it follows these steps:

1.  **Analyze**: Determines if a new Agent, Task, or Skill is required.
2.  **Draft**: Prepares the YAML or Markdown content.
3.  **Persist**: Uses the `file_write` tool to save the new component to the workspace.

## Workspace Structure

Agents MUST save new components to these specific directories for them to be detected:

| Component | Target Directory | File Format |
| :--- | :--- | :--- |
| **Agents** | `workspace/agents/` | `.yaml` |
| **Tasks** | `workspace/tasks/` | `.yaml` |
| **Skills** | `workspace/skills/` | `.md` |

## Example: Creating a Skill

If you ask: *"Create a skill called aws_helper to help with S3 bucket listings"*, the agent will:

1. Create a file at `workspace/skills/aws_helper.md`.
2. Write the skill content in Markdown format.
3. The next time an agent runs, this skill will be available in its knowledge base.

## Example: Creating a Specialist Agent

If you ask: *"I need a specialist in AWS security"*, the agent will:

1. Create a file at `workspace/agents/aws_security_expert.yaml`.
2. Define the role, goal, and backstory.
3. You can then run this agent using `crewclaw run -a aws_security_expert "..."`.

---

> [!TIP]
> You can also ask the agent to "improve itself" by refining its own `soul.md` or existing skills.
