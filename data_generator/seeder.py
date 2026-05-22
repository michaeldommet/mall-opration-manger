import os
import sys
import random
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch, helpers
from faker import Faker
import numpy as np
from sentence_transformers import SentenceTransformer

# Add parent directory to path to enable package import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_generator.config import (
    ELASTICSEARCH_URL,
    ELASTICSEARCH_API_KEY,
    ZONES,
    TENANTS,
    INDEX_FOOT_TRAFFIC,
    INDEX_TENANT_SALES,
    INDEX_MAINTENANCE_TICKETS,
    INDEX_EVENTS_CALENDAR,
    INDEX_PROMOTIONS_HISTORY,
    INDEX_MALL_DIRECTORY,
    INDEX_CUSTOMER_COUPONS,
    ALL_INDICES
)

fake = Faker()

# Initialize Embedding Model (384 dimensions)
print("Loading sentence-transformers/all-MiniLM-L6-v2 embedding model...")
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def get_es_client():
    if not ELASTICSEARCH_URL or not ELASTICSEARCH_API_KEY:
        print("\nERROR: ELASTICSEARCH_URL or ELASTICSEARCH_API_KEY is not defined in your environment/env file.")
        print("Please configure them in 'backend/.env' or at root level.")
        sys.exit(1)
    
    print(f"Connecting to Elastic Cloud Serverless: {ELASTICSEARCH_URL}")
    es = Elasticsearch(
        ELASTICSEARCH_URL,
        api_key=ELASTICSEARCH_API_KEY,
        request_timeout=60
    )
    if es.ping():
        print("Successfully authenticated and connected to Elastic Cloud Serverless!")
        return es
    else:
        print("Error: Could not ping Elastic Cloud Serverless cluster.")
        sys.exit(1)

