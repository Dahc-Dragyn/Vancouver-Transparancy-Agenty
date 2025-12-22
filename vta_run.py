import os
import asyncio
import re
import resend
from datetime import datetime
from playwright.async_api import async_playwright
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 1. INITIALIZATION & CONFIG
load_dotenv()
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"
resend.api_key = os.getenv("RESEND_API_KEY")

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# -------------------------------------------------------------------
# STAGE 1: THE EYES (Surgical Scout & Scraper)
# -------------------------------------------------------------------

async def get_latest_meeting_fingerprint(url: str, board_name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5) 
            h3_selector = f"h3:has-text('{board_name}')"
            header = page.locator(h3_selector).first
            container = page.locator(f"xpath=//h3[contains(., '{board_name}')]/ancestor::div[contains(@class, 'Mui')][1]")
            
            if await header.count() > 0:
                card_text = await container.inner_text() if await container.count() > 0 else await header.inner_text()
                await browser.close()
                return " ".join(card_text.split())
            await browser.close()
            return None
        except Exception:
            await browser.close()
            return None

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
        except Exception:
            await browser.close()
            return None

# -------------------------------------------------------------------
# STAGE 2: THE VOICE (High-End Email Dispatcher)
# -------------------------------------------------------------------

def dispatch_alerts():
    print("\n📧 Dispatching High-Value Signals...")
    query = db.collection("signals")\
        .where(filter=FieldFilter("status", "==", "unread"))\
        .where(filter=FieldFilter("score", ">=", 7))
    
    signals = query.stream()
    for doc in signals:
        sig = doc.to_dict()
        sub_doc = db.collection("subscribers").document(sig['subscriber_id']).get()
        if not sub_doc.exists: continue
        
        email = sub_doc.to_dict().get("email")
        industry = sig.get('industry')
        score = sig.get('score')

        try:
            resend.Emails.send({
                "from": "Aiyoda Intelligence <alerts@aiyoda.app>",
                "to": [email],
                "subject": f"🚨 PRIORITY [{score}/10]: {industry} Intelligence Alert",
                "html": f"""
                <div style="background-color: #f4f7f9; padding: 40px 10px; font-family: sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border-top: 6px solid #1a2a40; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                        <div style="padding: 30px;">
                            <p style="text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-size: 11px; font-weight: 700; margin-bottom: 5px;">Aiyoda Municipal Intelligence</p>
                            <h1 style="color: #1a2a40; font-size: 22px; margin: 0;">Executive Briefing: {industry}</h1>
                        </div>
                        <div style="background-color: #1a2a40; padding: 15px 30px; color: #ffffff;">
                            <span style="background: #e2e8f0; color: #1a2a40; padding: 3px 10px; border-radius: 3px; font-weight: 800; margin-right: 10px;">SCORE: {score}/10</span>
                            <span style="font-size: 12px; text-transform: uppercase; color: #94a3b8;">Priority Signal Detected</span>
                        </div>
                        <div style="padding: 30px; color: #334155; line-height: 1.8;">
                            <div style="background: #f8fafc; padding: 20px; border-radius: 6px; border-left: 4px solid #cbd5e1;">
                                {sig['analysis'].replace('\n', '<br>')}
                            </div>
                        </div>
                        <div style="padding: 20px; text-align: center; background: #f8fafc;">
                            <p style="font-size: 11px; color: #94a3b8;">© 2025 Aiyoda Transparency Agent. Source: Vancouver, WA.</p>
                        </div>
                    </div>
                </div>
                """
            })
            db.collection("signals").document(doc.id).update({"status": "notified"})
            print(f"   ✅ Priority Alert Sent to {email}")
        except Exception as e:
            print(f"   ❌ Dispatch Error: {e}")

# -------------------------------------------------------------------
# STAGE 3: THE BRAIN (Main Logic)
# -------------------------------------------------------------------

async def main():
    print(f"🚀 [{datetime.now().strftime('%H:%M:%S')}] Aiyoda Intelligence Run Starting...")

    orgs = db.collection("organizations").stream()
    for org_doc in orgs:
        org_data = org_doc.to_dict()
        boards = org_data.get("boards", {})
        bookmarks = org_data.get("last_processed", {})

        for board_key, board_name in boards.items():
            print(f"\n📡 Scouting Board: {board_name}...")
            current_fp = await get_latest_meeting_fingerprint(org_data['portal_url'], board_name)
            
            if not current_fp or current_fp == bookmarks.get(board_key):
                print(f"⏭️  No new content for {board_name}.")
                continue

            print(f"🆕 NEW DATA: Scraping full content...")
            raw_text = await scrape_portal_content(org_data['portal_url'], board_name)
            if not raw_text: continue

            profiles = db.collection("interest_profiles").where(filter=FieldFilter("active", "==", True)).stream()
            for prof_doc in profiles:
                prof = prof_doc.to_dict()
                print(f"🧠 AI Scoring for {prof['industry']}...")
                
                prompt = f"Analyze this text for the {prof['industry']} industry (Keywords: {prof['keywords']}). Format: SCORE: [1-10], REASON: [Short], ANALYSIS: [Summary]. If irrelevant, return NO_SIGNAL.\n\nTEXT: {raw_text}"
                response = client.models.generate_content(model=MODEL_ID, contents=prompt)
                
                if "NO_SIGNAL" not in response.text:
                    score = int(re.search(r"SCORE:\s*(\d+)", response.text).group(1)) if "SCORE" in response.text else 0
                    db.collection("signals").add({
                        "subscriber_id": prof['subscriber_id'],
                        "industry": prof['industry'],
                        "score": score,
                        "analysis": response.text,
                        "timestamp": datetime.now(),
                        "status": "unread"
                    })
                    print(f"   ✅ Signal Created (Score: {score})")

            db.collection("organizations").document(org_doc.id).update({f"last_processed.{board_key}": current_fp})

    # Trigger the Dispatcher after processing all boards
    dispatch_alerts()
    print(f"\n🏁 [{datetime.now().strftime('%H:%M:%S')}] Run Complete.")

if __name__ == "__main__":
    asyncio.run(main())