import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        target_url = "https://vancouverwa.portal.civicclerk.com/"
        print(f"🔗 Re-connecting to {target_url}...")
        
        try:
            await page.goto(target_url, wait_until="networkidle")
            
            # 1. Wait for the list to load
            print("⏳ Waiting for City Council entry...")
            await page.wait_for_selector("text=City Council Meeting", timeout=20000)

            # 2. Find the City Council Meeting entry and click it
            # We target the specific text to ensure we are clicking the right meeting
            cc_meeting = page.get_by_text("City Council Meeting").first
            
            print("🖱️ Clicking the City Council Meeting to reveal files...")
            await cc_meeting.click()
            
            # 3. Wait for the file links to appear
            # CivicClerk usually loads these in a secondary div or list
            print("⏳ Searching for file links (Agenda, Plain Text, etc.)...")
            await asyncio.sleep(3) # Short sleep to allow the drawer to slide open
            
            # Common link patterns in CivicClerk
            links = await page.query_selector_all("a")
            
            found_files = []
            for link in links:
                text = await link.inner_text()
                if any(word in text for word in ["Agenda", "Packet", "Text", "Minutes"]):
                    found_files.append(text.strip())

            if found_files:
                print(f"\n✅ Success! Found {len(found_files)} files for this meeting:")
                for i, file_name in enumerate(found_files):
                    print(f"   - {file_name}")
            else:
                print("\n⚠️ Clicked, but no file links were detected. We might need to target a specific 'Files' button.")
                # Take a screenshot to see why the links didn't show up
                await page.screenshot(path="debug_click.png")
                print("📸 Saved debug_click.png to check the UI.")

        except Exception as e:
            print(f"❌ Error during deep test: {e}")
        finally:
            await browser.close()
            print("\n🏁 Deep test complete.")

if __name__ == "__main__":
    asyncio.run(run_test())