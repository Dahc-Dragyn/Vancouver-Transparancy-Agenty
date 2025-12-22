import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

test_signal = {
    'subscriber_id': 'sub_chloe',
    'industry': 'Roadside Coffee Retail',
    'score': 10,
    'analysis': '### URGENT OPPORTUNITY\nThe City Council has just approved a new subsidy for Roadside Coffee Retailers for the 2026 fiscal year. Applications open next month.',
    'status': 'unread',
    'timestamp': datetime.now()
}

db.collection('signals').add(test_signal)
print('🚀 High-Value Test Signal successfully seeded in Firestore.')