"""
Mall Operations Brain — FastAPI Server with Google ADK Runner

This server wraps the Google ADK agent with a FastAPI SSE streaming layer,
maintaining full compatibility with the existing Next.js glassmorphic dashboard.
"""

import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import uvicorn
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# ─── Vertex AI Configuration ────────────────────────────────────────────────
# The ADK uses google-genai under the hood. For Vertex AI API keys (starting
# with "AQ."), we need to configure the client to route through Vertex AI.
google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
if google_key.startswith("AQ."):
    # Agent Platform Model AP key — route through Vertex AI
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID", "942081424214"))
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    os.environ.setdefault("GOOGLE_API_KEY", google_key)
    logger.info(f"[VERTEX AI] Auto-configured for Vertex AI (project: {os.environ['GOOGLE_CLOUD_PROJECT']})")

# ─── ADK Components ─────────────────────────────────────────────────────────
# Import the agent after environment is configured
from backend.app.adk_agent.agent import root_agent, customer_agent

session_service = InMemorySessionService()

# Manager Runner
runner = Runner(
    agent=root_agent,
    app_name="mall_operations_brain",
    session_service=session_service,
)

# Customer Runner
customer_runner = Runner(
    agent=customer_agent,
    app_name="shopper_personal_copilot",
    session_service=session_service,
)

# ─── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Mall Operations Brain API",
    description="Backend API serving Google ADK agent with Elastic MCP over SSE streams.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    role: str = "manager"  # "manager" or "customer"


@app.get("/api/health")
def health_check():
    """Simple connection health-check endpoint."""
    return {
        "status": "ok",
        "service": "Mall Operations Brain",
        "engine": "Google ADK + Elastic MCP",
        "model": root_agent.model,
    }


@app.get("/api/stores")
def get_stores():
    """Fetches all stores from the Elasticsearch mall-directory index with local mock fallback."""
    from backend.app.adk_agent.tools import _get_es_client
    es = _get_es_client()
    
    mock_stores = [
        {"name": "SneakerVault", "floor": "Floor 1", "zone": "EAST-WING", "category": "Apparel", "desc": "Premium sneaker boutique featuring retro releases."},
        {"name": "Sushi Express", "floor": "Floor 1", "zone": "FOOD-COURT", "category": "Dining", "desc": "Fresh sushi rolls, sashimi, and classic Japanese dishes."},
        {"name": "Café Bloom", "floor": "Floor 1", "zone": "FOOD-COURT", "category": "Dining", "desc": "Specialty coffee, organic teas, and freshly baked pastries."},
        {"name": "TechZone", "floor": "Floor 2", "zone": "ELECTRONICS-WING", "category": "Electronics", "desc": "Latest smartphones, laptops, smart home tech, and accessories."},
        {"name": "ByteShop", "floor": "Floor 2", "zone": "ELECTRONICS-WING", "category": "Electronics", "desc": "Expert computer components and high-performance gaming rigs."},
        {"name": "StyleCraft", "floor": "Floor 1", "zone": "FASHION-DISTRICT", "category": "Apparel", "desc": "Custom tailored menswear and premium accessories."},
        {"name": "FashionHub", "floor": "Floor 1", "zone": "FASHION-DISTRICT", "category": "Apparel", "desc": "Trendy streetwear and modern wardrobe essentials."},
        {"name": "Urban Threads", "floor": "Floor 1", "zone": "EAST-WING", "category": "Apparel", "desc": "Eco-friendly fabrics and contemporary casualwear."},
        {"name": "Pizza Palace", "floor": "Floor 1", "zone": "FOOD-COURT", "category": "Dining", "desc": "Gourmet wood-fired pizzas and fresh Italian pasta."},
        {"name": "Burger Barn", "floor": "Floor 1", "zone": "FOOD-COURT", "category": "Dining", "desc": "Flame-grilled artisan burgers and hand-cut fries."},
        {"name": "HomeStyle", "floor": "Floor 1", "zone": "WEST-WING", "category": "Apparel", "desc": "Modern home decor, textile accents, and furniture."},
        {"name": "BookNook", "floor": "Floor 1", "zone": "WEST-WING", "category": "Apparel", "desc": "Curated novels, local literature, and cozy reading corners."},
        {"name": "GlamCuts Salon", "floor": "Floor 3", "zone": "SERVICES-HUB", "category": "Services", "desc": "Full-service luxury hair styling and aesthetic treatments."},
        {"name": "QuickFix Phones", "floor": "Floor 3", "zone": "SERVICES-HUB", "category": "Services", "desc": "Immediate screen repairs and battery diagnostics."},
        {"name": "Entrance A", "floor": "Floor 0", "zone": "ENTRANCE-A", "category": "Transit", "desc": "East entrance portal situated on the ground level."},
        {"name": "Entrance B", "floor": "Floor 0", "zone": "ENTRANCE-B", "category": "Transit", "desc": "West entrance portal situated on the ground level."},
        {"name": "Entrance C", "floor": "Floor 0", "zone": "ENTRANCE-C", "category": "Transit", "desc": "North entrance portal situated on the ground level."},
        {"name": "Parking A", "floor": "Floor -1", "zone": "PARKING-A", "category": "Transit", "desc": "Underground parking hub with EV charging stalls."}
    ]
    
    if not es:
        return {"stores": mock_stores}
        
    try:
        query = {
            "query": {"match_all": {}},
            "size": 100
        }
        res = es.search(index="mall-directory", body=query)
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            return {"stores": mock_stores}
            
        stores = []
        for hit in hits:
            source = hit["_source"]
            stores.append({
                "name": source.get("store_name", "Unknown Store"),
                "floor": f"Floor {source.get('floor', 1)}",
                "zone": source.get("zone", "east-wing").upper(),
                "category": source.get("category", "General"),
                "desc": source.get("description", source.get("keywords", "Premium store")),
                "location": source.get("location", {})
            })
        return {"stores": stores}
    except Exception as e:
        logger.error(f"Error querying stores from Elasticsearch: {str(e)}")
        return {"stores": mock_stores}


