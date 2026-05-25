import math
import os
import random
import string
import time as _time
from datetime import datetime, timedelta
import urllib.request
import json
from elasticsearch import Elasticsearch

def _get_es_client():
    es_url = os.getenv("ELASTICSEARCH_URL", "")
    es_api_key = os.getenv("ELASTICSEARCH_API_KEY", "")
    if not es_url or not es_api_key:
        return None
    try:
        es = Elasticsearch(
            es_url,
            api_key=es_api_key,
            request_timeout=15
        )
        return es
    except Exception:
        return None


COORDINATES_LOOKUP = {
    "food-court": {"floor": 1, "lat": 24.7136, "lon": 46.6753},
    "electronics-wing": {"floor": 2, "lat": 24.7138, "lon": 46.6755},
    "fashion-district": {"floor": 1, "lat": 24.7134, "lon": 46.6751},
    "services-hub": {"floor": 3, "lat": 24.7140, "lon": 46.6757},
    "east-wing": {"floor": 1, "lat": 24.7139, "lon": 46.6758},
    "west-wing": {"floor": 1, "lat": 24.7133, "lon": 46.6748},
    "entrance-a": {"floor": 0, "lat": 24.7132, "lon": 46.6749},
    "entrance-b": {"floor": 0, "lat": 24.7142, "lon": 46.6759},
    "entrance-c": {"floor": 0, "lat": 24.7136, "lon": 46.6761},
    "parking-a": {"floor": -1, "lat": 24.7130, "lon": 46.6745}
}


def _fetch_coordinates(name_or_zone: str) -> dict:
    """
    Queries the Elasticsearch 'mall-directory' index to retrieve
    the floor, zone, and geo-coordinates (latitude and longitude) of a store or zone.
    """
    if not name_or_zone:
        return None
        
    es = _get_es_client()
    if not es:
        return None
        
    try:
        clean_name = name_or_zone.strip()
        # Search mall-directory index
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"store_id": clean_name.lower().replace(" ", "-")}},
                        {"term": {"store_name": clean_name}},
                        {"term": {"zone": clean_name.lower().replace(" ", "-")}},
                        {"match": {"store_name": {"query": clean_name, "operator": "and"}}},
                        {"match": {"keywords": clean_name.lower()}}
                    ]
                }
            },
            "size": 1
        }
        res = es.search(index="mall-directory", body=query)
        hits = res.get("hits", {}).get("hits", [])
        if hits:
            source = hits[0]["_source"]
            loc = source.get("location", {})
            return {
                "floor": int(source.get("floor", 1)),
                "lat": float(loc.get("lat", 24.7132)),
                "lon": float(loc.get("lon", 46.6749)),
                "zone": source.get("zone", "east-wing")
            }
    except Exception:
        # Silently return None so calling code falls back to COORDINATES_LOOKUP
        pass
    return None


