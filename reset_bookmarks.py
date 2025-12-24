import firebase_admin
from firebase_admin import credentials, firestore

# Initialize (Standard Boilerplate)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def reset_bookmarks():
    print("🧠 Wiping VTA Memory (Bookmarks)...")
    
    # Get all organizations (e.g., City of Vancouver)
    orgs = db.collection("organizations").stream()
    
    count = 0
    for org in orgs:
        print(f"   - Resetting state for: {org.id}")
        # We overwrite 'last_processed' with an empty map.
        # This forces the bot to treat EVERYTHING as a new meeting.
        org.reference.update({"last_processed": {}})
        count += 1
        
    print(f"✅ Reset {count} organizations. The bot is now 'fresh'.")
    print("👉 Now run: python vta_master.py")

if __name__ == "__main__":
    reset_bookmarks()