async def _stream_adk_events(user_message: str, role: str = "manager"):
    """
    Run the ADK agent and yield SSE-compatible JSON events matching the
    frontend's expected format:
    
      - {"type": "reasoning", "content": "..."}
      - {"type": "tool_call", "tool": "...", "arguments": {...}}
      - {"type": "tool_result", "tool": "...", "output": "..."}
      - {"type": "final_answer", "content": "..."}
    """
    # Route execution based on role
    if role == "customer":
        app_name = "shopper_personal_copilot"
        user_id = "mall_shopper"
        active_runner = customer_runner
        agent_name = "shopper_personal_copilot"
    else:
        app_name = "mall_operations_brain"
        user_id = "mall_manager"
        active_runner = runner
        agent_name = "mall_operations_brain"

    # Create a new session for each request (stateless for now)
    session_id = f"session-{id(user_message)}-{asyncio.get_event_loop().time()}"
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    # Build the user message content
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_text = ""

    try:
        async for event in active_runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=user_content,
        ):
            # Each event is an ADK Event object. We need to normalize it to
            # the SSE format that the Next.js frontend expects.
            
            author = getattr(event, "author", "")
            
            # Check for function calls (tool invocations)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Function call — agent is requesting a tool
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_name = fc.name or "unknown_tool"
                        tool_args = dict(fc.args) if fc.args else {}
                        
                        yield json.dumps({
                            "type": "tool_call",
                            "tool": tool_name,
                            "arguments": tool_args,
                        })
                    
                    # Function response — result from tool execution
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        tool_name = fr.name or "unknown_tool"
                        # The response can be a dict or a string
                        output = fr.response
                        if isinstance(output, dict):
                            output_str = json.dumps(output, indent=2)
                        else:
                            output_str = str(output)
                        
                        yield json.dumps({
                            "type": "tool_result",
                            "tool": tool_name,
                            "output": output_str,
                        })
                    
                    # Text content — either reasoning or final answer
                    elif hasattr(part, "text") and part.text:
                        text = part.text.strip()
                        if not text:
                            continue
                        
                        if author == agent_name:
                            # This is the agent's text output
                            # If this is a reasoning step (internal monologue before final),
                            # we emit it as reasoning. The last text becomes the final answer.
                            final_text = text
                            yield json.dumps({
                                "type": "reasoning",
                                "content": text[:200] + ("..." if len(text) > 200 else ""),
                            })

        # After the stream is complete, emit the final answer
        if final_text:
            yield json.dumps({
                "type": "final_answer",
                "content": final_text,
            })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[ADK ERROR] Agent execution failed: {error_msg}")
        
        # Check if it's an API key / permission issue
        if any(term in error_msg.lower() for term in ["permission", "403", "blocked", "api_key"]):
            yield json.dumps({
                "type": "reasoning",
                "content": f"⚠️ API credential issue detected: {error_msg[:150]}. Please verify your GOOGLE_API_KEY and Vertex AI configuration.",
            })
        
        yield json.dumps({
            "type": "error",
            "content": f"Agent execution error: {error_msg}",
        })


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Primary endpoint that accepts user operations prompts and yields
    real-time reasoning milestones and final reports using Server-Sent Events (SSE).
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message prompt cannot be empty.")

    print(f"[API] Received query request: {request.message} (role: {request.role})")

    async def event_generator():
        async for event_json in _stream_adk_events(request.message, request.role):
            yield {"data": event_json}

    return EventSourceResponse(event_generator())


@app.post("/api/scan")
async def scan_endpoint():
    """
    Triggers a proactive audit scanning for foot-traffic anomalies and triages findings.
    """
    print("[API] Proactive Weekly Operational Scan triggered manually.")

    async def event_generator():
        prompt = "Run the weekly scheduled operational foot traffic anomaly check."
        async for event_json in _stream_adk_events(prompt):
            yield {"data": event_json}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
