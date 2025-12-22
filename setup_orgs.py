import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def update_vancouver_boards():
    print("🔄 Updating Vancouver Organization with Planning Commission...")
    org_ref = db.collection("organizations").document("vancouver-wa")
    
    # We are mapping internal IDs to the exact text found on the CivicClerk portal
    org_ref.update({
        "boards": {
            "city_council": "City Council Meeting",
            "planning_comm": "Planning Commission" 
        }
    })
    print("✅ Planning Commission added to 'vancouver-wa' boards.")

if __name__ == "__main__":
    update_vancouver_boards()