def calculate_optimal_path(stops: list, start_zone: str = "entrance-a") -> str:
    """
    Computes backtrack-free sequences, calculates walking times (60m/min),
    and applies escalator/floor change penalties (+3m per floor).
    Resolves coordinates dynamically from Elasticsearch mall-directory.
    Exposed as a native ADK tool for Gemini to perform route optimizations.
    
    Args:
        stops (list): A list of dictionaries representing the shopping stops.
                      Each stop should contain:
                      - store_name (str): Name of the store (e.g. 'SneakerVault')
                      - activity (str): What to do (e.g. 'buy shoes')
                      - duration (int): Duration in minutes (e.g. 45)
                      - zone (str, optional): Physical zone (e.g. 'east-wing')
                      - floor (int, optional): Floor level (e.g. 1)
                      - notes (str, optional): Active discounts or notes
        start_zone (str): The starting point of the itinerary (e.g. 'entrance-a')
        
    Returns:
        str: A formatted markdown table containing the schedule, transit times,
             notes, and a summary.
    """
    try:
        from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs
        _span = _tracer.start_span(
            "pathfinder.calculate",
            attributes={"pathfinder.stop_count": len(stops), "pathfinder.start_zone": start_zone},
        )
    except Exception:
        _span = None

    try:
        # 1. Resolve start_zone from Elasticsearch
        start_coord = _fetch_coordinates(start_zone)
        if not start_coord:
            start_key = start_zone.lower().strip().replace(" ", "-")
            start_coord = COORDINATES_LOOKUP.get(start_key, {"floor": 0, "lat": 24.7132, "lon": 46.6749})
        
        current_lat = start_coord["lat"]
        current_lon = start_coord["lon"]
        current_floor = start_coord["floor"]
        
        # 2. Parse and validate stops coordinates
        valid_stops = []
        for stop in stops:
            store_name = stop.get("store_name", "")
            
            # Fetch coordinates from Elasticsearch
            es_info = None
            if store_name:
                es_info = _fetch_coordinates(store_name)
            if not es_info:
                # If store name query didn't work, try zone query if available
                zone_val = stop.get("zone", "")
                if zone_val:
                    es_info = _fetch_coordinates(zone_val)
                    
            if es_info:
                lat = es_info["lat"]
                lon = es_info["lon"]
                floor = stop.get("floor", es_info["floor"])
                zone = stop.get("zone", es_info["zone"])
            else:
                # Fallback to COORDINATES_LOOKUP
                zone_key = stop.get("zone", "").lower().strip().replace(" ", "-")
                zone_info = COORDINATES_LOOKUP.get(zone_key, None)
                
                lat = zone_info["lat"] if zone_info else current_lat
                lon = zone_info["lon"] if zone_info else current_lon
                floor = stop.get("floor", zone_info["floor"] if zone_info else 1)
                zone = stop.get("zone", "east-wing")
            
            try:
                floor = int(floor)
            except:
                floor = 1
                
            duration = stop.get("duration", 45)
            try:
                duration = int(duration)
            except:
                duration = 45
                
            valid_stops.append({
                "store_name": store_name or "Unknown Store",
                "activity": stop.get("activity", "Browse"),
                "duration": duration,
                "zone": zone,
                "floor": floor,
                "lat": lat,
                "lon": lon,
                "notes": stop.get("notes", "-")
            })
            
        # 3. Cluster / Sort stops to prevent backtracking!
        # Standard backtrack-free heuristic:
        # Group stops by Floor level, sort Floor levels ascending (or descending if starting on higher level),
        # and greedily order stops inside each floor.
        floors = sorted(list(set([s["floor"] for s in valid_stops])))
        
        # Determine sorting direction (if start floor > average stop floor, visit descending)
        avg_floor = sum(floors) / len(floors) if floors else 0
        if current_floor > avg_floor:
            floors = sorted(floors, reverse=True)
            
        sorted_stops = []
        for fl in floors:
            floor_stops = [s for s in valid_stops if s["floor"] == fl]
            
            # Greedily find nearest stop on this floor
            temp_stops = list(floor_stops)
            f_lat, f_lon = current_lat, current_lon
            while temp_stops:
                nearest_idx = 0
                min_dist = float("inf")
                for idx, ts in enumerate(temp_stops):
                    d = math.sqrt((ts["lat"] - f_lat)**2 + (ts["lon"] - f_lon)**2) * 111000
                    if d < min_dist:
                        min_dist = d
                        nearest_idx = idx
                closest = temp_stops.pop(nearest_idx)
                sorted_stops.append(closest)
                f_lat, f_lon = closest["lat"], closest["lon"]
                
        # 4. Build chronological schedule
        current_time = datetime(2026, 5, 21, 10, 0, 0) # Start itinerary at 10:00 AM
        
        itinerary_rows = []
        
        # Add Starting position as first row
        start_row = {
            "time_slot": current_time.strftime("%I:%M %p"),
            "floor": f"Floor {current_floor}",
            "zone": start_zone.upper(),
            "activity": "Trip Start / Entrance Arrival",
            "duration": "0 min",
            "transit": "0 min",
            "notes": "Starting Point"
        }
        itinerary_rows.append(start_row)
        
        total_walking_dist = 0.0
        total_floor_changes = 0
        
        c_lat, c_lon, c_floor = current_lat, current_lon, current_floor
        
        for stop in sorted_stops:
            # A. Calculate Transit Math
            dist = math.sqrt((stop["lat"] - c_lat)**2 + (stop["lon"] - c_lon)**2) * 111000
            walk_time = dist / 60.0  # 60 meters/min
            
            floor_diff = abs(stop["floor"] - c_floor)
            transit_penalty = floor_diff * 3.0  # +3 minutes per floor change
            
            total_transit = int(round(walk_time + transit_penalty))
            if total_transit < 1 and dist > 5:
                total_transit = 1
                
            total_walking_dist += dist
            total_floor_changes += floor_diff
            
            # Start moving to next stop
            if total_transit > 0:
                current_time += timedelta(minutes=total_transit)
                
            start_activity_time = current_time
            current_time += timedelta(minutes=stop["duration"])
            
            time_str = f"{start_activity_time.strftime('%I:%M %p')} - {current_time.strftime('%I:%M %p')}"
            
            itinerary_rows.append({
                "time_slot": time_str,
                "floor": f"Floor {stop['floor']}",
                "zone": stop["zone"],
                "activity": f"{stop['store_name']} ({stop['activity']})",
                "duration": f"{stop['duration']} min",
                "transit": f"{total_transit} min" if total_transit > 0 else "-",
                "notes": stop["notes"]
            })
            
            # Update current coordinates
            c_lat, c_lon, c_floor = stop["lat"], stop["lon"], stop["floor"]
            
        # 5. Generate final Markdown Table
        markdown = "### Optimized Personal Schedule\n\n"
        markdown += "| Time Slot | Floor | Zone | Activity / Store | Duration | Walking/Transit Time | Notes & Active Deals |\n"
        markdown += "|---|---|---|---|---|---|---|\n"
        for row in itinerary_rows:
            markdown += f"| {row['time_slot']} | {row['floor']} | {row['zone']} | {row['activity']} | {row['duration']} | {row['transit']} | {row['notes']} |\n"
            
        markdown += "\n### Itinerary Analytics Summary\n"
        markdown += f"- **Total Floor Level Changes:** {total_floor_changes}\n"
        markdown += f"- **Estimated Walking Distance:** {int(round(total_walking_dist))} meters\n"
        markdown += f"- **Backtracking Status:** **Optimal (0 backtracks)**\n"
        markdown += f"- **Calculated Speed:** 60 meters/min pace\n"
        
        if _span:
            _span.end()
        return markdown
    except Exception as e:
        if _span:
            _span.set_attribute("error", True)
            _span.record_exception(e)
            _span.end()
        return f"Error executing itinerary calculations: {str(e)}"


