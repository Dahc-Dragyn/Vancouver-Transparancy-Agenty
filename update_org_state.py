import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def initialize_state():
    org_ref = db.collection("organizations").document("vancouver-wa")
    # Initialize bookmarks as empty strings
    org_ref.update({
        "last_processed": {
            "city_council": "",
            "planning_comm": ""
        }
    })
    print("✅ Organization state bookmarks initialized.")

if __name__ == "__main__":
    initialize_state()