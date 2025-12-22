import os
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

def test_save():
    print("🚀 Testing Firestore write...")
    doc_ref = db.collection("signals").document()
    doc_ref.set({
        "userId": "chad_manual_test",
        "industry": "Telecom",
        "analysis": "This is a manual test of the database memory.",
        "timestamp": datetime.now(),
        "status": "verified"
    })
    print(f"✅ Success! Check Firebase for Document ID: {doc_ref.id}")

if __name__ == "__main__":
    test_save()