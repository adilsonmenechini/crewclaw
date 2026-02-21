"""Sample agent definitions."""

from crewai import Agent

from ..memory.crewai_llm import LiteLLMForCrewAI
from ..tools.crewai_tools import (
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


# All available tools
ALL_TOOLS = [
    WebSearchTool(),
    WebFetchTool(),
    FileReadToolCrewAI(),
    FileWriteToolCrewAI(),
    GrepToolCrewAI(),
    DirectoryListToolCrewAI(),
    MemorySearchToolCrewAI(),
    ExecToolCrewAI(),  # Shell commands
]


def create_router_agent() -> Agent:
    """Create a router agent that delegates to the correct sub-agent.

    This agent automatically analyzes the task and delegates to the appropriate
    specialist agent using CrewAI's delegation feature.

    The sub-agents must be included in a Crew with this agent for delegation to work.
    Use create_router_crew() to get a properly configured crew.

    Returns:
        Router Agent with delegation capability.
    """
    return Agent(
        role="AI Assistant Coordinator",
        goal="Analyze user requests and delegate to the most appropriate specialist agent",
        backstory="""You are an intelligent coordinator that analyzes user tasks and 
automatically delegates to the best specialist agent.

Available specialists (you can delegate to):
- researcher: For web searches, information gathering, fact finding
- writer: For creating/editing documents, content, markdown files  
- analyzer: For code analysis, debugging, finding patterns in code
- sre: For DevOps tasks, shell commands, system administration
- librarian: For research on external libraries, documentation, best practices

When you need more information, ask the user clarifying questions.
When the task fits a specialist, delegate using the delegation tools.""",
        llm=get_llm(),
        verbose=False,
        tools=ALL_TOOLS,
        allow_delegation=True,  # Enable delegation to sub-agents
    )


def create_router_crew():
    """Create a crew with router and all sub-agents for delegation.

    Returns:
        tuple: (router_agent, list of sub_agents)
    """

    # Sub-agents (specialists)
    researcher = Agent(
        role="Data Researcher",
        goal="Find and analyze information from web searches",
        backstory="Expert at finding and synthesizing information from multiple sources.",
        llm=get_llm(),
        tools=[WebSearchTool(), WebFetchTool(), FileReadToolCrewAI()],
        allow_delegation=False,
    )

    writer = Agent(
        role="Content Writer",
        goal="Create clear, engaging written content",
        backstory="Professional writer skilled in creating markdown content.",
        llm=get_llm(),
        tools=[FileWriteToolCrewAI(), FileReadToolCrewAI()],
        allow_delegation=False,
    )

    analyzer = Agent(
        role="Code Analyst",
        goal="Analyze code, find patterns, and debug issues",
        backstory="Expert developer good at understanding codebases and finding bugs.",
        llm=get_llm(),
        tools=[FileReadToolCrewAI(), GrepToolCrewAI(), DirectoryListToolCrewAI()],
        allow_delegation=False,
    )

    sre_agent = Agent(
        role="SRE Assistant",
        goal="Help with DevOps, system administration, and infrastructure tasks",
        backstory="Experienced SRE skilled in shell commands, monitoring, and troubleshooting.",
        llm=get_llm(),
        tools=ALL_TOOLS,
        allow_delegation=False,
    )

    librarian = Agent(
        role="Research Specialist",
        goal="Find external documentation and code patterns",
        backstory="Expert at researching libraries, frameworks, and best practices.",
        llm=get_llm(),
        tools=[WebSearchTool(), WebFetchTool(), FileReadToolCrewAI(), GrepToolCrewAI()],
        allow_delegation=False,
    )

    # Router agent
    router = create_router_agent()

    sub_agents = [researcher, writer, analyzer, sre_agent, librarian]

    return router, sub_agents


def create_researcher_agent() -> Agent:
    """Create a researcher agent with web search.

    Returns:
        Researcher Agent.
    """
    return Agent(
        role="Senior Data Researcher",
        goal="Find and analyze the most relevant information on any topic",
        backstory="""You are an expert researcher with a keen eye for detail.
        You excel at finding unique insights and presenting them clearly.
        Your strength is synthesizing complex information from multiple sources.""",
        llm=get_llm(),
        verbose=False,
        tools=[
            WebSearchTool(),
            WebFetchTool(),
            FileReadToolCrewAI(),
        ],
    )


def create_simple_agent() -> Agent:
    """Create a simple agent without web search (no API keys needed).

    Returns:
        Simple Agent.
    """
    return Agent(
        role="AI Assistant",
        goal="Help the user with their questions",
        backstory="""You are a helpful AI assistant that can answer questions
        and help with various tasks. You provide clear and concise responses.""",
        llm=get_llm(),
        verbose=False,
    )


def create_writer_agent() -> Agent:
    """Create a writer agent.

    Returns:
        Writer Agent.
    """
    return Agent(
        role="Professional Content Writer",
        goal="Create clear, engaging content based on research",
        backstory="""You are an experienced writer known for transforming
        complex information into compelling narratives.
        You have a talent for making technical topics accessible.""",
        llm=get_llm(),
        verbose=False,
        tools=[
            FileWriteToolCrewAI(),
            FileReadToolCrewAI(),
        ],
    )


def create_analyzer_agent() -> Agent:
    """Create an analyzer agent.

    Returns:
        Analyzer Agent.
    """
    return Agent(
        role="Data Analyst",
        goal="Analyze data and provide actionable insights",
        backstory="""You are a meticulous analyst with expertise in identifying
        patterns and trends. You excel at turning raw data into
        meaningful conclusions and recommendations.""",
        llm=get_llm(),
        verbose=False,
        tools=[
            FileReadToolCrewAI(),
            GrepToolCrewAI(),
        ],
    )


def create_full_agent() -> Agent:
    """Create a full-featured agent with all tools.

    Returns:
        Full Agent with all capabilities.
    """
    return Agent(
        role="Full Stack AI Assistant",
        goal="Accomplish any task using the available tools",
        backstory="""You are a versatile AI assistant with access to a wide
        range of tools. You can search the web, read and write files,
        search file contents, list directories, and execute shell commands
        when needed. Always choose the most appropriate tool for the task.""",
        llm=get_llm(),
        verbose=False,
        tools=ALL_TOOLS,
    )


def create_sre_agent() -> Agent:
    """Create an SRE (Site Reliability Engineer) agent.

    Based on docs/old/agents/AGENTS.md

    Returns:
        SRE Agent.
    """
    return Agent(
        role="SRE AI Assistant",
        goal="Help with site reliability, DevOps, and system administration tasks",
        backstory="""You are a helpful SRE AI assistant. Be concise, accurate, and efficient.

You are proactive - you don't just wait for commands, you identify issues and suggest fixes.
You verify everything - always confirm changes work before reporting completion.
You document your work - use MEMORY.md for important discoveries.
You know when to escalate - ask for clarification when needed.
Security first - follow shell command allowlist and workspace restrictions.""",
        llm=get_llm(),
        verbose=False,
        tools=ALL_TOOLS,
    )


def create_librarian_agent() -> Agent:
    """Create a Librarian agent - research specialist.

    Based on docs/old/agents/LIBRARIAN.md

    Returns:
        Librarian Agent for documentation research.
    """
    return Agent(
        role="Research Specialist",
        goal="Find and synthesize external documentation, code patterns, and best practices",
        backstory="""You are a research specialist focused on external documentation, code examples, and open source patterns.

Your core capabilities:
1. Documentation Research - Find and explain official documentation for libraries/frameworks
2. Code Pattern Discovery - Search open source repos for production-quality patterns
3. Multi-Repository Analysis - Compare approaches across different projects
4. Best Practices Synthesis - Combine findings into actionable guidance

You always verify information against official sources, provide code examples, and cite specific repositories.
You distinguish between "official recommendation" and "common practice".""",
        llm=get_llm(),
        verbose=False,
        tools=[
            WebSearchTool(),
            WebFetchTool(),
            FileReadToolCrewAI(),
            GrepToolCrewAI(),
            DirectoryListToolCrewAI(),
        ],
    )


def create_heartbeat_agent() -> Agent:
    """Create a Heartbeat agent for periodic tasks.

    Based on docs/old/agents/HEARTBEAT.md

    Returns:
        Heartbeat Agent for recurring tasks.
    """
    return Agent(
        role="Periodic Task Runner",
        goal="Execute recurring tasks, monitoring, and scheduled checks",
        backstory="""You are a periodic task runner that checks and executes recurring tasks.

You check HEARTBEAT.md every 30 minutes for:
- Monitoring tasks (health checks, disk usage, service status)
- Daily reminders
- Scheduled maintenance

You:
- Execute tasks efficiently
- Report results clearly
- Move completed tasks to "Completed" section
- Keep the file small for token efficiency""",
        llm=get_llm(),
        verbose=False,
        tools=[
            FileReadToolCrewAI(),
            FileWriteToolCrewAI(),
            GrepToolCrewAI(),
            DirectoryListToolCrewAI(),
        ],
    )


# Registry of sample agents
SAMPLE_AGENTS = {
    "researcher": create_researcher_agent,
    "simple": create_simple_agent,
    "writer": create_writer_agent,
    "analyzer": create_analyzer_agent,
    "full": create_full_agent,
    "sre": create_sre_agent,
    "librarian": create_librarian_agent,
    "heartbeat": create_heartbeat_agent,
    "router": create_router_agent,  # Auto-delegating agent
}


def get_sample_agent(name: str) -> Agent:
    """Get a sample agent by name.

    Args:
        name: Agent name.

    Returns:
        Agent instance.
    """
    if name not in SAMPLE_AGENTS:
        raise ValueError(f"Unknown sample agent: {name}. Available: {list(SAMPLE_AGENTS.keys())}")

    return SAMPLE_AGENTS[name]()
