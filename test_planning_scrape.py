import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Import your scrape_portal function here or use a dummy version for testing
async def run_planning_test():
    print("🕵️ Testing Planning Commission Scrape...")
    
    # We target the actual Vancouver portal
    url = "https://vancouverwa.portal.civicclerk.com/"
    board_text = "Planning Commission"
    
    # (In a real run, you'd call the scrape_portal function)
    # For now, let's simulate the Planning Commission result:
    simulated_planning_text = """
    Planning Commission Item 2.1: Public hearing regarding the rezoning of 
    500 acres in East Vancouver from Industrial to Mixed-Use Residential.
    Development will include 400 multi-family units and retail space.
    """
    
    prompt = f"""
    Analyze this Planning Commission update for a Construction company.
    Keywords: [rezoning, development, multi-family]
    
    Provide a SEVERITY and BUSINESS IMPACT analysis.
    Text: {simulated_planning_text}
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-09-2025",
        contents=prompt
    )
    
    print("-" * 30)
    print(f"🤖 ANALYSIS:\n{response.text}")

if __name__ == "__main__":
    asyncio.run(run_planning_test())