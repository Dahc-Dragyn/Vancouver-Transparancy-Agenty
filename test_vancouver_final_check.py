import asyncio
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a standard user agent helps avoid some "bot" detection
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        
        target_url = "https://vancouverwa.portal.civicclerk.com/"
        print(f"🔗 Connecting to {target_url}...")
        
        try:
            await page.goto(target_url, wait_until="networkidle")
            
            # 1. Locate the meeting
            print("⏳ Finding 'City Council Meeting'...")
            meeting_selector = "text=City Council Meeting"
            await page.wait_for_selector(meeting_selector)
            
            # 2. Click it
            print("🖱️ Clicking meeting...")
            await page.click(meeting_selector)
            
            # 3. Wait for the UI to change (increased wait for animation)
            print("⏳ Waiting 5s for the drawer/files to load...")
            await asyncio.sleep(5) 
            
            # 4. Dump ALL interactive elements
            print("\n--- DOM INSPECTION ---")
            
            # Get all links
            links = await page.query_selector_all("a")
            print(f"Found {len(links)} total links on page.")
            
            # Get all buttons (CivicClerk often uses buttons for the 'Plain Text' view)
            buttons = await page.query_selector_all("button")
            print(f"Found {len(buttons)} total buttons on page.")

            print("\n🔎 Searching for document-related keywords...")
            all_elements = links + buttons
            found = False
            
            for el in all_elements:
                text = await el.inner_text()
                # Clean up whitespace
                text = text.strip().replace('\n', ' ')
                
                # Check for any variation of document terms
                if any(word in text for word in ["Agenda", "Packet", "Text", "HTML", "PDF", "Minutes", "Files"]):
                    print(f"⭐ Potential Match: '{text}'")
                    found = True

            if not found:
                print("❌ Still no direct text matches. Let's look for ARIA labels...")
                # Sometimes buttons have no text but have an 'aria-label'
                for el in all_elements:
                    label = await el.get_attribute("aria-label")
                    if label and any(word in label for word in ["Agenda", "Packet", "Text"]):
                        print(f"⭐ Found via ARIA Label: '{label}'")
                        found = True

            # Final screenshot to visually confirm what is open
            await page.screenshot(path="final_debug_view.png")
            print("\n📸 Captured 'final_debug_view.png'. Check this to see the open drawer.")

        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()
            print("\n🏁 Final test complete.")

if __name__ == "__main__":
    asyncio.run(run_test())