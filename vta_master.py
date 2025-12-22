import os
import asyncio
import json
import re
from datetime import datetime
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

# 2. THE SCOUT (H3-Surgical Peek)
async def get_latest_meeting_fingerprint(url: str, board_name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(5) # Allow Material UI components to hydrate

            # Target the H3 headers identified in Rescue Vision
            h3_selector = f"h3:has-text('{board_name}')"
            header = page.locator(h3_selector).first
            
            # Find the nearest Material UI card container
            container = page.locator(f"xpath=//h3[contains(., '{board_name}')]/ancestor::div[contains(@class, 'Mui')][1]")
            
            if await header.count() > 0:
                # Capture the full card text (includes dates) for the bookmark
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

# 3. THE SCRAPER
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

# 4. THE MASTER LOOP
async def run_vta_production_cycle():
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Starting VTA Intelligence Cycle v2.2")

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
                print(f"⏭️  Skipping: Board not currently visible on portal.")
                continue

            if current_fp == last_seen:
                print(f"⏭️  Skipping: Already processed (Bookmark match).")
                continue

            print(f"🆕 NEW CONTENT FOUND: {board_name}...")
            raw_text = await scrape_portal_content(portal_url, board_name)
            if not raw_text: continue

            profiles = db.collection("interest_profiles").where(filter=FieldFilter("active", "==", True)).stream()
            
            for prof_doc in profiles:
                prof = prof_doc.to_dict()
                print(f"🧠 [Step 2: AI] Scoring relevance for {prof['industry']}...")

                prompt = f"""
                Analyze the following municipal meeting text for the {prof['industry']} industry.
                User Keywords: {prof['keywords']}
                Exclusions: {prof['exclusions']}

                Return your response in this EXACT format:
                SCORE: [1-10]
                REASON: [Short explanation of the score]
                ANALYSIS: [Full professional briefing]

                If the text is entirely irrelevant to the user's industry, return: NO_SIGNAL
                
                TEXT: {raw_text}
                """

                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                output = response.text

                if "NO_SIGNAL" not in output:
                    score_match = re.search(r"SCORE:\s*(\d+)", output)
                    score = int(score_match.group(1)) if score_match else 0
                    
                    db.collection("signals").add({
                        "subscriber_id": prof['subscriber_id'],
                        "profile_id": prof_doc.id,
                        "industry": prof['industry'],
                        "score": score,
                        "analysis": output,
                        "timestamp": datetime.now(),
                        "status": "unread" if score >= 7 else "archived"
                    })
                    print(f"   ✅ SIGNAL RECORDED (Score: {score}/10)")
                else:
                    print(f"   🛑 Noise Filtered.")

            # Update Bookmark
            db.collection("organizations").document(org_doc.id).update({
                f"last_processed.{board_key}": current_fp
            })
            print(f"🔖 State Bookmark Updated.")

    print(f"\n🏁 [{datetime.now().strftime('%H:%M:%S')}] Cycle Complete.")

if __name__ == "__main__":
    asyncio.run(run_vta_production_cycle())