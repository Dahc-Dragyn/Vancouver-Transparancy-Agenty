import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Configuration
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"

load_dotenv()

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

async def get_latest_meeting_title(url: str, board_search_text: str):
    """
    Peeks at the portal to grab the most recent meeting date/title string.
    Used to determine if a full scrape is necessary.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            # Find the row containing the board name
            # We assume the portal lists the most recent meeting first
            selector = f"text={board_search_text}"
            meeting_element = page.locator(selector).first
            
            # Extract the full text of that row (usually contains Date + Board Name)
            # This becomes our unique 'bookmark'
            title = await meeting_element.inner_text()
            await browser.close()
            return title.strip()
        except Exception as e:
            print(f"⚠️  Could not peek at {board_search_text}: {e}")
            await browser.close()
            return None

async def scrape_portal(url: str, board_search_text: str):
    """Full scrape logic (from previous step)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...") # Same UA as above
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await page.click(f"text={board_search_text}")
            await asyncio.sleep(5) 
            content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return content[:40000]
        except Exception:
            await browser.close()
            return None

async def run_vta_production_cycle():
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Starting State-Aware Cycle")

    orgs = db.collection("organizations").stream()
    
    for org_doc in orgs:
        org_id = org_doc.id
        org_data = org_doc.to_dict()
        portal_url = org_data.get("portal_url")
        boards = org_data.get("boards", {})
        # Load existing bookmarks for this org
        bookmarks = org_data.get("last_processed", {})

        for board_id, board_name in boards.items():
            # 1. PEAK: Check for new content
            current_meeting_id = await get_latest_meeting_title(portal_url, board_name)
            last_seen = bookmarks.get(board_id, "")

            if current_meeting_id and current_meeting_id == last_seen:
                print(f"⏭️  Skipping {board_name}: Already processed '{last_seen}'")
                continue

            print(f"📡 New Meeting Found: '{current_meeting_id}'. Scraping...")
            
            # 2. FULL SCRAPE
            raw_text = await scrape_portal(portal_url, board_name)
            if not raw_text:
                continue

            # 3. ANALYSIS LOOP
            profiles = db.collection("interest_profiles").where(filter=FieldFilter("active", "==", True)).stream()
            for prof_doc in profiles:
                prof = prof_doc.to_dict()
                
                prompt = f"Analyze for {prof['industry']} (Keywords: {prof['keywords']}): {raw_text}"
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                
                if "NO_SIGNAL" not in response.text:
                    db.collection("signals").add({
                        "subscriber_id": prof['subscriber_id'],
                        "analysis": response.text,
                        "board": board_name,
                        "timestamp": datetime.now()
                    })
                    print(f"✅ Signal found for {prof['subscriber_id']}")

            # 4. UPDATE BOOKMARK
            # We save the exact string we saw in Step 1 to Firestore
            db.collection("organizations").document(org_id).update({
                f"last_processed.{board_id}": current_meeting_id
            })
            print(f"🔖 Bookmark updated: {board_name} -> {current_meeting_id}")

if __name__ == "__main__":
    asyncio.run(run_vta_production_cycle())