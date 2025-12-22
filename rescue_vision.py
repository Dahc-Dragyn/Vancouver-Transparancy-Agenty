import asyncio
import json
from playwright.async_api import async_playwright

async def run_rescue_vision():
    url = "https://vancouverwa.portal.civicclerk.com/"
    print(f"🕵️  STARTING VISION RESCUE: {url}")
    
    async with async_playwright() as p:
        # We use a non-headless mode for one run if you were local, 
        # but on a server, we use extra slow-motion to ensure rendering.
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print("🌐 Navigating to portal...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 1. Give the dynamic 'Coming Up' widgets extra time to breathe
            print("⏳ Waiting 15 seconds for dynamic widgets to hydrate...")
            await asyncio.sleep(15)
            
            # 2. Capture the Full Page State for Debugging
            await page.screenshot(path="rescue_vision_debug.png", full_page=True)
            print("📸 Full-page screenshot saved as 'rescue_vision_debug.png'")

            # 3. Check for iFrames (The 'Ghost' Website Problem)
            frames = page.frames
            print(f"🖼️  Detected {len(frames)} frames on page.")
            for i, frame in enumerate(frames):
                print(f"   Frame {i}: {frame.url[:60]}...")

            # 4. Deep Text Search: Find every element that mentions a Board
            print("\n🔍 PROBING DOM FOR KEYWORD MATCHES:")
            search_terms = ["Council", "Planning", "Commission", "Redevelopment"]
            
            # This Javascript snippet runs inside the browser and finds the exact 
            # HTML tags and classes containing our boards.
            matches = await page.evaluate("""(terms) => {
                let results = [];
                terms.forEach(term => {
                    let elements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.includes(term) && el.children.length === 0);
                    
                    elements.forEach(el => {
                        results.push({
                            term: term,
                            tag: el.tagName,
                            class: el.className,
                            text: el.innerText.trim(),
                            visible: el.offsetWidth > 0 && el.offsetHeight > 0
                        });
                    });
                });
                return results;
            }""", search_terms)

            for m in matches:
                status = "✅ VISIBLE" if m['visible'] else "❌ HIDDEN"
                print(f"   Match [{m['term']}]: <{m['tag']} class='{m['class']}'> | Text: {m['text']} | {status}")

            # 5. Extract the entire visible text layer
            print("\n📝 RAW ACCESSIBILITY TEXT LAYER:")
            raw_text = await page.evaluate("() => document.body.innerText")
            with open("portal_text_dump.txt", "w") as f:
                f.write(raw_text)
            print("💾 Full text dump saved to 'portal_text_dump.txt'")

        except Exception as e:
            print(f"❌ CRITICAL VISION FAILURE: {e}")
        
        finally:
            await browser.close()
            print("\n🏁 Vision Rescue Complete. Analyze 'rescue_vision_debug.png' and the logs above.")

if __name__ == "__main__":
    asyncio.run(run_rescue_vision())