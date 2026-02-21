"""MCP Loader for connecting to external MCP servers from workspace configuration."""

import os
import glob
import json
import logging
import subprocess
from typing import List, Dict, Any
from crewclaw.config import get_config

logger = logging.getLogger(__name__)

class MCPLoader:
    """Loads and manages MCP server connections defined in a directory."""
    
    def __init__(self, mcp_dir: str | None = None):
        config = get_config()
        self.mcp_dir = mcp_dir or config.get("project.mcp_dir", "./workspace/mcp")
        self.servers: Dict[str, Any] = {}

    def load_all(self) -> Dict[str, Any]:
        """Scan directory and load all MCP server definitions (JSON/YAML)."""
        if not os.path.exists(self.mcp_dir):
            os.makedirs(self.mcp_dir, exist_ok=True)
            logger.info(f"Created MCP directory: {self.mcp_dir}")
            return {}

        for json_file in glob.glob(os.path.join(self.mcp_dir, "*.json")):
            self._load_server(json_file)
            
        return self.servers

    def _load_server(self, file_path: str):
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            server_name = os.path.splitext(os.path.basename(file_path))[0]
            if "command" in config:
                self.servers[server_name] = config
                logger.info(f"Loaded MCP server definition: {server_name}")
        except Exception as e:
            logger.error(f"Error loading MCP server from {file_path}: {e}")

    def get_tools_from_servers(self) -> List[Any]:
        """
        Connect to servers and fetch tools.
        Note: This is a placeholder for actual MCP client implementation.
        In a real scenario, this would use an MCP SDK to connect and discover tools.
        """
        all_tools = []
        # Implementation would go here
        return all_tools
