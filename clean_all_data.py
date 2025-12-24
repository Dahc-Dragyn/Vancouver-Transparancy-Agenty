import firebase_admin
from firebase_admin import credentials, firestore

# Initialize
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def delete_all_signals():
    """Recursively deletes all documents in the signals collection."""
    signals_ref = db.collection("signals")
    docs = signals_ref.limit(50).stream()
    deleted = 0

    for doc in docs:
        print(f'   🗑️  Deleting signal: {doc.id} ({doc.to_dict().get("industry", "Unknown")})')
        doc.reference.delete()
        deleted += 1

    if deleted >= 50:
        return delete_all_signals()

def reset_bookmarks():
    """Resets the 'last_processed' flag on organizations."""
    orgs = db.collection("organizations").stream()
    for org in orgs:
        print(f"   🧠 Wiping memory for: {org.id}")
        org.reference.update({"last_processed": {}})

if __name__ == "__main__":
    print("⚠️  STARTING SYSTEM PURGE ⚠️")
    
    print("\n1. Deleting all Signals...")
    delete_all_signals()
    print("✅ Signals deleted.")

    print("\n2. Resetting Scraper Memory...")
    reset_bookmarks()
    print("✅ Memory wiped.")

    print("\n✨ System is clean. Run 'python vta_master.py' to fetch REAL data.")