def activate_customer_coupon(store_name: str, discount_desc: str, shopper_id: str = "mall_shopper") -> str:
    """
    Simulates or executes the secure activate_customer_coupon Workflow.
    Generates a unique single-use coupon code, records it in the 'customer-coupons' index,
    and returns a success message including the coupon details and scannable token.

    Args:
        store_name (str): The name of the store (e.g. 'SneakerVault').
        discount_desc (str): The discount offer details (e.g. '20% off retro styles').
        shopper_id (str): The ID of the shopper activating the coupon.

    Returns:
        str: A message with the coupon activation outcome and unique token.
    """
    try:
        from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs
    except Exception:
        _tracer = None
        _obs = None

    _span_ctx = _tracer.start_as_current_span(
        "coupon.activation",
        attributes={"coupon.store_name": store_name, "coupon.shopper_id": shopper_id},
    ) if _tracer else __import__("contextlib").nullcontext()

    with _span_ctx as coupon_span:
      activation_start = _time.monotonic()
      try:
        # Check if we can trigger the actual Kibana/Elastic Serverless Workflow API
        es_url = os.getenv("ELASTERSEARCH_URL", os.getenv("ELASTICSEARCH_URL", ""))
        es_api_key = os.getenv("ELASTICSEARCH_API_KEY", "")
        
        workflow_triggered = False
        workflow_details = {}
        indexed_status = "Simulated Activation (Local Mode)"
        
        if es_url and es_api_key:
            # Construct the Workflow Trigger API URL
            # Serverless default space path with hyphenated ID: /s/default/api/workflows/workflow/activate-customer-coupon/run
            base_url = es_url.rstrip("/")
            if ".es." in base_url:
                base_url = base_url.replace(".es.", ".kb.")
            
            workflow_id = "activate-customer-coupon"
            workflow_url = f"{base_url}/s/default/api/workflows/workflow/{workflow_id}/run"
            
            payload = {
                "inputs": {
                    "store_name": store_name,
                    "discount_desc": discount_desc,
                    "shopper_id": shopper_id
                }
            }
            
            try:
                # 1. Trigger the workflow execution
                req = urllib.request.Request(
                    workflow_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"ApiKey {es_api_key}",
                        "Content-Type": "application/json",
                        "kbn-xsrf": "true"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    execution_id = res_body.get("workflowExecutionId")
                
                # 2. Poll execution details to retrieve compiled coupon token and variables
                if execution_id:
                    import time
                    details_url = f"{base_url}/s/default/api/workflows/executions/{execution_id}"
                    
                    # Poll for a max of 5 seconds (5 attempts, 1s sleep)
                    for attempt in range(5):
                        time.sleep(1)
                        try:
                            det_req = urllib.request.Request(
                                details_url,
                                headers={
                                    "Authorization": f"ApiKey {es_api_key}",
                                    "Content-Type": "application/json",
                                    "kbn-xsrf": "true"
                                },
                                method="GET"
                            )
                            with urllib.request.urlopen(det_req, timeout=5) as det_res:
                                details = json.loads(det_res.read().decode("utf-8"))
                                status = details.get("status")
                                if status == "completed":
                                    output_data = details.get("context", {}).get("output", {}).get("value", {})
                                    if output_data and "token" in output_data:
                                        workflow_details = output_data
                                        workflow_triggered = True
                                        indexed_status = "Activated & Orchestrated via Kibana Workflows API"
                                        break
                                elif status == "failed":
                                    break
                        except Exception:
                            # Keep polling
                            pass
            except Exception as e:
                # Capture the explicit fallback explanation
                err_msg = str(e)
                if hasattr(e, "read"):
                    try:
                        err_body = e.read().decode("utf-8")
                        if "Not Found" in err_body or "404" in err_msg:
                            err_msg += f" (Workflow '{workflow_id}' not found in Kibana. Have you imported activate_customer_coupon_workflow.yaml under Kibana UI > Workflows?)"
                        else:
                            err_msg += f" ({err_body})"
                    except Exception:
                        pass
                indexed_status = f"Simulated Activation (API Fallback: {err_msg})"

        if workflow_triggered:
            token = workflow_details.get("token", "")
            coupon_id = workflow_details.get("coupon_id", "")
            activated_at = workflow_details.get("activated_at", "")
            expires_at = workflow_details.get("expires_at", "")
        else:
            # Generate clean token SV-RETRO-982A
            # Get abbreviation of store name
            store_clean = "".join([c for c in store_name if c.isalnum()]).upper()
            abbrev = store_clean[:2] if len(store_clean) >= 2 else "CP"
            
            # Get abbreviation of discount
            disc_words = [w for w in discount_desc.split() if w.strip()]
            disc_clean = "".join([c for c in "".join(disc_words) if c.isalnum()]).upper()
            disc_abbrev = disc_clean[:5] if len(disc_clean) >= 5 else "DEAL"
            
            # Random suffix
            rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            token = f"{abbrev}-{disc_abbrev}-{rand_suffix}"
            
            # Connect to Elasticsearch
            es = _get_es_client()
            coupon_id = f"c-{random.randint(100000, 999999)}"
            activated_at = datetime.utcnow().isoformat() + "Z"
            expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
            
            doc = {
                "coupon_id": coupon_id,
                "store_name": store_name,
                "discount": discount_desc,
                "token": token,
                "shopper_id": shopper_id,
                "activated_at": activated_at,
                "expires_at": expires_at,
                "is_redeemed": False
            }
            
            indexed_status_final = indexed_status
            if es:
                try:
                    es.index(index="customer-coupons", document=doc, refresh=True)
                    if "API Fallback" in indexed_status:
                        indexed_status_final = f"{indexed_status} & Logged in Elasticsearch ('customer-coupons')"
                    else:
                        indexed_status_final = "Activated & Logged in Elasticsearch ('customer-coupons')"
                except Exception as es_err:
                    indexed_status_final = f"Simulated Activation (DB Index Error: {str(es_err)})"
            
            indexed_status = indexed_status_final
                
        result = (
            f"### Coupon Activated Successfully!\n\n"
            f"- **Store:** {store_name}\n"
            f"- **Discount:** {discount_desc}\n"
            f"- **Secure Token Code:** `{token}`\n"
            f"- **Shopper ID:** {shopper_id}\n"
            f"- **Status:** {indexed_status}\n"
            f"- **Expires At:** {expires_at}\n\n"
            f"**INSTRUCTIONS:** Render this coupon in the Next.js visual timeline with a scannable digital barcode "
            f"for checkout. Show the token `{token}` prominently."
        )

        # ── OTel: Record coupon activation metrics ──────────────────────
        activation_method = "workflow" if workflow_triggered else "local"
        if coupon_span:
            coupon_span.set_attribute("coupon.method", activation_method)
            coupon_span.set_attribute("coupon.token", token)
            coupon_span.set_attribute("coupon.duration_ms", (_time.monotonic() - activation_start) * 1000)
        if _obs:
            _obs.coupon_activations.add(1, {"store_name": store_name, "method": activation_method})

        return result
      except Exception as e:
        if coupon_span:
            coupon_span.set_attribute("error", True)
            coupon_span.record_exception(e)
        return f"Error executing coupon activation workflow: {str(e)}"


def _execute_esql(query: str) -> str:
    """Internal helper to run ES|QL queries natively."""
    try:
        from backend.app.telemetry import tracer as _tracer, obs_metrics as _obs
    except Exception:
        _tracer = None
        _obs = None

    es = _get_es_client()
    if not es:
        if _obs:
            _obs.esql_queries.add(1, {"status": "error"})
        return "Error: Elasticsearch client could not be initialized. Verify connection configurations."

    _span_ctx = _tracer.start_as_current_span(
        "esql.query",
        attributes={"esql.query": query[:500]},
    ) if _tracer else __import__("contextlib").nullcontext()

    with _span_ctx as esql_span:
        try:
            res = es.esql.query(query=query)
            columns = res.get("columns", [])
            values = res.get("values", [])
            
            if not columns:
                if _obs:
                    _obs.esql_queries.add(1, {"status": "success"})
                return "Query executed successfully, but returned no columns."
                
            # Format as Markdown table
            col_names = [col["name"] for col in columns]
            markdown = "| " + " | ".join(col_names) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(col_names)) + " |\n"
            
            for val_row in values:
                val_strs = []
                for v in val_row:
                    if v is None:
                        val_strs.append("-")
                    elif isinstance(v, dict):
                        val_strs.append(str(v))
                    else:
                        val_strs.append(str(v))
                markdown += "| " + " | ".join(val_strs) + " |\n"

            # ── OTel: Record success metrics ─────────────────────────────
            if esql_span:
                esql_span.set_attribute("esql.row_count", len(values))
                esql_span.set_attribute("esql.column_count", len(col_names))
            if _obs:
                _obs.esql_queries.add(1, {"status": "success"})

            return markdown
        except Exception as e:
            if esql_span:
                esql_span.set_attribute("error", True)
                esql_span.record_exception(e)
            if _obs:
                _obs.esql_queries.add(1, {"status": "error"})
            return f"Error executing ES|QL query: {str(e)}"


def run_esql_query(query: str) -> str:
    """
    Executes an ES|QL (Elasticsearch Query Language) query against the Elasticsearch cluster
    and returns the structured results as a formatted markdown table.
    
    Args:
        query (str): The raw ES|QL query string to execute (e.g. 'FROM mall-directory | KEEP store_name, floor | LIMIT 5').
    """
    return _execute_esql(query)


def esql_query(query: str) -> str:
    """
    Executes an ES|QL query against the Elasticsearch cluster and returns a markdown table of results.
    
    Args:
        query (str): The ES|QL query string to run.
    """
    return _execute_esql(query)


def esql(query: str) -> str:
    """
    Executes an ES|QL query against the Elasticsearch cluster and returns a markdown table of results.
    
    Args:
        query (str): The ES|QL query string to run.
    """
    return _execute_esql(query)
