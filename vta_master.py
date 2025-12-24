import os
import asyncio
import json
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 1. SETUP
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"
load_dotenv()

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# 2. DATABASE HYGIENE
def cleanup_old_signals():
    print("🧹 [Hygiene] Scanning for stale archived signals...")
    cutoff = datetime.now() - timedelta(days=21)
    
    stale_query = db.collection("signals")\
        .where(filter=FieldFilter("status", "==", "archived"))\
        .where(filter=FieldFilter("timestamp", "<", cutoff))
    
    batch = db.batch()
    count = 0
    docs = stale_query.stream()
    
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            
    if count > 0:
        batch.commit()
        print(f"   Deleted {count} stale signals older than {cutoff.date()}.")
    else:
        print("   Database is clean.")

# 3. THE SCOUT (H3-Surgical Peek)
async def get_latest_meeting_fingerprint(url: str, board_name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(5) 

            h3_selector = f"h3:has-text('{board_name}')"
            header = page.locator(h3_selector).first
            container = page.locator(f"xpath=//h3[contains(., '{board_name}')]/ancestor::div[contains(@class, 'Mui')][1]")
            
            if await header.count() > 0:
                card_text = await container.inner_text() if await container.count() > 0 else await header.inner_text()
                fingerprint = " ".join(card_text.split())
                await browser.close()
                return fingerprint
            else:
                await browser.close()
                return None
        except Exception:
            await browser.close()
            return None

# 4. THE SCRAPER
async def scrape_portal_content(url: str, board_name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await page.click(f"text='{board_name}'")
            await asyncio.sleep(5) 
            content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return content[:45000]
        except Exception as e:
            print(f"❌ Scraper Error: {e}")
            await browser.close()
            return None

# 5. THE LIBRARIAN (Fixed JSON Parser)
def analyze_meeting_holistically(board_name: str, raw_text: str):
    print(f"🏛️  [The Librarian] Analyzing {board_name} for public impact...")
    
    prompt = f"""
    You are a veteran City Hall Reporter. Analyze this meeting transcript.
    
    1. SUMMARY: A 3-sentence executive summary.
    2. TOPICS: List top 5 topics.
    3. KEYWORDS: Specific project names/locations.
    4. PUBLIC_SCORE: Rate significance 1-10 (7+ is Major News).
    5. PUBLIC_ANALYSIS: One paragraph on WHY it matters.

    Return ONLY valid JSON. No markdown formatting. No intro text.
    {{
      "summary": "...",
      "topics": ["..."],
      "keywords": ["..."],
      "public_score": 5,
      "public_analysis": "..."
    }}
    
    TEXT: {raw_text[:35000]}
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text
        
        # 🛠️ FIX: Use Regex to find the JSON object {...}
        # This ignores any text before or after the curly braces
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            clean_json = json_match.group(0)
            data = json.loads(clean_json)
            return data
        else:
            raise ValueError("No JSON found in response")

    except Exception as e:
        print(f"   ⚠️ Librarian Error: {e}")
        # print(f"   DEBUG RAW: {response.text}") # Uncomment if it fails again
        return {
            "summary": "Automated processing failed.",
            "topics": ["Unprocessed"],
            "keywords": [],
            "public_score": 0,
            "public_analysis": "Error during analysis."
        }

# 6. THE MASTER LOOP
async def run_vta_production_cycle():
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Starting VTA Intelligence Cycle v3.0 (Archive Mode)")

    cleanup_old_signals()

    orgs = db.collection("organizations").stream()
    
    for org_doc in orgs:
        org_data = org_doc.to_dict()
        portal_url = org_data.get("portal_url")
        boards = org_data.get("boards", {})
        bookmarks = org_data.get("last_processed", {})

        for board_key, board_name in boards.items():
            print(f"\n📡 [Step 1: Check] Board: {board_name}")
            
            current_fp = await get_latest_meeting_fingerprint(portal_url, board_name)
            last_seen = bookmarks.get(board_key, "")

            if current_fp is None:
                print(f"⏭️  Skipping: Board not visible.")
                continue

            if current_fp == last_seen:
                print(f"⏭️  Skipping: Already processed.")
                continue

            print(f"🆕 NEW CONTENT FOUND: {board_name}...")
            raw_text = await scrape_portal_content(portal_url, board_name)
            if not raw_text: continue

            # --- PHASE 2: INGEST FIRST (The Librarian) ---
            archive_data = analyze_meeting_holistically(board_name, raw_text)
            
            record_id = re.sub(r'\W+', '_', board_key) + "_" + datetime.now().strftime("%Y%m%d")
            
            db.collection("meeting_records").document(record_id).set({
                "board_name": board_name,
                "org_id": org_doc.id,
                "timestamp": datetime.now(),
                
                # NEW FIELDS FOR DASHBOARD
                "summary": archive_data.get("summary"),
                "topics": archive_data.get("topics"),
                "keywords": archive_data.get("keywords"),
                "score": archive_data.get("public_score", 0),          # Public Score
                "analysis": archive_data.get("public_analysis", ""),   # Public Analysis
                
                "raw_text_snippet": raw_text[:2000]
            })
            print(f"   💾 Meeting Archived (Public Score: {archive_data.get('public_score')}/10).")

            # --- PHASE 3: FILTER LATER (The Watchdog) ---
            profiles = db.collection("interest_profiles").where(filter=FieldFilter("active", "==", True)).stream()
            
            for prof_doc in profiles:
                prof = prof_doc.to_dict()
                print(f"   🧠 [Watchdog] Checking for {prof['industry']}...")

                prompt = f"""
                You are a "Paranoid Risk Assessor" for the {prof['industry']} industry.
                User Keywords: {prof['keywords']}
                Exclusions: {prof['exclusions']}

                Analyze the text. 
                - If there is ANY remote relevance (even minor), Score it 1-5.
                - If there is clear direct impact, Score it 6-8.
                - If there is critical urgency, Score it 9-10.

                Return your response in this EXACT format:
                SCORE: [1-10]
                REASON: [Short explanation of the score]
                ANALYSIS: [Full professional briefing]

                Only return "NO_SIGNAL" if 100% unrelated.
                
                TEXT: {raw_text}
                """

                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                output = response.text

                if "NO_SIGNAL" not in output:
                    score_match = re.search(r"SCORE:\s*(\d+)", output)
                    score = int(score_match.group(1)) if score_match else 1
                    
                    db.collection("signals").add({
                        "subscriber_id": prof['subscriber_id'],
                        "profile_id": prof_doc.id,
                        "industry": prof['industry'],
                        "score": score,
                        "analysis": output,
                        "related_meeting_id": record_id, # Link back to the master record
                        "timestamp": datetime.now(),
                        "status": "unread" if score >= 7 else "archived"
                    })
                    print(f"      ✅ ALERT GENERATED (Score: {score}/10)")
                else:
                    print(f"      🛑 No alert needed.")

            # Update Bookmark
            db.collection("organizations").document(org_doc.id).update({
                f"last_processed.{board_key}": current_fp
            })
            print(f"   🔖 Bookmark Updated.")

    print(f"\n🏁 [{datetime.now().strftime('%H:%M:%S')}] Cycle Complete.")

if __name__ == "__main__":
    asyncio.run(run_vta_production_cycle())