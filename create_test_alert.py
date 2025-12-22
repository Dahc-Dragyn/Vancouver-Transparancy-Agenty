import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# This signal is 'unread' and has a score of 10, so it WILL trigger the dispatcher.
dummy_signal = {
    "subscriber_id": "sub_chloe",  # Matches the ID in your seed_subscribers script
    "industry": "Roadside Coffee Retail",
    "score": 10,
    "analysis": "### PRIORITY OPPORTUNITY\nCity Council has approved a 50% reduction in permit fees for roadside businesses starting Jan 1st.",
    "status": "unread",
    "timestamp": datetime.now()
}

db.collection("signals").add(dummy_signal)
print("🚀 High-value signal created for Chloe. Ready for dispatch.")