"""Agent templates and shared utilities."""

from typing import Dict, Any, List
from crewai import Agent
from crewclaw.providers.crewai import LiteLLMForCrewAI
from crewclaw.agent.tools.crewai_tools import (
    WebSearchTool,
    WebFetchTool,
    FileReadToolCrewAI,
    FileWriteToolCrewAI,
    GrepToolCrewAI,
    DirectoryListToolCrewAI,
    MemorySearchToolCrewAI,
    ExecToolCrewAI,
)

def get_llm() -> LiteLLMForCrewAI:
    """Get shared LLM instance."""
    return LiteLLMForCrewAI()

# All available tools for template definitions
ALL_TOOLS_LIST = [
    "web_search", "web_fetch", "file_read", "file_write", 
    "grep", "ls", "memory_search", "shell"
]

# Actual tool objects for runtime (minimal set kept for backward compatibility)
def get_all_tools():
    return [
        WebSearchTool(),
        WebFetchTool(),
        FileReadToolCrewAI(),
        FileWriteToolCrewAI(),
        GrepToolCrewAI(),
        DirectoryListToolCrewAI(),
        MemorySearchToolCrewAI(),
        ExecToolCrewAI(),
    ]

# Core Templates
AGENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "assistant": {
        "role": "General Purpose AI Assistant",
        "goal": "Help the user with any request using available tools",
        "backstory": "You are a versatile and helpful AI assistant designed to follow instructions and provide high-quality results.",
        "tools": ["web_search", "web_fetch", "file_read"],
    },
    "researcher": {
        "role": "Senior Data Researcher",
        "goal": "Find and analyze the most relevant information on any topic",
        "backstory": "You are an expert researcher with a keen eye for detail and a talent for synthesizing complex information.",
        "tools": ["web_search", "web_fetch", "file_read"],
    },
    "writer": {
        "role": "Professional Content Writer",
        "goal": "Create clear, engaging, and accurate written content",
        "backstory": "You are a skilled writer who can transform raw data into compelling narratives.",
        "tools": ["file_write", "file_read"],
    },
    "sre": {
        "role": "Site Reliability Engineer",
        "goal": "Manage infrastructure, automate operations, and troubleshoot system issues",
        "backstory": "Expert SRE focused on reliability, security, and automation using shell commands and system analysis.",
        "tools": ["shell", "grep", "ls", "file_read"],
    },
    "analyzer": {
        "role": "Code & Data Analyst",
        "goal": "Deeply analyze codebases or datasets to find patterns and bugs",
        "backstory": "Meticulous analyst with deep technical knowledge and a systematic approach to problem solving.",
        "tools": ["grep", "ls", "file_read", "memory_search"],
    },
    "router": {
        "role": "Crew Coordinator",
        "goal": "Orchestrate specialized agents to complete complex multi-step goals",
        "backstory": "Intelligent coordinator that understands human intent and delegates tasks to the best specialists.",
        "tools": ["web_search", "file_read"],
        "allow_delegation": True,
    }
}

def get_template(name: str) -> Dict[str, Any]:
    """Get an agent template by name."""
    from crewclaw.config import get_config
    config = get_config()
    
    tpl = AGENT_TEMPLATES.get(name, AGENT_TEMPLATES["assistant"]).copy()
    
    # Inject configured AI name into backstory or role if it's the main assistant
    ai_name = config.get("ai.name")
    if ai_name and ai_name != "CrewClaw":
        if "backstory" in tpl:
            tpl["backstory"] = f"Your name is {ai_name}. {tpl['backstory']}"
            
    return tpl

def find_best_template(objective: str) -> Dict[str, Any]:
    """Find the most suitable template based on a description string."""
    obj_lower = objective.lower()
    if any(k in obj_lower for k in ["se", "infra", "ops", "shell", "docker", "k8s", "linux", "cloud"]):
        return AGENT_TEMPLATES["sre"]
    if any(k in obj_lower for k in ["research", "search", "find", "web", "internet"]):
        return AGENT_TEMPLATES["researcher"]
    if any(k in obj_lower for k in ["write", "doc", "text", "content", "blog"]):
        return AGENT_TEMPLATES["writer"]
    if any(k in obj_lower for k in ["analyze", "code", "bug", "pattern", "data"]):
        return AGENT_TEMPLATES["analyzer"]
    
    return AGENT_TEMPLATES["assistant"]

# Backward compatibility layer
def create_researcher_agent() -> Agent:
    tpl = get_template("researcher")
    from crewclaw.config import get_config
    ai_name = get_config().get("ai.name", "CrewClaw")
    return Agent(
        role=f"{ai_name} - {tpl['role']}",
        goal=tpl["goal"],
        backstory=f"You are {ai_name}. {tpl['backstory']}",
        llm=get_llm(),
        tools=[WebSearchTool(), WebFetchTool(), FileReadToolCrewAI()]
    )

def create_writer_agent() -> Agent:
    tpl = get_template("writer")
    from crewclaw.config import get_config
    ai_name = get_config().get("ai.name", "CrewClaw")
    return Agent(
        role=f"{ai_name} - {tpl['role']}",
        goal=tpl["goal"],
        backstory=f"You are {ai_name}. {tpl['backstory']}",
        llm=get_llm(),
        tools=[FileWriteToolCrewAI(), FileReadToolCrewAI()]
    )

def create_router_agent() -> Agent:
    tpl = get_template("router")
    from crewclaw.config import get_config
    config = get_config()
    ai_name = config.get("ai.name", "CrewClaw")
    objective = config.get("ai.objective", "Assist with SRE, automation and task management")
    return Agent(
        role=f"{ai_name} - {tpl['role']}",
        goal=objective,
        backstory=f"You are {ai_name}. {tpl['backstory']}",
        llm=get_llm(),
        tools=get_all_tools(),
        allow_delegation=True
    )

def get_sample_agent(name: str) -> Agent:
    """Legacy helper to get an agent. Prefers workspace instead if possible."""
    from crewclaw.config import get_config
    config = get_config()
    ai_name = config.get("ai.name", "CrewClaw")
    objective = config.get("ai.objective", "Assist with SRE, automation and task management")

    if name == "router":
        tpl = AGENT_TEMPLATES["router"]
        return Agent(
            role=f"{ai_name} - {tpl['role']}",
            goal=objective,
            backstory=f"You are {ai_name}. {tpl['backstory']}",
            llm=get_llm(),
            tools=get_all_tools(),
            allow_delegation=True
        )
    
    if name == "researcher": return create_researcher_agent()
    if name == "writer": return create_writer_agent()
    
    tpl = get_template(name)
    role = tpl["role"]
    goal = tpl["goal"]
    backstory = tpl["backstory"]

    # For the general 'assistant' or 'router', use the configured objective
    if name in ["assistant", "router"]:
        goal = objective

    return Agent(
        role=f"{ai_name} - {role}",
        goal=goal,
        backstory=f"You are {ai_name}. {backstory}",
        llm=get_llm()
    )

# Registry for legacy references
SAMPLE_AGENTS = {k: lambda n=k: get_sample_agent(n) for k in AGENT_TEMPLATES.keys()}
