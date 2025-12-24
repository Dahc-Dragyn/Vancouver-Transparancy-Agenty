import os
import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

SUBSTACK_EMAIL = "your-email@aiyoda.app" # Replace with your login email
SUBSTACK_PASSWORD = os.getenv("SUBSTACK_PASSWORD")
SUBSTACK_URL = "https://aiyoda.substack.com/publish"

async def post_to_substack(title: str, content_html: str):
    """
    Uses Playwright to log in to Substack and create a new draft.
    """
    print(f"🚀 [Publisher] Starting automated draft for: {title}")
    
    async with async_playwright() as p:
        # Launch browser (Headless=False useful for debugging login)
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Login Flow
            print("🔑 Logging in to Substack...")
            await page.goto("https://substack.com/sign-in")
            
            # Substack login can be tricky. We target the specific "Sign in with password" flow
            await page.fill('input[name="email"]', SUBSTACK_EMAIL)
            
            # Sometimes there is a "Sign in with password" text link to click
            # We assume the user has enabled password login
            try:
                await page.click("text=Sign in with password", timeout=3000)
            except:
                pass # The password field might just appear

            await page.fill('input[name="password"]', SUBSTACK_PASSWORD)
            await page.click('button[type="submit"]')
            
            # Wait for login to complete (look for the user avatar or dashboard)
            await page.wait_for_url("**/home**", timeout=30000)
            print("✅ Login Successful.")

            # 2. Go to Publisher Dashboard
            print("📝 Creating New Post...")
            await page.goto(SUBSTACK_URL)
            await asyncio.sleep(3) # Let the editor load

            # 3. Fill Title
            # Substack editor selectors are dynamic, but usually have aria-labels or placeholders
            await page.get_by_placeholder("Enter title").fill(title)
            await page.get_by_placeholder("Enter subtitle").fill("Weekly Intelligence Digest | Vancouver Transparency Agent")

            # 4. Fill Content
            # The editor is a "contenteditable" div. We can type or paste.
            # For HTML content, we need to be clever. 
            # Simple text insertion:
            editor = page.locator('.zk-editor') # This class name changes often.
            if await editor.count() == 0:
                # Fallback to role
                editor = page.get_by_role("textbox").nth(2) # Title, Subtitle, Body
            
            await editor.click()
            
            # We simulate "typing" the content or using clipboard paste
            # For this simple version, we strip HTML tags for safety or use simplified text
            clean_text = content_html.replace("<br>", "\n").replace("<div>", "").replace("</div>", "")
            await page.keyboard.insert_text(clean_text)

            # 5. Save and Exit
            print("💾 Saving Draft...")
            await asyncio.sleep(5) # Auto-save triggers
            
            # Optionally click "Settings" or verify "Saved" status
            # await page.click('[data-testid="post-settings-button"]')
            
            print(f"✅ Draft '{title}' saved to Substack!")
            
        except Exception as e:
            print(f"❌ Publishing failed: {e}")
            await page.screenshot(path="debug_publisher_error.png")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    # Test Run
    dummy_title = "The Machinery of Democracy: Weekly Digest"
    dummy_content = """
    This is a test automated draft from your VTA Agent.
    
    DATE: Dec 22, 2025
    TOPIC: Zoning & Permits
    
    The Planning Commission met yesterday to discuss...
    """
    asyncio.run(post_to_substack(dummy_title, dummy_content))