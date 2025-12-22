import os
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

async def run_multitenant_loop():
    # 1. Get ALL Active Profiles
    profiles = db.collection("interest_profiles").where("active", "==", True).stream()
    
    meeting_text = "Item 4.2: Water main repairs on Mill Plain Blvd will require a full lane closure and detour for 3 weeks starting July 1st. Paving RFPs for the restoration will be issued in late July."

    for doc in profiles:
        prof = doc.to_dict()
        prof_id = doc.id
        
        print(f"🧠 Analyzing for {prof['industry']}...")
        
        prompt = f"Analyze for {prof['industry']}: {meeting_text}. If relevant, return [SUMMARY] and [SO WHAT]. Else return NO_SIGNAL."

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-09-2025",
            contents=prompt
        )

        if "NO_SIGNAL" not in response.text:
            sig_ref = db.collection("signals").document()
            sig_ref.set({
                "profile_id": prof_id,
                "subscriber_id": prof['subscriber_id'],
                "industry": prof['industry'], # Added for better email context
                "analysis": response.text,
                "timestamp": datetime.now(),
                "status": "unread"  # <--- THIS WAS THE MISSING KEY
            })
            print(f"✅ Signal saved as 'unread' for {prof['subscriber_id']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_multitenant_loop())