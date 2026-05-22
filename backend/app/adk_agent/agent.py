"""
Mall Operations Brain — Google ADK Agent Definition

This module defines the root ADK agent connected to the Elastic MCP Server.
The agent uses Gemini on Vertex AI and automatically discovers Elasticsearch
tools (ES|QL, search, indices) via the MCP protocol.
"""

import os
import logging
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    SseConnectionParams,
    StdioConnectionParams,
    StdioServerParameters,
)

from backend.app.agent.prompts import AGENT_SYSTEM_PROMPT, SHOPPER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _get_model_name() -> str:
    """Determine the Gemini model to use."""
    model = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    # Normalize: if old config says gemini-1.5-flash or gpt-*, upgrade to 2.5-flash
    if "gpt" in model.lower() or model == "gemini-1.5-flash":
        model = "gemini-2.5-flash"
    return model


def _build_elastic_mcp_toolset() -> MCPToolset:
    """
    Build the Elastic MCP toolset.

    Supports two modes:
    1. SSE mode: If ELASTIC_MCP_URL is set, connect to the hosted Elastic Agent Builder
       MCP server via Server-Sent Events (remote/cloud).
    2. Stdio mode (fallback): Spawn the @elastic/mcp-server-elasticsearch npm package
       as a local subprocess.
    """
    elastic_mcp_url = os.getenv("ELASTIC_MCP_URL")

    if elastic_mcp_url:
        # Mode 1: Connect to hosted Elastic Agent Builder MCP server via SSE
        logger.info(f"[MCP] Connecting to Elastic Agent Builder MCP via SSE: {elastic_mcp_url}")
        return MCPToolset(
            connection_params=SseConnectionParams(
                url=elastic_mcp_url,
                headers={
                    "Authorization": f"ApiKey {os.getenv('ELASTICSEARCH_API_KEY', '')}",
                },
            )
        )
    else:
        # Mode 2: Spawn the official Elastic MCP Server as a subprocess
        es_url = os.getenv("ELASTICSEARCH_URL", "")
        es_api_key = os.getenv("ELASTICSEARCH_API_KEY", "")

        if not es_url or not es_api_key:
            raise ValueError(
                "ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY must be set in .env "
                "when ELASTIC_MCP_URL is not provided."
            )

        logger.info("[MCP] Spawning @elastic/mcp-server-elasticsearch via stdio")
        return MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@elastic/mcp-server-elasticsearch"],
                    env={
                        **os.environ,
                        "ES_URL": es_url,
                        "ES_API_KEY": es_api_key,
                        "OTEL_SDK_DISABLED": "true",
                        "OTEL_TRACES_EXPORTER": "none",
                        "OTEL_METRICS_EXPORTER": "none",
                        "OTEL_LOGS_EXPORTER": "none",
                    },
                )
            )
        )


# ─── Shared MCP Toolset ──────────────────────────────────────────────────────
# Create a single shared MCP toolset instance at module load time.
# This prevents spawning multiple local stdio subprocesses or establishing multiple
# parallel SSE connections, avoiding lock contentions or handshake failures.
shared_elastic_mcp = _build_elastic_mcp_toolset()


def create_agent() -> LlmAgent:
    """
    Create and return the Mall Operations Brain ADK agent.

    The agent uses:
    - Gemini 2.5 Flash via Vertex AI as the LLM
    - Elastic MCP Server for Elasticsearch tools (ES|QL, search, index listing)
    - The mall operations system prompt for reasoning guidance
    """
    model_name = _get_model_name()

    logger.info(f"[AGENT] Creating Mall Operations Brain agent with model: {model_name}")

    from backend.app.adk_agent.tools import esql, esql_query, run_esql_query

    agent = LlmAgent(
        name="mall_operations_brain",
        model=model_name,
        instruction=AGENT_SYSTEM_PROMPT,
        tools=[shared_elastic_mcp, esql, esql_query, run_esql_query],
    )

    return agent


def create_customer_agent() -> LlmAgent:
    """
    Create and return the Shopper Personal Co-Pilot ADK agent.
    """
    model_name = _get_model_name()

    logger.info(f"[AGENT] Creating Shopper Co-Pilot agent with model: {model_name}")

    from backend.app.adk_agent.tools import (
        calculate_optimal_path,
        activate_customer_coupon,
        esql,
        esql_query,
        run_esql_query,
    )

    agent = LlmAgent(
        name="shopper_personal_copilot",
        model=model_name,
        instruction=SHOPPER_SYSTEM_PROMPT,
        tools=[
            shared_elastic_mcp,
            calculate_optimal_path,
            activate_customer_coupon,
            esql,
            esql_query,
            run_esql_query,
        ],
    )

    return agent


# Pre-build the agents for import by main.py
root_agent = create_agent()
customer_agent = create_customer_agent()

