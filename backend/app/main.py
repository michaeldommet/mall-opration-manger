"""
Mall Operations Brain — FastAPI Server with Google ADK Runner

This server wraps the Google ADK agent with a FastAPI SSE streaming layer,
maintaining full compatibility with the existing Next.js glassmorphic dashboard.
"""

import os
import json
import asyncio
import logging
import time
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

# ─── OpenTelemetry Instrumentation ───────────────────────────────────────────
from backend.app.telemetry import init_telemetry, instrument_app, tracer
init_telemetry()

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

# Auto-instrument FastAPI with OTel (HTTP-level request/response tracing)
instrument_app(app)

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


# Lazy-loaded embedding model to keep startup fast
_transformer_model = None

@app.get("/api/search")
def hybrid_search(q: str = "", floor: str = None):
    """
    Performs multi-index hybrid search:
    1. Lexical search on 'mall-directory' index matching name, category, description, keywords.
    2. Dense vector semantic search on 'promotions-history' index using query embeddings.
    3. Merges matching stores, boosts stores with matching deals, and returns unified results.
    """
    from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs
    with _tracer.start_as_current_span("search.hybrid", attributes={"search.query": q or "", "search.floor_filter": floor or "all"}):
        if _obs:
            _obs.search_queries.add(1, {"floor": floor or "all"})

    from backend.app.adk_agent.tools import _get_es_client
    es = _get_es_client()
    
    q_clean = q.strip()
    
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

    def normalize_name(name: str):
        return "".join(c.lower() for c in name if c.isalnum())

    def local_fallback():
        results = []
        for s in mock_stores:
            # Filter by floor if requested
            if floor and floor != "all":
                target_floor = f"Floor {floor}"
                if floor == "-1" and "parking" in s["floor"].lower():
                    pass
                elif s["floor"] != target_floor:
                    continue
            
            # Filter by keyword if present
            if q_clean:
                q_lower = q_clean.lower()
                if (q_lower in s["name"].lower() or 
                    q_lower in s["category"].lower() or 
                    q_lower in s["desc"].lower() or 
                    q_lower in s["zone"].lower()):
                    results.append(s)
            else:
                results.append(s)
        return {"stores": results}

    if not es:
        return local_fallback()

    try:
        # 1. Fetch all store records from mall-directory for base metadata and local normalization
        query_all = {
            "query": {"match_all": {}},
            "size": 100
        }
        res_all = es.search(index="mall-directory", body=query_all)
        hits_all = res_all.get("hits", {}).get("hits", [])
        
        all_stores_list = []
        for hit in hits_all:
            source = hit["_source"]
            all_stores_list.append({
                "name": source.get("store_name", "Unknown Store"),
                "floor": f"Floor {source.get('floor', 1)}",
                "zone": source.get("zone", "east-wing").upper(),
                "category": source.get("category", "General"),
                "desc": source.get("description", source.get("keywords", "Premium store")),
                "location": source.get("location", {})
            })
            
        if not all_stores_list:
            all_stores_list = mock_stores

        # Build index mapping based on normalized names
        store_map = {normalize_name(s["name"]): s for s in all_stores_list}

        # If search query is empty, return all stores filtered by floor
        if not q_clean:
            results = []
            for s in all_stores_list:
                if floor and floor != "all":
                    target_floor = f"Floor {floor}"
                    if floor == "-1" and "parking" in s["floor"].lower():
                        pass
                    elif s["floor"] != target_floor:
                        continue
                results.append(s)
            return {"stores": results}

        # 2. Get embeddings and run semantic promotions query
        global _transformer_model
        if _transformer_model is None:
            logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 model for hybrid shopper search...")
            from sentence_transformers import SentenceTransformer
            _transformer_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            
        query_vector = _transformer_model.encode(q_clean).tolist()

        # KNN search on promotions-history
        semantic_body = {
            "knn": {
                "field": "copy_vector",
                "query_vector": query_vector,
                "k": 10,
                "num_candidates": 50
            },
            "size": 10
        }
        res_sem = es.search(index="promotions-history", body=semantic_body)
        sem_hits = res_sem.get("hits", {}).get("hits", [])

        # Map semantic deals to store normalized names
        promoted_deals = {}
        for hit in sem_hits:
            source = hit["_source"]
            tenants = source.get("participating_tenants", [])
            title = source.get("title", "")
            score = hit["_score"]
            
            if isinstance(tenants, str):
                tenants = [t.strip() for t in tenants.split(",") if t.strip()]
            
            for tenant in tenants:
                tenant_normalized = normalize_name(tenant)
                if tenant_normalized not in promoted_deals or score > promoted_deals[tenant_normalized]["score"]:
                    promoted_deals[tenant_normalized] = {
                        "title": title,
                        "score": score
                    }

        # 3. Run lexical keyword query on mall-directory
        lexical_must = [
            {
                "bool": {
                    "should": [
                        {"match": {"store_name": {"query": q_clean, "boost": 4.0}}},
                        {"match": {"category": {"query": q_clean, "boost": 2.5}}},
                        {"match": {"description": {"query": q_clean, "boost": 1.0}}},
                        {"match": {"keywords": {"query": q_clean, "boost": 2.0}}}
                    ]
                }
            }
        ]
        
        lexical_body = {
            "query": {
                "bool": {
                    "must": lexical_must
                }
            },
            "size": 50
        }
        res_lex = es.search(index="mall-directory", body=lexical_body)
        lex_hits = res_lex.get("hits", {}).get("hits", [])

        # Map lexical search results
        lexical_matches = {}
        for hit in lex_hits:
            name = hit["_source"].get("store_name", "")
            lexical_matches[normalize_name(name)] = hit["_score"]

        # 4. Merge and Score Fusion
        merged_results = []
        for norm_name, store in store_map.items():
            # Apply floor filter
            if floor and floor != "all":
                target_floor = f"Floor {floor}"
                if floor == "-1" and "parking" in store["floor"].lower():
                    pass
                elif store["floor"] != target_floor:
                    continue

            is_match = False
            combined_score = 0.0
            
            # Check lexical match
            if norm_name in lexical_matches:
                is_match = True
                combined_score += lexical_matches[norm_name]
                
            # Check semantic promotion deal match
            deal_title = None
            if norm_name in promoted_deals:
                is_match = True
                deal_title = promoted_deals[norm_name]["title"]
                promo_score = promoted_deals[norm_name]["score"]
                # Scale promo score to align with lexical scores
                combined_score += (promo_score * 15.0)

            if is_match:
                store_res = store.copy()
                store_res["deal"] = deal_title
                store_res["score"] = combined_score
                merged_results.append(store_res)

        # Sort merged results by combined score descending
        sorted_results = sorted(merged_results, key=lambda x: x["score"], reverse=True)
        
        # Strip internal score before returning
        for s in sorted_results:
            s.pop("score", None)

        return {"stores": sorted_results}

    except Exception as e:
        logger.error(f"Error in backend hybrid search endpoint: {str(e)}")
        return local_fallback()




