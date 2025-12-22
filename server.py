import os
import asyncio
from datetime import datetime
from fastmcp import FastMCP
from playwright.async_api import async_playwright
from google import genai
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Configuration - Using the cheapest/efficient model per your instructions
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"

load_dotenv()

# Initialize Memory (Firestore)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccount.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Brain (Gemini 2.5)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

mcp = FastMCP("VancouverTransparencyAgent")

async def scrape_portal(url: str, board_search_text: str):
    """
    Flexible scraper that finds the correct board row and extracts data.
    Uses a real User Agent to minimize blocks.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1. Use a standard desktop User Agent to prevent CivicClerk/iCompass blocks
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {url}...")
            await page.goto(url, wait_until="networkidle")
            
            # 2. Look for the board name (e.g., 'Planning Commission')
            selector = f"text={board_search_text}"
            await page.wait_for_selector(selector, timeout=10000)
            
            print(f"🎯 Found {board_search_text}. Clicking...")
            await page.click(selector)
            
            # 3. Wait for the side-drawer or dynamic page content to load
            await asyncio.sleep(5) 
            
            # 4. Extract text content
            content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            
            # Return a large chunk optimized for Gemini 2.5 Flash-Lite's context window
            return content[:40000] 
            
        except Exception as e:
            print(f"❌ Error during scrape for {board_search_text}: {e}")
            await browser.close()
            return None

@mcp.tool()
async def run_intelligence_pass(org_id: str, board_id: str, user_id: str, industry: str, keywords: list[str]):
    """
    Fetches portal data based on Org/Board IDs, analyzes with Gemini 2.5, 
    and saves the 'Signal' to Firestore.
    """
    # 1. Look up the organization settings
    org_doc = db.collection("organizations").document(org_id).get()
    if not org_doc.exists:
        return f"Error: {org_id} not found in database."
    
    org_data = org_doc.to_dict()
    portal_url = org_data['portal_url']
    board_name = org_data['boards'].get(board_id)

    if not board_name:
        return f"Error: Board ID {board_id} not found for organization {org_id}."

    # 2. Scrape
    print(f"📡 Scraping {board_name} at {org_id}...")
    raw_text = await scrape_portal(portal_url, board_name)
    
    if not raw_text:
        return "❌ Scraping failed. Could not find the board or content timed out."

    # 3. Analyze with Gemini 2.5 Flash-Lite
    prompt = f"""
    You are a Strategic Business Intelligence Agent for {industry}.
    Analyze these municipal minutes for relevance to: {', '.join(keywords)}.
    
    If relevant items are found, provide a detailed impact analysis:
    - CATEGORY: (Regulatory/Financial/Infrastructure)
    - IMPACT: (How it affects {industry} specifically)
    - DEADLINES: (Dates mentioned)
    
    If no relevance is found, return ONLY the phrase: NO_RELEVANT_SIGNAL
    
    TEXT:
    {raw_text}
    """
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt
    )
    
    analysis = response.text

    # 4. Record the Signal
    if "NO_RELEVANT_SIGNAL" not in analysis:
        doc_ref = db.collection("signals").document()
        doc_ref.set({
            "orgId": org_id,
            "boardId": board_id,
            "userId": user_id,
            "industry": industry,
            "analysis": analysis,
            "timestamp": datetime.now(),
            "status": "unread",
            "model_used": MODEL_ID
        })
        return f"✅ Signal Recorded! (ID: {doc_ref.id})"
    
    return f"ℹ️ No matches found for {board_name}."

if __name__ == "__main__":
    mcp.run()