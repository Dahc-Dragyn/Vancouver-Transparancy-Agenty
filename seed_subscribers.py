import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def seed_subscribers():
    print("🌱 Seeding Multi-Tenant Test Data...")
    
    # 1. THE CONTRACTOR
    sub1 = {"email": "ian@infrastructure.com", "status": "active", "tier": "pro"}
    db.collection("subscribers").document("sub_ian").set(sub1)
    
    db.collection("interest_profiles").document("prof_ian_road").set({
        "subscriber_id": "sub_ian",
        "industry": "Civil Engineering & Construction",
        "keywords": ["paving", "RFP", "bid", "street restoration"],
        "exclusions": ["residential", "private"],
        "active": True
    })

    # 2. THE COFFEE STAND
    sub2 = {"email": "chloe@coffee-stand.com", "status": "active", "tier": "basic"}
    db.collection("subscribers").document("sub_chloe").set(sub2)
    
    db.collection("interest_profiles").document("prof_chloe_retail").set({
        "subscriber_id": "sub_chloe",
        "industry": "Roadside Coffee Retail",
        "keywords": ["Road Closure", "Detour", "Water Main"],
        "exclusions": ["zoning change"],
        "active": True
    })

    print("✅ Seeded Ian (Contractor) and Chloe (Coffee Stand).")

if __name__ == "__main__":
    seed_subscribers()