async def _stream_adk_events(user_message: str, role: str = "manager"):
    """
    Run the ADK agent and yield SSE-compatible JSON events matching the
    frontend's expected format:
    
      - {"type": "reasoning", "content": "..."}
      - {"type": "tool_call", "tool": "...", "arguments": {...}}
      - {"type": "tool_result", "tool": "...", "output": "..."}
      - {"type": "final_answer", "content": "..."}
    """
    from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs

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
    session_start = time.monotonic()
    tool_call_count = 0
    reasoning_step_count = 0
    total_text_chars = 0

    # ── OTel: Root span for the entire agent session ─────────────────────
    with _tracer.start_as_current_span(
        "agent.session",
        attributes={
            "agent.role": role,
            "agent.name": agent_name,
            "agent.session_id": session_id,
            "agent.user_message": user_message[:500],
        },
    ) as session_span:
        if _obs:
            _obs.session_count.add(1, {"role": role, "agent_name": agent_name})

        try:
            # Track timing for reasoning vs tool phases
            last_event_time = time.monotonic()
            pending_tool_name = None
            tool_start_time = None

            async for event in active_runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_content,
            ):
                # Each event is an ADK Event object. We need to normalize it to
                # the SSE format that the Next.js frontend expects.
                
                now = time.monotonic()
                author = getattr(event, "author", "")
                
                # Check for function calls (tool invocations)
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Function call — agent is requesting a tool
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            tool_name = fc.name or "unknown_tool"
                            tool_args = dict(fc.args) if fc.args else {}

                            # Record reasoning duration (time since last event)
                            reasoning_ms = (now - last_event_time) * 1000
                            if _obs and reasoning_ms > 10:  # skip trivial gaps
                                _obs.reasoning_duration.record(reasoning_ms, {"role": role, "agent_name": agent_name})

                            # Start tracking tool execution time
                            pending_tool_name = tool_name
                            tool_start_time = now
                            tool_call_count += 1
                            
                            yield json.dumps({
                                "type": "tool_call",
                                "tool": tool_name,
                                "arguments": tool_args,
                            })
                            last_event_time = time.monotonic()
                        
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

                            # ── OTel: Record tool execution duration & status ────
                            tool_status = "success"
                            if output_str.startswith("Error"):
                                tool_status = "error"

                            if _obs:
                                # Tool duration
                                if tool_start_time:
                                    tool_ms = (now - tool_start_time) * 1000
                                    _obs.tool_duration.record(tool_ms, {"tool_name": pending_tool_name or tool_name, "status": tool_status})
                                # Tool call counter
                                _obs.tool_calls.add(1, {"tool_name": tool_name, "status": tool_status})

                            pending_tool_name = None
                            tool_start_time = None
                            
                            yield json.dumps({
                                "type": "tool_result",
                                "tool": tool_name,
                                "output": output_str,
                            })
                            last_event_time = time.monotonic()
                        
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
                                reasoning_step_count += 1
                                total_text_chars += len(text)
                                yield json.dumps({
                                    "type": "reasoning",
                                    "content": text[:200] + ("..." if len(text) > 200 else ""),
                                })
                                last_event_time = time.monotonic()

            # After the stream is complete, emit the final answer
            if final_text:
                total_text_chars += len(final_text)
                yield json.dumps({
                    "type": "final_answer",
                    "content": final_text,
                })

            # ── OTel: Finalize session span with summary attributes ──────
            session_duration_ms = (time.monotonic() - session_start) * 1000
            estimated_tokens = total_text_chars // 4  # rough token estimate
            session_span.set_attribute("agent.tool_call_count", tool_call_count)
            session_span.set_attribute("agent.reasoning_steps", reasoning_step_count)
            session_span.set_attribute("agent.estimated_tokens", estimated_tokens)
            session_span.set_attribute("agent.session_duration_ms", session_duration_ms)

            if _obs:
                _obs.tokens_consumed.add(estimated_tokens, {"role": role, "agent_name": agent_name})

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[ADK ERROR] Agent execution failed: {error_msg}")
            session_span.set_attribute("error", True)
            session_span.set_attribute("error.message", error_msg[:500])
            session_span.record_exception(e)
            
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