def create_index_mappings(es):
    # Mapping Definitions
    mappings = {
        INDEX_FOOT_TRAFFIC: {
            "mappings": {
                "properties": {
                    "timestamp": { "type": "date" },
                    "zone": { "type": "keyword" },
                    "entrance": { "type": "keyword" },
                    "visitor_count": { "type": "integer" },
                    "location": { "type": "geo_point" },
                    "floor": { "type": "integer" }
                }
            }
        },
        INDEX_TENANT_SALES: {
            "mappings": {
                "properties": {
                    "date": { "type": "date" },
                    "store_id": { "type": "keyword" },
                    "store_name": { "type": "keyword" },
                    "category": { "type": "keyword" },
                    "revenue": { "type": "double" },
                    "floor": { "type": "integer" },
                    "zone": { "type": "keyword" }
                }
            }
        },
        INDEX_MAINTENANCE_TICKETS: {
            "mappings": {
                "properties": {
                    "ticket_id": { "type": "keyword" },
                    "created_at": { "type": "date" },
                    "closed_at": { "type": "date" },
                    "description": { "type": "text" },
                    "description_vector": { 
                        "type": "dense_vector", 
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "zone": { "type": "keyword" },
                    "severity": { "type": "keyword" },
                    "status": { "type": "keyword" },
                    "assignee": { "type": "keyword" }
                }
            }
        },
        INDEX_EVENTS_CALENDAR: {
            "mappings": {
                "properties": {
                    "event_id": { "type": "keyword" },
                    "title": { "type": "text" },
                    "start_time": { "type": "date" },
                    "end_time": { "type": "date" },
                    "zone": { "type": "keyword" },
                    "expected_attendance": { "type": "integer" },
                    "impact_level": { "type": "keyword" }
                }
            }
        },
        INDEX_PROMOTIONS_HISTORY: {
            "mappings": {
                "properties": {
                    "campaign_id": { "type": "keyword" },
                    "title": { "type": "text" },
                    "copy_text": { "type": "text" },
                    "copy_vector": { 
                        "type": "dense_vector", 
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "participating_tenants": { "type": "keyword" },
                    "zone": { "type": "keyword" },
                    "sales_lift_percent": { "type": "double" },
                    "start_date": { "type": "date" },
                    "end_date": { "type": "date" }
                }
            }
        },
        INDEX_MALL_DIRECTORY: {
            "mappings": {
                "properties": {
                    "store_id": { "type": "keyword" },
                    "store_name": { "type": "keyword" },
                    "category": { "type": "keyword" },
                    "floor": { "type": "integer" },
                    "zone": { "type": "keyword" },
                    "location": { "type": "geo_point" },
                    "description": { "type": "text" },
                    "keywords": { "type": "keyword" }
                }
            }
        },
        INDEX_CUSTOMER_COUPONS: {
            "mappings": {
                "properties": {
                    "coupon_id": { "type": "keyword" },
                    "store_name": { "type": "keyword" },
                    "discount": { "type": "keyword" },
                    "token": { "type": "keyword" },
                    "shopper_id": { "type": "keyword" },
                    "activated_at": { "type": "date" },
                    "expires_at": { "type": "date" },
                    "is_redeemed": { "type": "boolean" }
                }
            }
        }
    }

    for index_name, mapping_body in mappings.items():
        if es.indices.exists(index=index_name):
            print(f"Index {index_name} already exists. Recreating index to update mappings...")
            es.indices.delete(index=index_name)
        es.indices.create(index=index_name, body=mapping_body)
        print(f"Created index {index_name} with explicit mapping.")

# --- Generators ---

def generate_foot_traffic_docs(days=90):
    print("Generating foot-traffic documents...")
    docs = []
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    current_time = start_date
    while current_time < end_date:
        is_weekend = current_time.weekday() >= 5 # Friday/Saturday/Sunday
        hour = current_time.hour
        
        # Hourly profile factor (mall open 9 AM to 10 PM)
        if hour < 9 or hour > 22:
            base_factor = random.uniform(0.01, 0.05)
        elif 12 <= hour <= 14: # Lunch peak
            base_factor = random.uniform(0.7, 1.0)
        elif 18 <= hour <= 20: # Evening peak
            base_factor = random.uniform(0.8, 1.1)
        else:
            base_factor = random.uniform(0.3, 0.6)
            
        weekend_mult = 1.5 if is_weekend else 1.0
        
        for zone_name, zone_info in ZONES.items():
            # Skip parking for entrance calculation
            if zone_name == "parking-a":
                entrance = "Parking-Deck"
                base_val = 150
            elif "entrance" in zone_name:
                entrance = zone_name.replace("entrance-", "Entrance-").upper()
                base_val = 200
            else:
                entrance = "N/A"
                base_val = 100
                
            count = int(base_val * base_factor * weekend_mult * random.uniform(0.8, 1.2))
            
            # Intentional traffic anomaly for Flow 4: Entrance A traffic falls by 40% during the last 7 days
            if zone_name == "entrance-a" and (end_date - current_time).days <= 7:
                count = int(count * 0.5)
                
            doc = {
                "_index": INDEX_FOOT_TRAFFIC,
                "_source": {
                    "timestamp": current_time.isoformat() + "Z",
                    "zone": zone_name,
                    "entrance": entrance,
                    "visitor_count": count,
                    "location": {"lat": zone_info["lat"], "lon": zone_info["lon"]},
                    "floor": zone_info["floor"]
                }
            }
            docs.append(doc)
            
        current_time += timedelta(hours=1)
    return docs

def generate_tenant_sales_docs(days=90):
    print("Generating tenant-sales documents...")
    docs = []
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    current_time = start_date
    
    # Store base daily sales ranges
    base_sales = {
        "electronics": (3000, 8000),
        "apparel": (1500, 4500),
        "food": (800, 2500),
        "services": (600, 1800),
        "home": (1200, 3500),
        "lifestyle": (800, 2000)
    }
    
    while current_time < end_date:
        is_weekend = current_time.weekday() >= 5
        weekend_mult = 1.4 if is_weekend else 1.0
        
        # Date breakdown
        is_current_month = current_time.month == end_date.month and current_time.year == end_date.year
        
        for tenant in TENANTS:
            category = tenant["category"]
            min_s, max_s = base_sales.get(category, (1000, 3000))
            daily_revenue = random.uniform(min_s, max_s) * weekend_mult * random.uniform(0.9, 1.1)
            
            # Flow 1/3 Intentional performance anomaly:
            # - FashionHub (apparel) and Burger Barn (food) underperform heavily in the current month (May 2026) vs last month.
            # - FashionHub underperforms because of a lack of fashion-district promotions.
            # - Burger Barn underperforms because of a water leak ticket starting May 10th.
            if is_current_month:
                if tenant["store_id"] == "fashionhub":
                    daily_revenue = daily_revenue * 0.72 # 28% drop
                elif tenant["store_id"] == "burgerbarn":
                    # Dropped specifically after May 10th due to maintenance
                    if current_time.day >= 10:
                        daily_revenue = daily_revenue * 0.60 # 40% drop
                elif tenant["store_id"] == "sneakervault":
                    daily_revenue = daily_revenue * 0.68 # 32% drop
            
            doc = {
                "_index": INDEX_TENANT_SALES,
                "_source": {
                    "date": current_time.strftime("%Y-%m-%dT00:00:00Z"),
                    "store_id": tenant["store_id"],
                    "store_name": tenant["store_name"],
                    "category": tenant["category"],
                    "revenue": round(daily_revenue, 2),
                    "floor": tenant["floor"],
                    "zone": tenant["zone"]
                }
            }
            docs.append(doc)
            
        current_time += timedelta(days=1)
    return docs

def generate_maintenance_tickets_docs():
    print("Generating maintenance-tickets documents...")
    docs = []
    
    # Pre-defined ticket subjects to create rich text descriptions (great for semantic matching)
    facilities_issues = [
        {"desc": "HVAC system malfunction in Electronics Wing causing overheating and fan rattle.", "zone": "electronics-wing", "severity": "high"},
        {"desc": "Broken floor tiles near GlamCuts Salon. Tripping hazard, needs immediate patching.", "zone": "services-hub", "severity": "medium"},
        {"desc": "Escalator leading from floor 1 to floor 2 in East Wing stopped moving. Main belt jammed.", "zone": "east-wing", "severity": "high"},
        {"desc": "Flickering overhead light ballast in Parking Deck A, bay C3. Driver visibility reduced.", "zone": "parking-a", "severity": "low"},
        {"desc": "Unresponsive automatic sliding glass entrance door A. Sensor logic faulty.", "zone": "entrance-a", "severity": "medium"},
        {"desc": "Clogged storm drain at Entrance B courtyard causing 3 inches of standing water.", "zone": "entrance-b", "severity": "high"},
        {"desc": "WiFi access point outage in Fashion District. Customers unable to connect to mall portal.", "zone": "fashion-district", "severity": "low"},
        {"desc": "Trash compactor breakdown in basement loading dock. Trash backup, odor issue.", "zone": "west-wing", "severity": "medium"},
        {"desc": "Elevator #3 doors refusing to open on Floor 3. Emergency maintenance team dispatched.", "zone": "services-hub", "severity": "critical"}
    ]
    
    # Specific correlation ticket: Critical water leak/plumbing issue in the food-court zone
    # This correlates directly with the drop in Burger Barn sales starting May 10th
    correlation_tickets = [
        {
            "desc": "Severe water pipe leak from the third floor restroom ceiling dripping directly into the food court seating area near Burger Barn. Flooded floor tiles, safety cones deployed, seating blocked.",
            "zone": "food-court",
            "severity": "critical",
            "status": "open",
            "created_offset": 9 # 9 days ago (May 10 if current is May 19)
        },
        {
            "desc": "Air conditioning unit failure (Chiller 2) in food court kitchen zone causing high humidity and temperatures of 85°F. Cooking staff reports unbearable work conditions.",
            "zone": "food-court",
            "severity": "high",
            "status": "closed",
            "created_offset": 20,
            "closed_offset": 18
        }
    ]
    
    # Generate vector embeddings in batch
    all_descriptions = [item["desc"] for item in facilities_issues] + [item["desc"] for item in correlation_tickets]
    print(f"Generating semantic vector embeddings for {len(all_descriptions)} maintenance tickets...")
    vectors = embedder.encode(all_descriptions).tolist()
    
    idx = 0
    end_date = datetime.utcnow()
    
    # Index standard tickets
    for item in facilities_issues:
        created_at = end_date - timedelta(days=random.randint(1, 60))
        status = random.choice(["open", "closed", "in-progress"])
        closed_at = None
        if status == "closed":
            closed_at = (created_at + timedelta(days=random.randint(1, 5))).isoformat() + "Z"
            
        doc = {
            "_index": INDEX_MAINTENANCE_TICKETS,
            "_source": {
                "ticket_id": f"TKT-{random.randint(1000, 9999)}",
                "created_at": created_at.isoformat() + "Z",
                "closed_at": closed_at,
                "description": item["desc"],
                "description_vector": vectors[idx],
                "zone": item["zone"],
                "severity": item["severity"],
                "status": status,
                "assignee": fake.name()
            }
        }
        docs.append(doc)
        idx += 1
        
    # Index specific correlation tickets
    for item in correlation_tickets:
        created_at = end_date - timedelta(days=item["created_offset"])
        closed_at = None
        status = item.get("status", "open")
        if status == "closed":
            closed_at = (created_at + timedelta(days=item.get("closed_offset", 2))).isoformat() + "Z"
            
        doc = {
            "_index": INDEX_MAINTENANCE_TICKETS,
            "_source": {
                "ticket_id": f"TKT-{random.randint(1000, 9999)}",
                "created_at": created_at.isoformat() + "Z",
                "closed_at": closed_at,
                "description": item["desc"],
                "description_vector": vectors[idx],
                "zone": item["zone"],
                "severity": item["severity"],
                "status": status,
                "assignee": fake.name()
            }
        }
        docs.append(doc)
        idx += 1
        
    return docs

def generate_events_docs():
    print("Generating events-calendar documents...")
    docs = []
    end_date = datetime.utcnow()
    
    # Seed events
    events = [
        {"title": "Spring Fashion Parade & Catwalk", "zone": "fashion-district", "offset": -15, "duration": 4, "attendance": 1200, "impact": "high"},
        {"title": "International Food & Dessert Festival", "zone": "food-court", "offset": -5, "duration": 3, "attendance": 2500, "impact": "high"},
        {"title": "Local Indie Acoustic Live", "zone": "east-wing", "offset": -30, "duration": 2, "attendance": 600, "impact": "medium"},
        {"title": "Future Tech & VR Showcase", "zone": "electronics-wing", "offset": -45, "duration": 5, "attendance": 1800, "impact": "high"},
        {"title": "Spring Cleaning Sale Promotion", "zone": "west-wing", "offset": -22, "duration": 3, "attendance": 400, "impact": "low"},
        
        # Flow 2/4 Target Correlation: Major concert scheduled in East Wing for upcoming weekend
        {"title": "Summer Rock Fest & Artist Concert", "zone": "east-wing", "offset": 4, "duration": 2, "attendance": 3500, "impact": "critical"},
        {"title": "Electronics Mega Weekend Sale", "zone": "electronics-wing", "offset": 12, "duration": 3, "attendance": 1500, "impact": "high"}
    ]
    
    for item in events:
        start_time = end_date + timedelta(days=item["offset"])
        end_time = start_time + timedelta(hours=item["duration"])
        
        doc = {
            "_index": INDEX_EVENTS_CALENDAR,
            "_source": {
                "event_id": f"EVT-{random.randint(100, 999)}",
                "title": item["title"],
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "zone": item["zone"],
                "expected_attendance": item["attendance"],
                "impact_level": item["impact"]
            }
        }
        docs.append(doc)
    return docs

def generate_promotions_docs():
    print("Generating promotions-history documents...")
    docs = []
    end_date = datetime.utcnow()
    
    promotions = [
        {
            "title": "East Wing Spring Apparel Blowout",
            "copy": "Sizzling spring savings! Get up to 40% off premium sneakers, jackets, and streetwear accessories at SneakerVault and Urban Threads in the East Wing all weekend long.",
            "zone": "east-wing",
            "tenants": ["sneakervault", "urbanthreads"],
            "lift": 22.4,
            "offset": -30
        },
        {
            "title": "Summer Taste Food Court Special",
            "copy": "Treat your taste buds! Buy one get one free combos at Burger Barn, Sushi Express, and Café Bloom. Discover new flavors at the level 1 food court this week.",
            "zone": "food-court",
            "tenants": ["burgerbarn", "sushiexpress", "cafebloom"],
            "lift": 18.2,
            "offset": -45
        },
        {
            "title": "Electronics Wing Upgrade Extravaganza",
            "copy": "Power up your devices! Huge rebates on smartphones, headsets, laptops, and virtual reality consoles at TechZone and ByteShop. Located on floor 2.",
            "zone": "electronics-wing",
            "tenants": ["techzone", "byteshop"],
            "lift": 14.8,
            "offset": -12
        },
        {
            "title": "Midweek Quick Services Discount",
            "copy": "Get it fixed! 15% discount on phone repair or premium styling services at QuickFix Phones and GlamCuts Salon. Quick, convenient, and affordable.",
            "zone": "services-hub",
            "tenants": ["quickfix", "glamcuts"],
            "lift": 3.5,
            "offset": -60
        },
        {
            "title": "Spring Fashion District Styling Campaign",
            "copy": "Elevate your style! Enjoy complimentary fashion styling consults plus 20% off all modern apparel collections at FashionHub and StyleCraft in the Fashion District.",
            "zone": "fashion-district",
            "tenants": ["fashionhub", "stylecraft"],
            "lift": 24.1,
            "offset": -40
        }
    ]
    
    # Generate vectors
    print("Generating semantic vector embeddings for promotions...")
    all_copies = [p["copy"] for p in promotions]
    vectors = embedder.encode(all_copies).tolist()
    
    for idx, item in enumerate(promotions):
        start_date = end_date + timedelta(days=item["offset"])
        end_date_promo = start_date + timedelta(days=4)
        
        doc = {
            "_index": INDEX_PROMOTIONS_HISTORY,
            "_source": {
                "campaign_id": f"CAM-{random.randint(100, 999)}",
                "title": item["title"],
                "copy_text": item["copy"],
                "copy_vector": vectors[idx],
                "participating_tenants": item["tenants"],
                "zone": item["zone"],
                "sales_lift_percent": item["lift"],
                "start_date": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                "end_date": end_date_promo.strftime("%Y-%m-%dT00:00:00Z")
            }
        }
        docs.append(doc)
    return docs

def generate_mall_directory_docs():
    print("Generating mall-directory documents...")
    docs = []
    for tenant in TENANTS:
        zone_name = tenant["zone"]
        zone_coords = ZONES.get(zone_name, {"lat": 24.7130, "lon": 46.6745, "floor": 1})
        doc = {
            "_index": INDEX_MALL_DIRECTORY,
            "_source": {
                "store_id": tenant["store_id"],
                "store_name": tenant["store_name"],
                "category": tenant["category"],
                "floor": tenant["floor"],
                "zone": tenant["zone"],
                "location": {
                    "lat": zone_coords["lat"],
                    "lon": zone_coords["lon"]
                },
                "description": f"Premium {tenant['category']} store located in {tenant['zone']} on floor {tenant['floor']}.",
                "keywords": [tenant["store_name"].lower(), tenant["category"].lower(), tenant["zone"].lower()]
            }
        }
        docs.append(doc)
        
    # Also seed physical entry and exit zones for agent location queries
    for zone_name, zone_info in ZONES.items():
        if "entrance" in zone_name or "parking" in zone_name:
            doc = {
                "_index": INDEX_MALL_DIRECTORY,
                "_source": {
                    "store_id": zone_name,
                    "store_name": zone_name.replace("-", " ").title(),
                    "category": "navigation",
                    "floor": zone_info["floor"],
                    "zone": zone_name,
                    "location": {
                        "lat": zone_info["lat"],
                        "lon": zone_info["lon"]
                    },
                    "description": f"Mall access point: {zone_name.replace('-', ' ').title()}.",
                    "keywords": [zone_name.replace("-", " "), "entrance", "parking", "start"]
                }
            }
            docs.append(doc)
            
    return docs

def seed_database():
    es = get_es_client()
    create_index_mappings(es)
    
    # Collect all docs
    docs = []
    docs.extend(generate_foot_traffic_docs(90))
    docs.extend(generate_tenant_sales_docs(90))
    docs.extend(generate_maintenance_tickets_docs())
    docs.extend(generate_events_docs())
    docs.extend(generate_promotions_docs())
    docs.extend(generate_mall_directory_docs())
    
    print(f"\nTotal prepared documents: {len(docs)}")
    print("Starting bulk index ingestion into Elastic Cloud Serverless...")
    
    success, errors = helpers.bulk(es, docs, chunk_size=500)
    print(f"Index Operation completed: successfully indexed {success} documents.")
    if errors:
        print(f"Errors occurred: {errors}")
        sys.exit(1)
        
    print("\nDatabase seeding completed successfully! Verification stats:")
    for idx_name in ALL_INDICES:
        count_res = es.count(index=idx_name)
        print(f"  - Index '{idx_name}': {count_res['count']} documents.")

if __name__ == "__main__":
    seed_database()
