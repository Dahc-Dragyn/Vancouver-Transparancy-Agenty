import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def restore_vancouver():
    print("🏗️  Restoring Vancouver-WA Organization structure...")
    
    org_data = {
        "name": "Vancouver, WA",
        "portal_url": "https://vancouverwa.portal.civicclerk.com/",
        "last_processed": {},  # Empty so the next run is a "Full Scale Test"
        "boards": {
            "city_council": "City Council Meeting",
            "planning_comm": "Planning Commission - 4th Tuesday",
            "tmc": "Transportation and Mobility Commission",
            "ccra": "City Center Redevelopment Authority",
            "pac": "Parking Advisory Committee"
        }
    }
    
    # This restores the document the Master Controller is looking for
    db.collection("organizations").document("vancouver-wa").set(org_data)
    print("✅ Vancouver-WA restored with 5 active boards.")

if __name__ == "__main__":
    restore_vancouver()