import os
from dotenv import load_dotenv

# Load workspace env variables
load_dotenv()
backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)

# Elastic Cloud Connection parameters
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY", "")

# Index Names
INDEX_FOOT_TRAFFIC = "foot-traffic"
INDEX_TENANT_SALES = "tenant-sales"
INDEX_MAINTENANCE_TICKETS = "maintenance-tickets"
INDEX_EVENTS_CALENDAR = "events-calendar"
INDEX_PROMOTIONS_HISTORY = "promotions-history"
INDEX_MALL_DIRECTORY = "mall-directory"
INDEX_CUSTOMER_COUPONS = "customer-coupons"

ALL_INDICES = [
    INDEX_FOOT_TRAFFIC,
    INDEX_TENANT_SALES,
    INDEX_MAINTENANCE_TICKETS,
    INDEX_EVENTS_CALENDAR,
    INDEX_PROMOTIONS_HISTORY,
    INDEX_MALL_DIRECTORY,
    INDEX_CUSTOMER_COUPONS
]

# Mall geographic and semantic structure
ZONES = {
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

TENANTS = [
    {"store_id": "techzone", "store_name": "TechZone", "zone": "electronics-wing", "category": "electronics", "floor": 2},
    {"store_id": "byteshop", "store_name": "ByteShop", "zone": "electronics-wing", "category": "electronics", "floor": 2},
    {"store_id": "fashionhub", "store_name": "FashionHub", "zone": "fashion-district", "category": "apparel", "floor": 1},
    {"store_id": "stylecraft", "store_name": "StyleCraft", "zone": "fashion-district", "category": "apparel", "floor": 1},
    {"store_id": "urbanthreads", "store_name": "Urban Threads", "zone": "east-wing", "category": "apparel", "floor": 1},
    {"store_id": "burgerbarn", "store_name": "Burger Barn", "zone": "food-court", "category": "food", "floor": 1},
    {"store_id": "sushiexpress", "store_name": "Sushi Express", "zone": "food-court", "category": "food", "floor": 1},
    {"store_id": "pizzapalace", "store_name": "Pizza Palace", "zone": "food-court", "category": "food", "floor": 1},
    {"store_id": "cafebloom", "store_name": "Café Bloom", "zone": "food-court", "category": "food", "floor": 1},
    {"store_id": "quickfix", "store_name": "QuickFix Phones", "zone": "services-hub", "category": "services", "floor": 3},
    {"store_id": "glamcuts", "store_name": "GlamCuts Salon", "zone": "services-hub", "category": "services", "floor": 3},
    {"store_id": "sneakervault", "store_name": "SneakerVault", "zone": "east-wing", "category": "apparel", "floor": 1},
    {"store_id": "homestyle", "store_name": "HomeStyle", "zone": "west-wing", "category": "home", "floor": 1},
    {"store_id": "booknook", "store_name": "BookNook", "zone": "west-wing", "category": "lifestyle", "floor": 1}
]
