import time
import schedule
import subprocess
import logging
import asyncio
from datetime import datetime

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SCHEDULER] - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

def run_scout_process():
    """
    Runs the main VTA Master loop in a separate process.
    This ensures a clean Playwright/Browser session every time (prevents memory leaks).
    """
    logging.info("🚀 [Job: Scout] Starting vta_master.py...")
    try:
        # 'capture_output=True' allows us to log the script's print statements here
        result = subprocess.run(["python", "vta_master.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info(f"✅ [Job: Scout] Success.\nOutput Snippet: {result.stdout[-200:]}") # Log last 200 chars
        else:
            logging.error(f"❌ [Job: Scout] Failed.\nError: {result.stderr}")
            
    except Exception as e:
        logging.error(f"❌ [Job: Scout] Execution Exception: {e}")

def run_weekly_digest_pipeline():
    """
    Orchestrates the Digest creation and Substack publishing.
    Uses imports so we can pass the 'letter' text variable directly.
    """
    logging.info("☕ [Job: Digest] Starting Weekly Newsletter Pipeline...")
    
    try:
        # Import here to avoid early initialization issues
        import generate_weekly_digest
        import vta_publisher

        # 1. Generate the content
        logging.info("   1. Fetching signals and writing letter...")
        signals = generate_weekly_digest.fetch_weekly_signals()
        
        if not signals:
            logging.info("   ℹ️ No signals found this week. Skipping publication.")
            return

        letter_html = generate_weekly_digest.write_hcr_letter(signals)
        
        # 2. Publish to Substack
        title = f"The Machinery of Democracy: {datetime.now().strftime('%B %d, %Y')}"
        logging.info(f"   2. Publishing draft '{title}' to Substack...")
        
        # We need a fresh event loop for this async call
        asyncio.run(vta_publisher.post_to_substack(title, letter_html))
        
        logging.info("✅ [Job: Digest] Pipeline Complete. Draft saved.")
        
    except Exception as e:
        logging.error(f"❌ [Job: Digest] Failed: {e}")

# --- SCHEDULE CONFIGURATION ---

# 1. The Scout: Runs every 6 hours (00:00, 06:00, 12:00, 18:00 roughly)
schedule.every(6).hours.do(run_scout_process)

# 2. The Digest: Runs every Friday at 09:00 AM
# Note: Ensure your server time is set correctly or adjust for UTC.
schedule.every().friday.at("09:00").do(run_weekly_digest_pipeline)

# --- HEARTBEAT ---

if __name__ == "__main__":
    print(f"⏱️  VTA Scheduler Online at {datetime.now().strftime('%H:%M:%S')}")
    print("    - Scout Job:    Every 6 hours")
    print("    - Digest Job:   Fridays @ 09:00 AM")
    print("    - Logs:         scheduler.log")

    # Optional: Run the Scout immediately on startup to prove it works
    # run_scout_process()

    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute