import os
import asyncio
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Setup
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"
load_dotenv()

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# 2. Define the Test Scenarios
test_scenarios = [
    {
        "name": "Construction - Fee Hike",
        "industry": "Construction & Excavation",
        "keywords": ["Permit", "Fees", "Right-of-Way", "Engineering"],
        "snippet": "Council moved to increase Right-of-Way permit fees by 15% to cover rising administrative costs for the Engineering department."
    },
    {
        "name": "Construction - New Bid",
        "industry": "Civil Engineering",
        "keywords": ["RFP", "Bid", "Paving", "Street Restoration"],
        "snippet": "The 2026 Street Restoration plan was approved, earmarking $4M for repaving projects in the Heights neighborhood; RFPs to be issued in February."
    },
    {
        "name": "Coffee Stand - Road Closure",
        "industry": "Roadside Coffee Retail",
        "keywords": ["Road Closure", "Traffic", "Water Main"],
        "snippet": "Water main repairs on Mill Plain Blvd will require a full lane closure and detour for 3 weeks starting July 1st."
    },
    {
        "name": "Coffee Stand - Signage Law",
        "industry": "Small Business / Coffee Shop",
        "keywords": ["Signage", "A-Frame", "Code Enforcement"],
        "snippet": "Proposed updates to the code would prohibit unanchored A-frame signs on public sidewalks to ensure ADA compliance."
    },
    {
        "name": "Noise Test - Parks Naming",
        "industry": "Construction & Coffee Shop",
        "keywords": ["Zoning", "Development", "Permit"],
        "snippet": "The Parks Department announced the naming of the new community garden on 136th Ave after a local pioneer."
    }
]

async def run_suite():
    print(f"🚀 Launching Stress Test Suite using {MODEL_ID}...\n")
    
    for test in test_scenarios:
        print(f"🧪 Running: {test['name']}...")
        
        prompt = f"""
        Act as a Professional Regulatory Intelligence Agent.
        Analyze this meeting snippet for a user in the '{test['industry']}' industry.
        Keywords: {test['keywords']}

        If the text is relevant to the business, provide:
        - SEVERITY: (High/Medium/Low)
        - SUMMARY: What is happening?
        - SO WHAT: How does this impact their profit or operations?
        - DATE: Any deadlines or start dates?

        If the text is NOT relevant or is just general 'noise', return ONLY the word: NO_SIGNAL
        
        TEXT: {test['snippet']}
        """

        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        analysis = response.text

        # Record to Firestore
        doc_ref = db.collection("stress_tests").document()
        doc_ref.set({
            "test_name": test["name"],
            "industry": test["industry"],
            "analysis": analysis,
            "is_signal": "NO_SIGNAL" not in analysis,
            "timestamp": datetime.now()
        })

        print(f"   {'✅ Signal Found' if 'NO_SIGNAL' not in analysis else '🛑 Noise Filtered'}")
        print(f"   ID: {doc_ref.id}\n")

    print("🏁 All tests complete. Check the 'stress_tests' collection in Firestore!")

if __name__ == "__main__":
    asyncio.run(run_suite())