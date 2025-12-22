import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # New correct URL for Vancouver, WA
        target_url = "https://vancouverwa.portal.civicclerk.com/"
        
        print(f"🔗 Connecting to {target_url}...")
        
        try:
            # Navigate and wait for the app to initialize
            await page.goto(target_url, wait_until="networkidle")
            
            # CivicClerk can be slow. We'll wait for the main list container.
            print("⏳ Waiting for CivicClerk to render meetings...")
            
            # We look for a common text string 'City Council' or a link to ensure it's loaded
            await page.wait_for_selector("text=City Council", timeout=20000)

            # Let's pull the text of the first few 'cards' or meeting entries
            # CivicClerk usually uses divs for rows. We'll grab all text within the main content area.
            entries = await page.query_selector_all("div[role='listitem'], .event-row, .meeting-item")
            
            # If those generic selectors fail, we'll try to find all headers
            if not entries:
                 entries = await page.query_selector_all("h1, h2, h3")

            print(f"\n✅ Connection Successful! Found {len(entries)} items on the page.\n")
            print("--- First 5 Items Found ---")
            
            for i, entry in enumerate(entries[:5]):
                text = await entry.inner_text()
                # Clean up the text for a short preview
                preview = " ".join(text.split()[:15]) 
                print(f"{i+1}. {preview}...")

        except Exception as e:
            print(f"❌ Failed to pull data: {e}")
            await page.screenshot(path="vancouver_error.png")
            print("📸 Error screenshot saved to vancouver_error.png")

        finally:
            await browser.close()
            print("\n🏁 Test complete.")

if __name__ == "__main__":
    asyncio.run(run_test())