@app.get("/api/pulse")
def get_pulse_feed():
    """
    Fetches the latest curated dynamic Happenings & Deals feed from the 'pulse-dashboard-feed' index.
    """
    from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs

    es_url = os.getenv("ELASTICSEARCH_URL", "")
    es_api_key = os.getenv("ELASTICSEARCH_API_KEY", "")
    
    # Static fallback in case Elasticsearch is offline or index hasn't been written to by the workflow yet
    fallback_feed = [
        {
            "id": "happening-1",
            "type": "event",
            "badge": "🎨 Art & Craft",
            "title": "Spring Artisan Market",
            "desc": "Local crafts, handmade jewelry, and organic food stalls in the Central Atrium.",
            "time": "Today, 10:00 AM - 8:00 PM",
            "location": "📍 Central Atrium (Floor 1)",
            "store": "Café Bloom",
            "actionLabel": "🧭 Route to Atrium",
            "prompt": "Plan a walking itinerary starting from Entrance A to Café Bloom to visit the Spring Artisan Market in the Central Atrium"
        },
        {
            "id": "happening-2",
            "type": "promo",
            "badge": "⚡ Flash Promo",
            "title": "Café Bloom: Pastry Happy Hour",
            "desc": "Get an exclusive free organic pastry with any Large Latte purchase.",
            "time": "1:00 PM - 4:00 PM Daily",
            "location": "📍 Food Court (Floor 1)",
            "store": "Café Bloom",
            "actionLabel": "🎟️ Claim BOGO Pastry",
            "prompt": "Activate customer coupon for Store: **Café Bloom** and Discount: **Free Pastry w/ Large Latte**"
        },
        {
            "id": "happening-3",
            "type": "music",
            "badge": "🎷 Live Music",
            "title": "Sunset Jazz Concert",
            "desc": "Enjoy smooth contemporary jazz tunes while dining at the Food Court.",
            "time": "Tonight, 6:00 PM - 9:00 PM",
            "location": "📍 Food Court (Floor 1)",
            "store": "Sushi Express",
            "actionLabel": "🧭 Plan Dinner Route",
            "prompt": "Plan a 90-minute dining stop at Sushi Express including the BOGO Roll deal while enjoying the Sunset Jazz Concert"
        },
        {
            "id": "happening-4",
            "type": "promo",
            "badge": "🎁 Seasonal Sale",
            "title": "SneakerVault Retro Weekend",
            "desc": "Get an exclusive 20% off all vintage and retro sneakers releases.",
            "time": "This Friday - Sunday",
            "location": "📍 East-Wing (Floor 1)",
            "store": "SneakerVault",
            "actionLabel": "👟 View Retro Deals",
            "prompt": "Check SneakerVault deals, activate coupon, and plan a shopping stop"
        }
    ]

    if not es_url or not es_api_key:
        return {"feed": fallback_feed, "source": "fallback"}
        
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(es_url, api_key=es_api_key, request_timeout=10)
        
        if not es.indices.exists(index="pulse-dashboard-feed"):
            return {"feed": fallback_feed, "source": "fallback"}
            
        # Search for the latest curation document
        query = {
            "query": {"match_all": {}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 1
        }
        with _tracer.start_as_current_span("pulse.feed.fetch", attributes={"pulse.index": "pulse-dashboard-feed"}) as pulse_span:
            res = es.search(index="pulse-dashboard-feed", body=query)
            hits = res.get("hits", {}).get("hits", [])
            
            if hits:
                source = hits[0]["_source"]
                curated = source.get("curated_feed", [])
                # If curated is stored as a JSON string, load it
                if isinstance(curated, str):
                    import json
                    try:
                        curated = json.loads(curated)
                    except Exception:
                        pass
                if isinstance(curated, list) and len(curated) > 0:
                    pulse_span.set_attribute("pulse.source", "live_elasticsearch")
                    pulse_span.set_attribute("pulse.card_count", len(curated))
                    if _obs:
                        _obs.pulse_workflow_runs.add(1, {"source": "live_elasticsearch"})
                    return {"feed": curated, "source": "live_elasticsearch"}

            pulse_span.set_attribute("pulse.source", "fallback")
                
    except Exception as e:
        logger.error(f"[API] Error loading curated pulse feed from Elasticsearch: {str(e)}")
        
    return {"feed": fallback_feed, "source": "fallback"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
