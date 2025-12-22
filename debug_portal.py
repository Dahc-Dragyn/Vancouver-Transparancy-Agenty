import asyncio
from playwright.async_api import async_playwright

async def debug_vancouver_portal():
    url = "https://vancouverwa.portal.civicclerk.com/"
    print(f"🕵️  Inspecting Portal: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        
        # 1. Take a screenshot so we can see what the bot sees
        await page.screenshot(path="portal_debug.png")
        print("📸 Screenshot saved as 'portal_debug.png'")
        
        # 2. Extract all table rows
        print("\n📋 All visible board names/rows found on page:")
        rows = await page.locator("tr").all()
        for i, row in enumerate(rows):
            text = await row.inner_text()
            # Clean up the text for display
            clean_text = " | ".join([t.strip() for t in text.split('\t') if t.strip()])
            if clean_text:
                print(f"  [{i}] {clean_text}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_vancouver_portal())